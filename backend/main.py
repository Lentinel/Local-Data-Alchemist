import os
import json
import shutil
import subprocess
import uuid
import threading
from collections import Counter
from datetime import date, datetime, timedelta
import hashlib
import re
import base64
from pathlib import Path

import tkinter as tk
from tkinter import filedialog

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import httpx
from openai import APIConnectionError, AuthenticationError, OpenAI
from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from typing import Literal, Optional


ENV_PATH = Path(__file__).resolve().with_name(".env")
load_dotenv(dotenv_path=ENV_PATH, override=True)

app = FastAPI()
APP_VERSION = "phase7-native-fs-stable-2026-04-11"

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CATEGORY_RULES = {
    "logs": {
        ".log",
        ".txt",
        ".out",
        ".trace",
        ".err",
    },
    "images": {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".bmp",
        ".gif",
        ".tif",
        ".tiff",
    },
    "documents": {
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".csv",
        ".json",
        ".xml",
        ".md",
    },
    "archives": {
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".gz",
    },
    "code": {
        ".py",
        ".js",
        ".ts",
        ".vue",
        ".html",
        ".css",
        ".java",
        ".go",
        ".rs",
        ".sql",
    },
}

CATEGORY_LABELS = {
    "logs": "日志",
    "images": "图片",
    "documents": "文档/数据表",
    "archives": "压缩包",
    "code": "代码",
    "unknown": "未知类型",
}

ALLOWED_ACTIONS = {"rename_and_move", "move", "delete", "keep"}
TEXT_EXTENSIONS = {
    ".txt",
    ".log",
    ".csv",
    ".md",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".ini",
    ".conf",
    ".py",
    ".js",
    ".ts",
    ".vue",
    ".html",
    ".css",
    ".sql",
}


class FileInfo(BaseModel):
    name: str = Field(..., min_length=1, description="文件名")
    path: str = Field(..., min_length=1, description="文件相对路径")
    extension: str = Field(default="", description="文件扩展名")
    category: str = Field(default="unknown", description="文件分类")
    size: int = Field(default=0, ge=0, description="文件大小(字节)")


class PlanRequest(BaseModel):
    target_path: str = Field(..., min_length=1, description="目标目录路径")

    @field_validator("target_path")
    @classmethod
    def validate_target_path_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("目标路径不能为空或仅包含空白字符")
        return v


class FolderRequest(BaseModel):
    target_path: str = Field(..., min_length=1, description="目标目录路径")

    @field_validator("target_path")
    @classmethod
    def validate_target_path_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("目标路径不能为空或仅包含空白字符")
        return v


ActionType = Literal["rename_and_move", "move", "delete", "keep"]


class ActionPlanItem(BaseModel):
    file: str = Field(..., min_length=1, description="源文件相对路径")
    action: ActionType = Field(..., description="操作类型: rename_and_move | move | delete | keep")
    target_path: str | None = Field(default=None, description="目标相对路径（move/rename_and_move 操作必填）")
    reason: str = Field(default="", description="操作理由")
    extracted_info: dict | None = Field(default=None, description="提取的结构化信息")

    @field_validator("file")
    @classmethod
    def validate_file_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("文件路径不能为空或仅包含空白字符")
        return v

    @model_validator(mode="after")
    def validate_action_requirements(self) -> "ActionPlanItem":
        if self.action in {"move", "rename_and_move"}:
            if not self.target_path or not str(self.target_path).strip():
                raise ValueError(f"{self.action} 操作需要提供有效的 target_path")
        return self


class ExecutePlanRequest(BaseModel):
    target_path: str = Field(..., min_length=1, description="目标目录路径")
    plan: list[ActionPlanItem] = Field(default_factory=list, description="执行计划列表")

    @field_validator("target_path")
    @classmethod
    def validate_target_path_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("目标路径不能为空或仅包含空白字符")
        return v


class UndoPlanRequest(BaseModel):
    target_path: str = Field(..., min_length=1, description="目标目录路径")

    @field_validator("target_path")
    @classmethod
    def validate_target_path_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("目标路径不能为空或仅包含空白字符")
        return v


class FilePreviewRequest(BaseModel):
    target_path: str = Field(..., min_length=1, description="目标目录路径")
    file_path: str = Field(..., min_length=1, description="要预览的文件相对路径")

    @field_validator("target_path", "file_path")
    @classmethod
    def validate_paths_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("路径不能为空或仅包含空白字符")
        return v


class ListHistoryRequest(BaseModel):
    target_path: str = Field(..., min_length=1, description="目标目录路径")

    @field_validator("target_path")
    @classmethod
    def validate_target_path_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("目标路径不能为空或仅包含空白字符")
        return v


class GetHistoryRequest(BaseModel):
    target_path: str = Field(..., min_length=1, description="目标目录路径")
    history_id: str = Field(..., min_length=1, description="历史记录ID")

    @field_validator("target_path", "history_id")
    @classmethod
    def validate_fields_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("字段不能为空或仅包含空白字符")
        return v


class DetectDuplicatesRequest(BaseModel):
    target_path: str = Field(..., min_length=1, description="目标目录路径")
    fast_mode: bool = Field(default=True, description="是否使用快速检测模式")

    @field_validator("target_path")
    @classmethod
    def validate_target_path_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("目标路径不能为空或仅包含空白字符")
        return v


class KeepDuplicateRequest(BaseModel):
    target_path: str = Field(..., min_length=1, description="目标目录路径")
    keep_file: str = Field(..., min_length=1, description="要保留的文件路径")
    duplicate_files: list[str] = Field(..., description="要删除的重复文件列表")

    @field_validator("target_path", "keep_file")
    @classmethod
    def validate_fields_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("字段不能为空或仅包含空白字符")
        return v

    @field_validator("duplicate_files")
    @classmethod
    def validate_duplicate_files_not_empty(cls, v: list[str]) -> list[str]:
        if not v or len(v) == 0:
            raise ValueError("重复文件列表不能为空")
        for f in v:
            if not f or not f.strip():
                raise ValueError("重复文件列表中包含空路径")
        return v


class TemplateRule(BaseModel):
    rule_id: str = Field(..., min_length=1, description="规则ID")
    name: str = Field(..., min_length=1, description="规则名称")
    match_extensions: list[str] = Field(default_factory=list, description="匹配的扩展名列表")
    match_pattern: str = Field(default="", description="匹配正则表达式")
    match_category: str = Field(default="", description="匹配的分类")
    action: ActionType = Field(..., description="操作类型")
    target_path: str = Field(default="", description="目标路径模板")
    reason: str = Field(default="", description="操作理由")
    priority: int = Field(default=0, description="优先级")


class AlchemyTemplate(BaseModel):
    id: str = Field(..., min_length=1, description="模板ID")
    name: str = Field(..., min_length=1, description="模板名称")
    description: str = Field(..., description="模板描述")
    icon: str = Field(default="📁", description="图标")
    is_builtin: bool = Field(default=False, description="是否为内置模板")
    created_at: str = Field(default="", description="创建时间")
    updated_at: str = Field(default="", description="更新时间")
    rules: list[TemplateRule] = Field(default_factory=list, description="规则列表")


class ListTemplatesRequest(BaseModel):
    pass


class GetTemplateRequest(BaseModel):
    template_id: str = Field(..., min_length=1, description="模板ID")

    @field_validator("template_id")
    @classmethod
    def validate_template_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("模板ID不能为空或仅包含空白字符")
        return v


class SaveTemplateRequest(BaseModel):
    template: dict = Field(..., description="模板数据")

    @field_validator("template")
    @classmethod
    def validate_template_not_empty(cls, v: dict) -> dict:
        if not v:
            raise ValueError("模板数据不能为空")
        return v


class DeleteTemplateRequest(BaseModel):
    template_id: str = Field(..., min_length=1, description="模板ID")

    @field_validator("template_id")
    @classmethod
    def validate_template_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("模板ID不能为空或仅包含空白字符")
        return v


class ApplyTemplateRequest(BaseModel):
    target_path: str = Field(..., min_length=1, description="目标目录路径")
    template_id: str = Field(..., min_length=1, description="模板ID")

    @field_validator("target_path", "template_id")
    @classmethod
    def validate_fields_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("字段不能为空或仅包含空白字符")
        return v


RenameRuleType = Literal[
    "prefix", "suffix", "find_replace", "regex", 
    "numbering", "date_prefix", "date_suffix"
]


class RenameRule(BaseModel):
    rule_type: RenameRuleType = Field(..., description="重命名规则类型")
    prefix: str = Field(default="", description="前缀")
    suffix: str = Field(default="", description="后缀")
    find_text: str = Field(default="", description="要查找的文本")
    replace_text: str = Field(default="", description="替换文本")
    regex_pattern: str = Field(default="", description="正则表达式模式")
    regex_replacement: str = Field(default="", description="正则表达式替换")
    start_number: int = Field(default=1, ge=0, description="起始编号")
    number_padding: int = Field(default=3, ge=1, le=10, description="编号填充位数")
    number_separator: str = Field(default="_", description="编号分隔符")
    number_position: Literal["prefix", "suffix", "replace"] = Field(default="prefix", description="编号位置")


class RenamePreviewRequest(BaseModel):
    target_path: str = Field(..., min_length=1, description="目标目录路径")
    selected_files: list[str] = Field(..., description="选中的文件列表")
    rules: list[RenameRule] = Field(..., description="重命名规则列表")

    @field_validator("target_path")
    @classmethod
    def validate_target_path_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("目标路径不能为空或仅包含空白字符")
        return v

    @field_validator("selected_files")
    @classmethod
    def validate_selected_files_not_empty(cls, v: list[str]) -> list[str]:
        if not v or len(v) == 0:
            raise ValueError("选中的文件列表不能为空")
        for f in v:
            if not f or not f.strip():
                raise ValueError("选中的文件列表中包含空路径")
        return v

    @field_validator("rules")
    @classmethod
    def validate_rules_not_empty(cls, v: list[RenameRule]) -> list[RenameRule]:
        if not v or len(v) == 0:
            raise ValueError("重命名规则列表不能为空")
        return v


class RenameExecuteRequest(BaseModel):
    target_path: str = Field(..., min_length=1, description="目标目录路径")
    rename_plan: list[dict] = Field(..., description="重命名计划列表")

    @field_validator("target_path")
    @classmethod
    def validate_target_path_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("目标路径不能为空或仅包含空白字符")
        return v

    @field_validator("rename_plan")
    @classmethod
    def validate_rename_plan_not_empty(cls, v: list[dict]) -> list[dict]:
        if not v or len(v) == 0:
            raise ValueError("重命名计划列表不能为空")
        return v


class DashboardStatsRequest(BaseModel):
    target_path: str = Field(..., min_length=1, description="目标目录路径")

    @field_validator("target_path")
    @classmethod
    def validate_target_path_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("目标路径不能为空或仅包含空白字符")
        return v


class MultiTargetRequest(BaseModel):
    target_paths: list[str] = Field(..., description="目标目录路径列表")

    @field_validator("target_paths")
    @classmethod
    def validate_target_paths_not_empty(cls, v: list[str]) -> list[str]:
        if not v or len(v) == 0:
            raise ValueError("目标目录路径列表不能为空")
        valid_paths = []
        for path in v:
            if path is None or not isinstance(path, str):
                raise ValueError("目标路径必须是字符串类型")
            if not path.strip():
                raise ValueError("目标路径列表中包含空路径")
            valid_paths.append(path)
        return valid_paths


class MultiExecuteRequest(BaseModel):
    targets: list[dict] = Field(..., description="多目录执行计划列表")

    @field_validator("targets")
    @classmethod
    def validate_targets_not_empty(cls, v: list[dict]) -> list[dict]:
        if not v or len(v) == 0:
            raise ValueError("执行计划列表不能为空")
        return v


TaskStatus = Literal["pending", "running", "completed", "cancelled", "failed"]
TaskType = Literal["execute_plan", "undo_plan", "rename_execute", "deduplicate"]


class TaskProgress(BaseModel):
    task_id: str = Field(..., description="任务唯一ID")
    task_type: TaskType = Field(..., description="任务类型")
    status: TaskStatus = Field(..., description="任务状态")
    total: int = Field(default=0, ge=0, description="总步骤数")
    current: int = Field(default=0, ge=0, description="当前步骤")
    message: str = Field(default="", description="当前消息")
    current_file: str = Field(default="", description="当前处理的文件")
    start_time: Optional[str] = Field(default=None, description="开始时间")
    end_time: Optional[str] = Field(default=None, description="结束时间")
    error: Optional[str] = Field(default=None, description="错误信息")
    result: Optional[dict] = Field(default=None, description="执行结果")
    
    move_total: int = Field(default=0, ge=0, description="移动操作总数")
    move_done: int = Field(default=0, ge=0, description="已完成移动操作数")
    delete_total: int = Field(default=0, ge=0, description="删除操作总数")
    delete_done: int = Field(default=0, ge=0, description="已完成删除操作数")
    rename_total: int = Field(default=0, ge=0, description="重命名操作总数")
    rename_done: int = Field(default=0, ge=0, description="已完成重命名操作数")
    keep_total: int = Field(default=0, ge=0, description="保留操作总数")
    keep_done: int = Field(default=0, ge=0, description="已完成保留操作数")
    
    completed_items: list[dict] = Field(default_factory=list, description="已完成的操作列表")
    eta_seconds: Optional[float] = Field(default=None, description="估计剩余秒数")
    items_per_second: Optional[float] = Field(default=None, description="每秒处理速度")

    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return min(100.0, (self.current / self.total) * 100)


class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    percentage: float
    current: int
    total: int
    message: str
    current_file: str
    error: Optional[str]
    result: Optional[dict]
    
    move_total: int
    move_done: int
    delete_total: int
    delete_done: int
    rename_total: int
    rename_done: int
    keep_total: int
    keep_done: int
    
    completed_items: list[dict]
    eta_seconds: Optional[float]
    items_per_second: Optional[float]
    formatted_eta: Optional[str]


class CancelTaskRequest(BaseModel):
    task_id: str = Field(..., min_length=1, description="任务ID")


class PreviewPlanRequest(BaseModel):
    target_path: str = Field(..., min_length=1, description="目标目录路径")
    plan: list[ActionPlanItem] = Field(..., min_length=1, description="执行计划列表")

    @field_validator("target_path")
    @classmethod
    def validate_target_path_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("目标路径不能为空或仅包含空白字符")
        return v

    @field_validator("plan")
    @classmethod
    def validate_plan_not_empty(cls, v: list[ActionPlanItem]) -> list[ActionPlanItem]:
        if not v or len(v) == 0:
            raise ValueError("执行计划列表不能为空")
        return v


_task_store: dict[str, TaskProgress] = {}
_task_lock = threading.Lock()
_task_cancellation_flags: dict[str, bool] = {}


def format_eta(seconds: float) -> str:
    if seconds is None or seconds < 0:
        return "计算中..."
    if seconds < 60:
        return f"约 {int(seconds)} 秒"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"约 {minutes} 分 {secs} 秒"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"约 {hours} 小时 {minutes} 分"


def create_task(
    task_type: TaskType, 
    total: int = 0,
    plan: list | None = None,
) -> str:
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    
    move_total = 0
    delete_total = 0
    rename_total = 0
    keep_total = 0
    
    if plan:
        for item in plan:
            action = getattr(item, "action", None) or (item.get("action") if isinstance(item, dict) else None)
            if action == "move":
                move_total += 1
            elif action == "delete":
                delete_total += 1
            elif action == "rename_and_move":
                rename_total += 1
            elif action == "keep":
                keep_total += 1
    
    with _task_lock:
        _task_store[task_id] = TaskProgress(
            task_id=task_id,
            task_type=task_type,
            status="pending",
            total=total,
            current=0,
            message="任务已创建，等待执行",
            current_file="",
            start_time=datetime.now().isoformat(),
            end_time=None,
            error=None,
            result=None,
            move_total=move_total,
            move_done=0,
            delete_total=delete_total,
            delete_done=0,
            rename_total=rename_total,
            rename_done=0,
            keep_total=keep_total,
            keep_done=0,
            completed_items=[],
            eta_seconds=None,
            items_per_second=None,
        )
        _task_cancellation_flags[task_id] = False
    return task_id


def get_task(task_id: str) -> TaskProgress | None:
    with _task_lock:
        return _task_store.get(task_id)


def update_task_progress(
    task_id: str,
    current: int | None = None,
    message: str | None = None,
    current_file: str | None = None,
    status: TaskStatus | None = None,
    error: str | None = None,
    result: dict | None = None,
    move_done: int | None = None,
    delete_done: int | None = None,
    rename_done: int | None = None,
    keep_done: int | None = None,
    completed_item: dict | None = None,
):
    with _task_lock:
        task = _task_store.get(task_id)
        if not task:
            return
        
        if current is not None:
            task.current = current
            
            if task.current > 0 and task.start_time:
                try:
                    start_dt = datetime.fromisoformat(task.start_time)
                    elapsed = (datetime.now() - start_dt).total_seconds()
                    if elapsed > 0:
                        task.items_per_second = task.current / elapsed
                        remaining = task.total - task.current
                        if task.items_per_second > 0:
                            task.eta_seconds = remaining / task.items_per_second
                        else:
                            task.eta_seconds = None
                    else:
                        task.eta_seconds = None
                except (ValueError, TypeError):
                    task.eta_seconds = None
        
        if message is not None:
            task.message = message
        if current_file is not None:
            task.current_file = current_file
        if status is not None:
            task.status = status
            if status in {"completed", "cancelled", "failed"}:
                task.end_time = datetime.now().isoformat()
                task.eta_seconds = 0
        if error is not None:
            task.error = error
        if result is not None:
            task.result = result
        
        if move_done is not None:
            task.move_done = move_done
        if delete_done is not None:
            task.delete_done = delete_done
        if rename_done is not None:
            task.rename_done = rename_done
        if keep_done is not None:
            task.keep_done = keep_done
        
        if completed_item is not None:
            task.completed_items.append(completed_item)
            if len(task.completed_items) > 100:
                task.completed_items = task.completed_items[-50:]


def is_task_cancelled(task_id: str) -> bool:
    with _task_lock:
        return _task_cancellation_flags.get(task_id, False)


def cancel_task(task_id: str) -> bool:
    with _task_lock:
        if task_id not in _task_store:
            return False
        _task_cancellation_flags[task_id] = True
        task = _task_store[task_id]
        if task.status in {"pending", "running"}:
            task.status = "cancelled"
            task.end_time = datetime.now().isoformat()
        return True


def cleanup_old_tasks(max_age_hours: int = 24):
    with _task_lock:
        now = datetime.now()
        task_ids_to_remove = []
        for task_id, task in _task_store.items():
            if task.end_time:
                try:
                    end_time = datetime.fromisoformat(task.end_time)
                    if (now - end_time).total_seconds() > max_age_hours * 3600:
                        task_ids_to_remove.append(task_id)
                except (ValueError, TypeError):
                    task_ids_to_remove.append(task_id)
        for task_id in task_ids_to_remove:
            del _task_store[task_id]
            if task_id in _task_cancellation_flags:
                del _task_cancellation_flags[task_id]


def preview_plan_impl(
    target_dir: Path,
    plan: list[ActionPlanItem]
) -> dict:
    summary = {
        "total_actions": len(plan),
        "by_action": {},
        "move_actions": [],
        "delete_actions": [],
        "keep_actions": [],
        "conflicts": [],
        "warnings": [],
        "new_folders": set(),
    }

    target_paths_map = {}
    source_paths_map = {}

    for i, item in enumerate(plan):
        action = item.action
        source_file = item.file

        if action not in summary["by_action"]:
            summary["by_action"][action] = 0
        summary["by_action"][action] += 1

        source_path = resolve_inside_target(target_dir, source_file)
        source_exists = source_path.exists()

        if not source_exists:
            summary["warnings"].append({
                "index": i,
                "action": action,
                "file": source_file,
                "message": "源文件不存在"
            })

        if action in {"move", "rename_and_move"}:
            target_file = item.target_path
            target_path = resolve_inside_target(target_dir, target_file)
            
            summary["move_actions"].append({
                "index": i,
                "source": source_file,
                "source_name": Path(source_file).name,
                "target": target_file,
                "target_name": Path(target_file).name,
                "source_exists": source_exists,
            })

            target_parent = Path(target_file).parent
            if str(target_parent) != "." and str(target_parent) != "":
                summary["new_folders"].add(str(target_parent))

            if target_path.exists() and target_path != source_path:
                summary["conflicts"].append({
                    "index": i,
                    "type": "target_exists",
                    "source": source_file,
                    "target": target_file,
                    "message": "目标路径已存在"
                })

            normalized_target = str(target_path.resolve())
            if normalized_target in target_paths_map:
                summary["conflicts"].append({
                    "index": i,
                    "type": "duplicate_target",
                    "source": source_file,
                    "target": target_file,
                    "other_source": target_paths_map[normalized_target]["source"],
                    "message": "多个文件将移动到同一个目标"
                })
            target_paths_map[normalized_target] = {
                "source": source_file,
                "target": target_file,
                "index": i,
            }

        elif action == "delete":
            summary["delete_actions"].append({
                "index": i,
                "file": source_file,
                "file_name": Path(source_file).name,
                "source_exists": source_exists,
            })

        elif action == "keep":
            summary["keep_actions"].append({
                "index": i,
                "file": source_file,
                "file_name": Path(source_file).name,
                "source_exists": source_exists,
            })

    move_count = len(summary["move_actions"])
    delete_count = len(summary["delete_actions"])
    keep_count = len(summary["keep_actions"])

    has_conflicts = len(summary["conflicts"]) > 0
    has_warnings = len(summary["warnings"]) > 0
    needs_confirmation = has_conflicts or delete_count > 0

    safety_level = "safe"
    safety_reasons = []

    if has_conflicts:
        safety_level = "danger"
        safety_reasons.append(f"检测到 {len(summary['conflicts'])} 个冲突")
    
    if delete_count > 0:
        safety_level = "warning" if safety_level == "safe" else safety_level
        safety_reasons.append(f"将删除 {delete_count} 个文件")
    
    if move_count > 10:
        safety_level = "warning" if safety_level == "safe" else safety_level
        safety_reasons.append(f"涉及 {move_count} 个文件操作")

    return {
        "status": "success",
        "summary": {
            "total_actions": summary["total_actions"],
            "move_count": move_count,
            "delete_count": delete_count,
            "keep_count": keep_count,
            "by_action": summary["by_action"],
            "new_folders_count": len(summary["new_folders"]),
            "new_folders": list(summary["new_folders"]),
        },
        "conflicts": summary["conflicts"],
        "warnings": summary["warnings"],
        "move_actions": summary["move_actions"],
        "delete_actions": summary["delete_actions"],
        "keep_actions": summary["keep_actions"],
        "safety_level": safety_level,
        "safety_reasons": safety_reasons,
        "has_conflicts": has_conflicts,
        "has_warnings": has_warnings,
        "needs_confirmation": needs_confirmation,
    }


def get_file_modification_time(file_path: Path) -> date | None:
    try:
        timestamp = file_path.stat().st_mtime
        return date.fromtimestamp(timestamp)
    except (OSError, Exception):
        return None


def calculate_dashboard_stats(
    target_dir: Path,
    files_info: list[dict],
    include_history: bool = True
) -> dict:
    total_files = len(files_info)
    total_size = sum(f.get("size", 0) for f in files_info)
    
    category_stats = {
        "images": {"count": 0, "size": 0},
        "documents": {"count": 0, "size": 0},
        "archives": {"count": 0, "size": 0},
        "code": {"count": 0, "size": 0},
        "logs": {"count": 0, "size": 0},
        "unknown": {"count": 0, "size": 0},
    }
    
    extension_counts = {}
    
    size_buckets = {
        "tiny": {"count": 0, "size": 0, "label": "< 100KB"},
        "small": {"count": 0, "size": 0, "label": "100KB - 1MB"},
        "medium": {"count": 0, "size": 0, "label": "1MB - 10MB"},
        "large": {"count": 0, "size": 0, "label": "10MB - 100MB"},
        "huge": {"count": 0, "size": 0, "label": "> 100MB"},
    }
    
    today = date.today()
    week_dates = []
    for i in range(6, -1, -1):
        week_dates.append(today - timedelta(days=i))
    
    weekly_stats = {}
    for d in week_dates:
        weekly_stats[d.isoformat()] = {"count": 0, "size": 0, "date": d.isoformat()}
    
    for file_info in files_info:
        category = file_info.get("category", "unknown")
        size = file_info.get("size", 0)
        extension = file_info.get("extension", "").lower()
        
        if category in category_stats:
            category_stats[category]["count"] += 1
            category_stats[category]["size"] += size
        
        if extension:
            if extension not in extension_counts:
                extension_counts[extension] = {"count": 0, "size": 0}
            extension_counts[extension]["count"] += 1
            extension_counts[extension]["size"] += size
        
        if size < 100 * 1024:
            size_buckets["tiny"]["count"] += 1
            size_buckets["tiny"]["size"] += size
        elif size < 1024 * 1024:
            size_buckets["small"]["count"] += 1
            size_buckets["small"]["size"] += size
        elif size < 10 * 1024 * 1024:
            size_buckets["medium"]["count"] += 1
            size_buckets["medium"]["size"] += size
        elif size < 100 * 1024 * 1024:
            size_buckets["large"]["count"] += 1
            size_buckets["large"]["size"] += size
        else:
            size_buckets["huge"]["count"] += 1
            size_buckets["huge"]["size"] += size
        
        file_path = resolve_inside_target(target_dir, file_info.get("path", ""))
        if file_path.exists():
            mod_date = get_file_modification_time(file_path)
            if mod_date:
                date_str = mod_date.isoformat()
                if date_str in weekly_stats:
                    weekly_stats[date_str]["count"] += 1
                    weekly_stats[date_str]["size"] += size
    
    top_extensions = sorted(
        extension_counts.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )[:10]
    
    history_stats = None
    if include_history:
        history_list = list_history(target_dir)
        history_stats = {
            "total_operations": len(history_list),
            "by_type": {},
            "last_7_days": 0,
        }
        
        for item in history_list:
            op_type = item.get("type", "unknown")
            if op_type not in history_stats["by_type"]:
                history_stats["by_type"][op_type] = 0
            history_stats["by_type"][op_type] += 1
            
            created_at = item.get("created_at")
            if created_at:
                try:
                    if isinstance(created_at, str):
                        if "T" in created_at:
                            item_date = datetime.fromisoformat(created_at).date()
                        else:
                            item_date = date.fromisoformat(created_at)
                    else:
                        item_date = created_at
                    
                    if (today - item_date).days <= 7:
                        history_stats["last_7_days"] += 1
                except (ValueError, TypeError):
                    pass
    
    return {
        "overview": {
            "total_files": total_files,
            "total_size": total_size,
            "categories": category_stats,
        },
        "size_distribution": size_buckets,
        "extension_distribution": {
            ext: data for ext, data in top_extensions
        },
        "weekly_activity": list(weekly_stats.values()),
        "history_stats": history_stats,
    }


def scan_and_analyze_single_path(
    target_path: str,
    index: int = 0
) -> dict:
    try:
        target_dir = get_target_dir(target_path)
        files_info = scan_target_files(target_dir)
        analysis_result = build_analysis(files_info)
        file_snippets = build_file_snippets(target_dir, [FileInfo(**f) for f in files_info])
        
        return {
            "status": "success",
            "index": index,
            "target_path": str(target_dir),
            "files": file_snippets,
            "file_inventory": files_info,
            "analysis": analysis_result,
            "file_count": len(files_info),
            "total_size": analysis_result.get("total_size", 0) if analysis_result else 0,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "index": index,
            "target_path": target_path,
            "error": str(exc),
            "files": [],
            "file_inventory": [],
            "analysis": None,
            "file_count": 0,
            "total_size": 0,
        }


def generate_plan_for_single_path(
    target_path: str,
    files_info: list[dict],
    file_inventory: list[dict],
    index: int = 0
) -> dict:
    try:
        target_dir = get_target_dir(target_path)
        
        files_s = [FileInfo(**f) for f in files_info]
        
        files_content = generate_files_content(files_s)
        prompt = build_prompt(target_dir, files_content, files_info)
        
        try:
            action_plan = call_llm_for_plan(prompt)
            plan_status = "success"
            plan_error = None
        except Exception as llm_exc:
            action_plan = []
            plan_status = "llm_failed"
            plan_error = str(llm_exc)
        
        return {
            "status": plan_status,
            "index": index,
            "target_path": str(target_dir),
            "plan": action_plan,
            "error": plan_error,
            "file_count": len(files_info),
            "action_count": len(action_plan),
        }
    except Exception as exc:
        return {
            "status": "failed",
            "index": index,
            "target_path": target_path,
            "plan": [],
            "error": str(exc),
            "file_count": 0,
            "action_count": 0,
        }


def get_templates_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


BUILTIN_TEMPLATES = [
    {
        "id": "builtin-photos",
        "name": "照片整理",
        "description": "将照片按时间和类型分类整理，适合相机导入和截图文件夹",
        "icon": "📷",
        "is_builtin": True,
        "rules": [
            {
                "rule_id": "rule-1",
                "name": "PNG图片",
                "match_extensions": [".png"],
                "match_pattern": "",
                "match_category": "images",
                "action": "move",
                "target_path": "images/png/{name}",
                "reason": "PNG格式图片通常是截图或透明背景图片，归档到images/png目录",
                "priority": 10
            },
            {
                "rule_id": "rule-2",
                "name": "JPG/JPEG图片",
                "match_extensions": [".jpg", ".jpeg"],
                "match_pattern": "",
                "match_category": "images",
                "action": "move",
                "target_path": "images/photos/{name}",
                "reason": "JPG格式照片通常是相机拍摄的照片，归档到images/photos目录",
                "priority": 10
            },
            {
                "rule_id": "rule-3",
                "name": "GIF动图",
                "match_extensions": [".gif"],
                "match_pattern": "",
                "match_category": "images",
                "action": "move",
                "target_path": "images/gif/{name}",
                "reason": "GIF格式动图，归档到images/gif目录",
                "priority": 10
            },
            {
                "rule_id": "rule-4",
                "name": "WEBP图片",
                "match_extensions": [".webp"],
                "match_pattern": "",
                "match_category": "images",
                "action": "move",
                "target_path": "images/webp/{name}",
                "reason": "WEBP格式图片，归档到images/webp目录",
                "priority": 10
            },
            {
                "rule_id": "rule-5",
                "name": "截图文件",
                "match_extensions": [],
                "match_pattern": "screenshot|screen.*shot|截图",
                "match_category": "images",
                "action": "rename_and_move",
                "target_path": "images/screenshots/{date}_{name}",
                "reason": "截图文件统一归档到screenshots目录，并添加日期前缀",
                "priority": 20
            }
        ]
    },
    {
        "id": "builtin-downloads",
        "name": "下载文件夹清理",
        "description": "清理下载文件夹，按文件类型分类归档，删除临时文件",
        "icon": "📥",
        "is_builtin": True,
        "rules": [
            {
                "rule_id": "rule-1",
                "name": "安装包文件",
                "match_extensions": [".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm"],
                "match_pattern": "",
                "match_category": "",
                "action": "move",
                "target_path": "installers/{name}",
                "reason": "安装包文件归档到installers目录",
                "priority": 10
            },
            {
                "rule_id": "rule-2",
                "name": "压缩包文件",
                "match_extensions": [".zip", ".rar", ".7z", ".tar", ".gz"],
                "match_pattern": "",
                "match_category": "archives",
                "action": "move",
                "target_path": "archives/{name}",
                "reason": "压缩包文件归档到archives目录",
                "priority": 10
            },
            {
                "rule_id": "rule-3",
                "name": "PDF文档",
                "match_extensions": [".pdf"],
                "match_pattern": "",
                "match_category": "documents",
                "action": "move",
                "target_path": "documents/pdf/{name}",
                "reason": "PDF文档归档到documents/pdf目录",
                "priority": 10
            },
            {
                "rule_id": "rule-4",
                "name": "Word文档",
                "match_extensions": [".doc", ".docx"],
                "match_pattern": "",
                "match_category": "documents",
                "action": "move",
                "target_path": "documents/word/{name}",
                "reason": "Word文档归档到documents/word目录",
                "priority": 10
            },
            {
                "rule_id": "rule-5",
                "name": "Excel表格",
                "match_extensions": [".xls", ".xlsx", ".csv"],
                "match_pattern": "",
                "match_category": "documents",
                "action": "move",
                "target_path": "documents/spreadsheets/{name}",
                "reason": "Excel表格和CSV文件归档到documents/spreadsheets目录",
                "priority": 10
            },
            {
                "rule_id": "rule-6",
                "name": "临时缓存文件",
                "match_extensions": [".tmp", ".temp", ".cache"],
                "match_pattern": "",
                "match_category": "",
                "action": "delete",
                "target_path": "",
                "reason": "临时缓存文件可以安全删除",
                "priority": 5
            },
            {
                "rule_id": "rule-7",
                "name": "Torrent种子文件",
                "match_extensions": [".torrent"],
                "match_pattern": "",
                "match_category": "",
                "action": "delete",
                "target_path": "",
                "reason": "下载完成后种子文件通常不再需要",
                "priority": 5
            }
        ]
    },
    {
        "id": "builtin-logs",
        "name": "日志归档",
        "description": "整理日志文件，按日期和严重级别分类",
        "icon": "📋",
        "is_builtin": True,
        "rules": [
            {
                "rule_id": "rule-1",
                "name": "标准日志文件",
                "match_extensions": [".log", ".txt"],
                "match_pattern": "",
                "match_category": "logs",
                "action": "rename_and_move",
                "target_path": "logs/archive/{date}_{name}",
                "reason": "日志文件按日期归档，便于追溯",
                "priority": 10
            },
            {
                "rule_id": "rule-2",
                "name": "错误日志",
                "match_extensions": [".err", ".error"],
                "match_pattern": "error|Error|ERROR|exception|Exception",
                "match_category": "logs",
                "action": "rename_and_move",
                "target_path": "logs/errors/{date}_{name}",
                "reason": "错误日志单独归档，便于问题排查",
                "priority": 20
            },
            {
                "rule_id": "rule-3",
                "name": "Trace追踪文件",
                "match_extensions": [".trace"],
                "match_pattern": "",
                "match_category": "logs",
                "action": "move",
                "target_path": "logs/traces/{name}",
                "reason": "Trace追踪文件归档到traces目录",
                "priority": 10
            }
        ]
    },
    {
        "id": "builtin-code",
        "name": "代码文件整理",
        "description": "按编程语言分类整理代码文件，适合收集的代码片段",
        "icon": "💻",
        "is_builtin": True,
        "rules": [
            {
                "rule_id": "rule-1",
                "name": "Python文件",
                "match_extensions": [".py"],
                "match_pattern": "",
                "match_category": "code",
                "action": "move",
                "target_path": "code/python/{name}",
                "reason": "Python代码文件归档到code/python目录",
                "priority": 10
            },
            {
                "rule_id": "rule-2",
                "name": "JavaScript文件",
                "match_extensions": [".js", ".jsx"],
                "match_pattern": "",
                "match_category": "code",
                "action": "move",
                "target_path": "code/javascript/{name}",
                "reason": "JavaScript代码文件归档到code/javascript目录",
                "priority": 10
            },
            {
                "rule_id": "rule-3",
                "name": "TypeScript文件",
                "match_extensions": [".ts", ".tsx"],
                "match_pattern": "",
                "match_category": "code",
                "action": "move",
                "target_path": "code/typescript/{name}",
                "reason": "TypeScript代码文件归档到code/typescript目录",
                "priority": 10
            },
            {
                "rule_id": "rule-4",
                "name": "Java文件",
                "match_extensions": [".java"],
                "match_pattern": "",
                "match_category": "code",
                "action": "move",
                "target_path": "code/java/{name}",
                "reason": "Java代码文件归档到code/java目录",
                "priority": 10
            },
            {
                "rule_id": "rule-5",
                "name": "Go文件",
                "match_extensions": [".go"],
                "match_pattern": "",
                "match_category": "code",
                "action": "move",
                "target_path": "code/go/{name}",
                "reason": "Go代码文件归档到code/go目录",
                "priority": 10
            },
            {
                "rule_id": "rule-6",
                "name": "Rust文件",
                "match_extensions": [".rs"],
                "match_pattern": "",
                "match_category": "code",
                "action": "move",
                "target_path": "code/rust/{name}",
                "reason": "Rust代码文件归档到code/rust目录",
                "priority": 10
            },
            {
                "rule_id": "rule-7",
                "name": "SQL文件",
                "match_extensions": [".sql"],
                "match_pattern": "",
                "match_category": "code",
                "action": "move",
                "target_path": "code/sql/{name}",
                "reason": "SQL脚本文件归档到code/sql目录",
                "priority": 10
            },
            {
                "rule_id": "rule-8",
                "name": "HTML/CSS文件",
                "match_extensions": [".html", ".htm", ".css"],
                "match_pattern": "",
                "match_category": "code",
                "action": "move",
                "target_path": "code/web/{name}",
                "reason": "HTML和CSS文件归档到code/web目录",
                "priority": 10
            },
            {
                "rule_id": "rule-9",
                "name": "Vue文件",
                "match_extensions": [".vue"],
                "match_pattern": "",
                "match_category": "code",
                "action": "move",
                "target_path": "code/vue/{name}",
                "reason": "Vue组件文件归档到code/vue目录",
                "priority": 10
            }
        ]
    },
    {
        "id": "builtin-documents",
        "name": "文档整理",
        "description": "整理各类文档，按类型和用途分类归档",
        "icon": "📄",
        "is_builtin": True,
        "rules": [
            {
                "rule_id": "rule-1",
                "name": "PDF文档",
                "match_extensions": [".pdf"],
                "match_pattern": "",
                "match_category": "documents",
                "action": "move",
                "target_path": "documents/pdf/{name}",
                "reason": "PDF文档归档到pdf目录",
                "priority": 10
            },
            {
                "rule_id": "rule-2",
                "name": "Word文档",
                "match_extensions": [".doc", ".docx"],
                "match_pattern": "",
                "match_category": "documents",
                "action": "move",
                "target_path": "documents/word/{name}",
                "reason": "Word文档归档到word目录",
                "priority": 10
            },
            {
                "rule_id": "rule-3",
                "name": "Excel表格",
                "match_extensions": [".xls", ".xlsx"],
                "match_pattern": "",
                "match_category": "documents",
                "action": "move",
                "target_path": "documents/excel/{name}",
                "reason": "Excel表格归档到excel目录",
                "priority": 10
            },
            {
                "rule_id": "rule-4",
                "name": "CSV数据文件",
                "match_extensions": [".csv"],
                "match_pattern": "",
                "match_category": "documents",
                "action": "move",
                "target_path": "documents/data/{name}",
                "reason": "CSV数据文件归档到data目录",
                "priority": 10
            },
            {
                "rule_id": "rule-5",
                "name": "Markdown文档",
                "match_extensions": [".md"],
                "match_pattern": "",
                "match_category": "documents",
                "action": "move",
                "target_path": "documents/markdown/{name}",
                "reason": "Markdown文档归档到markdown目录",
                "priority": 10
            },
            {
                "rule_id": "rule-6",
                "name": "JSON数据文件",
                "match_extensions": [".json"],
                "match_pattern": "",
                "match_category": "documents",
                "action": "move",
                "target_path": "documents/data/{name}",
                "reason": "JSON数据文件归档到data目录",
                "priority": 10
            },
            {
                "rule_id": "rule-7",
                "name": "XML配置文件",
                "match_extensions": [".xml"],
                "match_pattern": "",
                "match_category": "documents",
                "action": "move",
                "target_path": "documents/config/{name}",
                "reason": "XML配置文件归档到config目录",
                "priority": 10
            }
        ]
    }
]


def load_all_templates() -> list[dict]:
    templates = []
    
    for builtin in BUILTIN_TEMPLATES:
        templates.append(builtin.copy())
    
    templates_dir = get_templates_dir()
    if templates_dir.exists():
        for template_file in templates_dir.glob("*.json"):
            try:
                content = json.loads(template_file.read_text(encoding="utf-8"))
                content["is_builtin"] = False
                templates.append(content)
            except (json.JSONDecodeError, OSError, Exception):
                continue
    
    return templates


def find_template(template_id: str) -> dict | None:
    for template in BUILTIN_TEMPLATES:
        if template["id"] == template_id:
            return template.copy()
    
    templates_dir = get_templates_dir()
    if templates_dir.exists():
        template_file = templates_dir / f"{template_id}.json"
        if template_file.exists():
            try:
                content = json.loads(template_file.read_text(encoding="utf-8"))
                content["is_builtin"] = False
                return content
            except (json.JSONDecodeError, OSError, Exception):
                pass
    
    return None


def save_user_template(template_data: dict) -> dict:
    templates_dir = get_templates_dir()
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    template_id = template_data.get("id")
    if not template_id:
        template_id = f"user-{uuid.uuid4().hex[:8]}"
        template_data["id"] = template_id
    
    now = datetime.now().isoformat()
    if "created_at" not in template_data or not template_data["created_at"]:
        template_data["created_at"] = now
    template_data["updated_at"] = now
    template_data["is_builtin"] = False
    
    template_file = templates_dir / f"{template_id}.json"
    template_file.write_text(json.dumps(template_data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return template_data


def delete_user_template(template_id: str) -> bool:
    if template_id.startswith("builtin-"):
        return False
    
    templates_dir = get_templates_dir()
    template_file = templates_dir / f"{template_id}.json"
    
    if template_file.exists():
        try:
            template_file.unlink()
            return True
        except OSError:
            pass
    
    return False


def match_file_to_rule(file_info: dict, rule: dict) -> bool:
    extension = (file_info.get("extension") or "").lower()
    name = file_info.get("name") or ""
    path = file_info.get("path") or ""
    category = file_info.get("category") or ""
    
    match_extensions = rule.get("match_extensions") or []
    if match_extensions:
        ext_match = any(ext.lower() == extension for ext in match_extensions)
        if not ext_match:
            return False
    
    match_pattern = rule.get("match_pattern") or ""
    if match_pattern:
        try:
            pattern = re.compile(match_pattern, re.IGNORECASE)
            if not pattern.search(name) and not pattern.search(path):
                return False
        except re.error:
            pass
    
    match_category = rule.get("match_category") or ""
    if match_category:
        if category != match_category:
            return False
    
    return True


def apply_template_to_files(template: dict, files_info: list[dict], target_dir: Path) -> list[dict]:
    rules = template.get("rules") or []
    sorted_rules = sorted(rules, key=lambda r: r.get("priority", 0), reverse=True)
    
    today = date.today().isoformat()
    plan = []
    processed_files = set()
    
    for file_info in files_info:
        file_path = file_info.get("path")
        if file_path in processed_files:
            continue
        
        matched_rule = None
        for rule in sorted_rules:
            if match_file_to_rule(file_info, rule):
                matched_rule = rule
                break
        
        if not matched_rule:
            plan.append({
                "file": file_path,
                "action": "keep",
                "target_path": None,
                "reason": "无匹配规则，保留原位置",
                "extracted_info": {
                    "type": "none",
                    "amount": None,
                    "currency": None,
                    "date": None,
                    "merchant": None,
                    "document_id": None,
                    "title": "",
                    "severity": None,
                    "error_code": None,
                    "root_cause": "",
                    "recommended_action": "",
                    "summary": "",
                }
            })
            processed_files.add(file_path)
            continue
        
        action = matched_rule.get("action", "keep")
        target_path_template = matched_rule.get("target_path", "")
        reason = matched_rule.get("reason", "")
        
        target_path = None
        if action in {"move", "rename_and_move"} and target_path_template:
            file_name = Path(file_path).name
            name_stem = Path(file_name).stem
            
            target_path = target_path_template.replace("{name}", file_name)
            target_path = target_path.replace("{date}", today)
            
            if "{stem}" in target_path:
                target_path = target_path.replace("{stem}", name_stem)
        
        plan.append({
            "file": file_path,
            "action": action,
            "target_path": target_path if action in {"move", "rename_and_move"} else None,
            "reason": reason,
            "extracted_info": {
                "type": "none",
                "amount": None,
                "currency": None,
                "date": None,
                "merchant": None,
                "document_id": None,
                "title": matched_rule.get("name", ""),
                "severity": None,
                "error_code": None,
                "root_cause": "",
                "recommended_action": "",
                "summary": f"应用模板：{template.get('name', '未命名模板')}",
            }
        })
        processed_files.add(file_path)
    
    return plan


WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

WINDOWS_INVALID_CHARS = set(r'\/:*?"<>|')

MAX_FILENAME_LENGTH = 255


def validate_filename(filename: str) -> tuple[bool, str | None]:
    if not filename or not filename.strip():
        return False, "文件名为空"
    
    for char in filename:
        if char in WINDOWS_INVALID_CHARS:
            return False, f"包含非法字符: {repr(char)}"
    
    name_without_ext = Path(filename).stem.upper()
    if name_without_ext in WINDOWS_RESERVED_NAMES:
        return False, f"包含 Windows 保留名称: {name_without_ext}"
    
    for reserved in WINDOWS_RESERVED_NAMES:
        if name_without_ext.startswith(f"{reserved}."):
            return False, f"包含 Windows 保留名称: {reserved}"
    
    if filename.endswith(".") or filename.endswith(" "):
        return False, "文件名不能以点或空格结尾"
    
    if len(filename) > MAX_FILENAME_LENGTH:
        return False, f"文件名过长 ({len(filename)} > {MAX_FILENAME_LENGTH})"
    
    if not name_without_ext.strip():
        return False, "文件名主体部分为空（如 .hidden 格式仅隐藏文件可用）"
    
    return True, None


def sanitize_filename(name: str, fallback_prefix: str = "file") -> str:
    if not name or not name.strip():
        return f"{fallback_prefix}_sanitized"
    
    sanitized = []
    for char in name:
        if char in WINDOWS_INVALID_CHARS:
            sanitized.append("_")
        else:
            sanitized.append(char)
    
    sanitized = "".join(sanitized)
    
    while sanitized.endswith(".") or sanitized.endswith(" "):
        sanitized = sanitized[:-1]
    
    if not sanitized or not Path(sanitized).stem.strip():
        return f"{fallback_prefix}_sanitized"
    
    stem = Path(sanitized).stem.upper()
    if stem in WINDOWS_RESERVED_NAMES:
        sanitized = f"{sanitized}_renamed"
    
    if len(sanitized) > MAX_FILENAME_LENGTH:
        extension = Path(sanitized).suffix
        max_stem_length = MAX_FILENAME_LENGTH - len(extension) - 1
        if max_stem_length < 1:
            max_stem_length = 1
        stem = Path(sanitized).stem[:max_stem_length]
        sanitized = stem + extension
    
    return sanitized


def apply_rename_rules(
    original_name: str,
    rules: list[RenameRule],
    index: int = 0,
    total_count: int = 1,
    sanitize: bool = True
) -> tuple[str, str | None]:
    name_stem = Path(original_name).stem
    extension = Path(original_name).suffix
    current_name = name_stem
    
    for rule in rules:
        rule_type = rule.rule_type
        
        if rule_type == "prefix":
            prefix = rule.prefix or ""
            current_name = prefix + current_name
        
        elif rule_type == "suffix":
            suffix = rule.suffix or ""
            current_name = current_name + suffix
        
        elif rule_type == "find_replace":
            find_text = rule.find_text or ""
            replace_text = rule.replace_text or ""
            if find_text:
                current_name = current_name.replace(find_text, replace_text)
        
        elif rule_type == "regex":
            pattern = rule.regex_pattern or ""
            replacement = rule.regex_replacement or ""
            if pattern:
                try:
                    current_name = re.sub(pattern, replacement, current_name)
                except re.error:
                    pass
        
        elif rule_type == "numbering":
            start_num = rule.start_number or 1
            padding = rule.number_padding or 3
            separator = rule.number_separator or "_"
            position = rule.number_position or "prefix"
            
            num_str = str(start_num + index).zfill(padding)
            
            if position == "prefix":
                current_name = num_str + separator + current_name
            elif position == "suffix":
                current_name = current_name + separator + num_str
            elif position == "replace":
                current_name = num_str
        
        elif rule_type == "date_prefix":
            today = date.today().isoformat()
            separator = rule.number_separator or "_"
            current_name = today + separator + current_name
        
        elif rule_type == "date_suffix":
            today = date.today().isoformat()
            separator = rule.number_separator or "_"
            current_name = current_name + separator + today
    
    final_name = current_name + extension
    
    is_valid, error_reason = validate_filename(final_name)
    
    if not is_valid and sanitize:
        sanitized_name = sanitize_filename(final_name, fallback_prefix=name_stem or "file")
        if sanitized_name != final_name:
            return sanitized_name, f"自动修正: {error_reason}"
    
    if not is_valid:
        return final_name, error_reason
    
    return final_name, None


def generate_rename_preview(
    target_dir: Path,
    selected_files: list[str],
    rules: list[RenameRule]
) -> dict:
    results = []
    conflicts = []
    warnings = []
    new_names = set()
    file_info_map = {}
    
    for file_path in selected_files:
        full_path = resolve_inside_target(target_dir, file_path)
        if not full_path.exists():
            continue
        
        original_name = full_path.name
        file_info_map[file_path] = {
            "path": file_path,
            "original_name": original_name,
            "full_path": full_path
        }
    
    sorted_files = sorted(file_info_map.items(), key=lambda x: x[1]["original_name"])
    
    for index, (file_path, info) in enumerate(sorted_files):
        original_name = info["original_name"]
        new_name, validation_warning = apply_rename_rules(
            original_name,
            rules,
            index,
            len(sorted_files)
        )
        
        parent_dir = Path(file_path).parent
        if parent_dir == Path("."):
            new_path = new_name
        else:
            new_path = str(parent_dir / new_name)
        
        conflict = False
        if new_name != original_name:
            if new_name in new_names:
                conflict = True
                conflicts.append({
                    "file": file_path,
                    "original_name": original_name,
                    "new_name": new_name,
                    "reason": "与其他重命名文件冲突"
                })
            
            new_full_path = resolve_inside_target(target_dir, new_path)
            if new_full_path.exists() and new_path != file_path:
                conflict = True
                conflicts.append({
                    "file": file_path,
                    "original_name": original_name,
                    "new_name": new_name,
                    "reason": "目标文件已存在"
                })
            
            new_names.add(new_name)
        
        if validation_warning:
            warnings.append({
                "file": file_path,
                "original_name": original_name,
                "new_name": new_name,
                "warning": validation_warning
            })
        
        results.append({
            "original_path": file_path,
            "original_name": original_name,
            "new_name": new_name,
            "new_path": new_path,
            "has_change": new_name != original_name,
            "conflict": conflict,
            "validation_warning": validation_warning,
            "sanitized": validation_warning and validation_warning.startswith("自动修正"),
            "index": index
        })
    
    return {
        "status": "success",
        "previews": results,
        "conflicts": conflicts,
        "warnings": warnings,
        "has_conflicts": len(conflicts) > 0,
        "has_warnings": len(warnings) > 0,
        "total_files": len(results),
        "changed_count": sum(1 for r in results if r["has_change"])
    }


def execute_rename_plan(
    target_dir: Path,
    rename_plan: list[dict]
) -> dict:
    snapshot_path = get_snapshot_path(target_dir)
    if snapshot_path.exists():
        raise HTTPException(
            status_code=409,
            detail="检测到未回滚的 snapshot，请先执行 Undo 后再运行重命名操作。"
        )
    
    results = []
    snapshot_operations = []
    errors = []
    
    valid_plans = [p for p in rename_plan if p.get("has_change") and not p.get("conflict")]
    
    for item in valid_plans:
        original_path = item.get("original_path")
        new_path = item.get("new_path")
        
        if not original_path or not new_path:
            results.append({
                "original_path": original_path,
                "new_path": new_path,
                "status": "skipped",
                "message": "缺少必要的路径参数"
            })
            continue
        
        try:
            original_name = Path(original_path).name
            new_name = Path(new_path).name
            
            if new_name != original_name:
                is_valid, error_reason = validate_filename(new_name)
                if not is_valid:
                    sanitized_name = sanitize_filename(new_name, fallback_prefix=Path(original_name).stem or "file")
                    if sanitized_name != new_name:
                        parent_dir = Path(new_path).parent
                        if parent_dir == Path("."):
                            new_path = sanitized_name
                        else:
                            new_path = str(parent_dir / sanitized_name)
                        
                        errors.append({
                            "original_path": original_path,
                            "original_name": original_name,
                            "original_new_name": new_name,
                            "corrected_name": sanitized_name,
                            "reason": error_reason
                        })
            
            source_path = resolve_inside_target(target_dir, original_path)
            dest_path = resolve_inside_target(target_dir, new_path)
            
            if not source_path.exists():
                results.append({
                    "original_path": original_path,
                    "new_path": new_path,
                    "status": "skipped",
                    "message": "源文件不存在"
                })
                continue
            
            if dest_path.exists() and new_path != original_path:
                results.append({
                    "original_path": original_path,
                    "new_path": new_path,
                    "status": "skipped",
                    "message": "目标路径已存在"
                })
                continue
            
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                shutil.move(str(source_path), str(dest_path))
            except OSError as e:
                error_msg = str(e)
                if "already exists" in error_msg.lower() or "exists" in error_msg.lower():
                    results.append({
                        "original_path": original_path,
                        "new_path": new_path,
                        "status": "skipped",
                        "message": f"目标文件已存在: {error_msg}"
                    })
                elif "permission" in error_msg.lower():
                    results.append({
                        "original_path": original_path,
                        "new_path": new_path,
                        "status": "error",
                        "message": f"权限不足: {error_msg}"
                    })
                else:
                    results.append({
                        "original_path": original_path,
                        "new_path": new_path,
                        "status": "error",
                        "message": f"重命名失败: {error_msg}"
                    })
                continue
            
            snapshot_operations.append({
                "action": "rename_and_move",
                "original_path": original_path,
                "new_path": new_path,
            })
            
            results.append({
                "original_path": original_path,
                "original_name": Path(original_path).name,
                "new_path": new_path,
                "new_name": Path(new_path).name,
                "status": "success",
                "absolute_original_path": str(source_path),
                "absolute_new_path": str(dest_path),
            })
        except Exception as e:
            results.append({
                "original_path": original_path,
                "new_path": new_path,
                "status": "error",
                "message": f"处理失败: {str(e)}"
            })
            errors.append({
                "original_path": original_path,
                "error": str(e)
            })
    
    if snapshot_operations:
        write_snapshot(target_dir, snapshot_operations)
        
        history_id = uuid.uuid4().hex
        write_history(
            target_dir=target_dir,
            history_id=history_id,
            operation_type="rename",
            target_path=str(target_dir),
            plan=rename_plan,
            results=results,
            snapshot_path=str(snapshot_path),
        )
    
    return {
        "status": "success",
        "executed": len([r for r in results if r["status"] == "success"]),
        "total": len(results),
        "results": results,
        "errors": errors,
        "has_errors": len(errors) > 0,
        "snapshot_path": str(snapshot_path),
        "history_id": history_id if snapshot_operations else None,
    }


def classify_file(extension: str) -> str:
    for category, extensions in CATEGORY_RULES.items():
        if extension in extensions:
            return category
    return "unknown"


def calculate_file_hash(file_path: Path, fast_mode: bool = True) -> str:
    try:
        if not file_path.exists() or not file_path.is_file():
            return ""
        
        file_size = file_path.stat().st_size
        
        if fast_mode and file_size > 10 * 1024 * 1024:
            hasher = hashlib.sha256()
            hasher.update(str(file_size).encode())
            hasher.update(b"|")
            
            with file_path.open("rb") as f:
                start_bytes = f.read(16384)
                hasher.update(start_bytes)
                hasher.update(b"|")
                
                if file_size > 65536:
                    num_samples = min(8, file_size // (2 * 1024 * 1024))
                    num_samples = max(2, num_samples)
                    
                    step = file_size // (num_samples + 1)
                    
                    for i in range(1, num_samples + 1):
                        sample_pos = step * i
                        try:
                            f.seek(sample_pos)
                            sample_bytes = f.read(4096)
                            hasher.update(sample_bytes)
                            hasher.update(b"|")
                        except (OSError, ValueError):
                            continue
                
                if file_size > 32768:
                    try:
                        end_pos = max(0, file_size - 16384)
                        f.seek(end_pos)
                        end_bytes = f.read(16384)
                        hasher.update(end_bytes)
                    except (OSError, ValueError):
                        pass
            
            return hasher.hexdigest()
        
        hasher = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(131072), b""):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    except (OSError, Exception):
        return ""


def detect_duplicates(target_dir: Path, fast_mode: bool = True) -> dict:
    files_info = scan_target_files(target_dir)
    
    size_groups = {}
    for file_info in files_info:
        size = file_info["size"]
        if size not in size_groups:
            size_groups[size] = []
        size_groups[size].append(file_info)
    
    potential_duplicates = {}
    for size, size_files in size_groups.items():
        if len(size_files) < 2:
            continue
        
        hash_groups = {}
        for file_info in size_files:
            file_path = resolve_inside_target(target_dir, file_info["path"])
            file_hash = calculate_file_hash(file_path, fast_mode)
            
            if not file_hash:
                continue
            
            if file_hash not in hash_groups:
                hash_groups[file_hash] = []
            hash_groups[file_hash].append(file_info)
        
        for file_hash, hash_files in hash_groups.items():
            if len(hash_files) >= 2:
                if file_hash not in potential_duplicates:
                    potential_duplicates[file_hash] = {
                        "hash": file_hash,
                        "size": size,
                        "files": []
                    }
                potential_duplicates[file_hash]["files"].extend(hash_files)
    
    duplicate_groups = []
    total_duplicate_size = 0
    total_duplicate_count = 0
    
    for group in potential_duplicates.values():
        files = group["files"]
        if len(files) < 2:
            continue
        
        files_sorted = sorted(files, key=lambda f: f["name"])
        
        duplicate_groups.append({
            "hash": group["hash"],
            "size": group["size"],
            "files": files_sorted,
            "recommended_keep": 0
        })
        
        total_duplicate_size += group["size"] * (len(files_sorted) - 1)
        total_duplicate_count += (len(files_sorted) - 1)
    
    return {
        "status": "success",
        "total_files_scanned": len(files_info),
        "duplicate_groups": duplicate_groups,
        "total_duplicate_count": total_duplicate_count,
        "total_duplicate_size": total_duplicate_size,
        "fast_mode": fast_mode
    }


def build_analysis(files_info: list[dict]) -> dict:
    category_counter = Counter(file["category"] for file in files_info)
    extension_counter = Counter(file["extension"] or "unknown" for file in files_info)

    recommendations = []
    if category_counter["logs"]:
        recommendations.append("检测到日志文件，可优先进行错误码、时间线和异常频率统计。")
    if category_counter["images"]:
        recommendations.append("检测到图片文件，下一步可接入 OCR 或多模态模型提取票据/截图信息。")
    if category_counter["documents"]:
        recommendations.append("检测到文档或表格，可进入结构化字段抽取与汇总。")
    if category_counter["unknown"]:
        recommendations.append("存在未知类型文件，建议保留原路径并交给后续 AI 分类器复判。")
    if not recommendations:
        recommendations.append("文件清单已生成，可继续接入 LLM 分析流水线。")

    return {
        "mode": "local-rule-engine",
        "total_files": len(files_info),
        "categories": [
            {
                "key": key,
                "label": CATEGORY_LABELS[key],
                "count": category_counter[key],
            }
            for key in CATEGORY_LABELS
            if category_counter[key]
        ],
        "extensions": [
            {"extension": extension, "count": count}
            for extension, count in extension_counter.most_common()
        ],
        "recommendations": recommendations,
    }


def get_target_dir(target_path: str | None) -> Path:
    if not target_path:
        raise HTTPException(status_code=400, detail="缺少 target_path 参数。")
    
    if not isinstance(target_path, str):
        raise HTTPException(status_code=400, detail="target_path 必须是字符串类型。")
    
    path_stripped = target_path.strip()
    if not path_stripped:
        raise HTTPException(status_code=400, detail="target_path 不能为空或仅包含空白字符。")
    
    try:
        target_dir = Path(path_stripped).expanduser().resolve()
    except (OSError, ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=400, 
            detail=f"无效的路径格式：{str(exc)}"
        ) from exc
    
    try:
        if not target_dir.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"目标文件夹不存在：{str(target_dir)}"
            )
        
        if not target_dir.is_dir():
            raise HTTPException(
                status_code=400, 
                detail=f"路径指向的不是文件夹：{str(target_dir)}"
            )
    except HTTPException:
        raise
    except OSError as exc:
        raise HTTPException(
            status_code=500, 
            detail=f"访问路径时发生错误：{str(exc)}"
        ) from exc

    return target_dir


def resolve_inside_target(target_dir: Path, relative_path: str | None) -> Path:
    if relative_path is None:
        raise HTTPException(status_code=400, detail="缺少路径参数。")
    
    if not isinstance(relative_path, str):
        raise HTTPException(status_code=400, detail="路径参数必须是字符串类型。")
    
    path_stripped = relative_path.strip()
    if not path_stripped:
        raise HTTPException(status_code=400, detail="路径参数不能为空或仅包含空白字符。")
    
    if ".." in path_stripped.split("/") or ".." in path_stripped.split("\\"):
        raise HTTPException(
            status_code=400, 
            detail=f"不允许使用父目录引用(..)：{path_stripped}"
        )
    
    try:
        normalized_target = target_dir.resolve()
        resolved_path = (normalized_target / path_stripped).resolve()
    except (OSError, ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=400, 
            detail=f"无效的路径格式：{str(exc)}"
        ) from exc
    
    try:
        if not resolved_path.is_relative_to(normalized_target):
            raise HTTPException(
                status_code=400, 
                detail=f"计划包含不安全路径：{path_stripped}（可能导致目录遍历攻击）"
            )
    except HTTPException:
        raise
    except OSError as exc:
        raise HTTPException(
            status_code=500, 
            detail=f"路径验证时发生错误：{str(exc)}"
        ) from exc
    
    return resolved_path


def to_target_relative(target_dir: Path, path: Path) -> str:
    return path.resolve().relative_to(target_dir.resolve()).as_posix()


def get_snapshot_path(target_dir: Path) -> Path:
    return target_dir / "snapshot.json"


def get_history_dir(target_dir: Path) -> Path:
    return target_dir / ".alchemy_history"


def is_valid_history_id(history_id: str) -> bool:
    if not history_id or not isinstance(history_id, str):
        return False
    if len(history_id) != 32:
        return False
    if not re.match(r'^[0-9a-f]+$', history_id):
        return False
    return True


def get_history_path(target_dir: Path, history_id: str) -> Path:
    if not is_valid_history_id(history_id):
        raise HTTPException(status_code=400, detail=f"无效的历史记录ID：{history_id}")
    
    history_dir = get_history_dir(target_dir)
    return history_dir / f"{history_id}.json"


def write_snapshot(target_dir: Path, operations: list[dict]) -> None:
    snapshot_path = get_snapshot_path(target_dir)
    snapshot = {
        "version": 1,
        "created_at": date.today().isoformat(),
        "operations": operations,
    }
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")


def write_history(
    target_dir: Path,
    history_id: str,
    operation_type: str,
    target_path: str,
    plan: list[dict],
    results: list[dict],
    snapshot_path: str = None,
) -> None:
    try:
        history_dir = get_history_dir(target_dir)
        history_dir.mkdir(parents=True, exist_ok=True)
        
        history_record = {
            "id": history_id,
            "type": operation_type,
            "target_path": target_path,
            "created_at": datetime.now().isoformat(),
            "plan": plan,
            "results": results,
            "snapshot_path": snapshot_path,
        }
        
        history_file = get_history_path(target_dir, history_id)
        history_file.write_text(json.dumps(history_record, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, Exception) as exc:
        # 历史记录写入失败不应影响主流程，只记录错误（在实际生产环境中可能需要日志记录）
        print(f"警告：历史记录写入失败：{str(exc)}")


def get_safe_sort_key(history_item: dict) -> tuple:
    created_at = history_item.get("created_at", "")
    
    if not created_at or not isinstance(created_at, str):
        return (0, "")
    
    # 尝试解析日期时间字符串
    try:
        # 尝试解析 ISO 格式日期时间
        if "T" in created_at:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            return (2, dt.isoformat())
        else:
            # 尝试解析简单日期格式
            return (1, created_at)
    except (ValueError, TypeError, Exception):
        return (0, created_at)


def list_history(target_dir: Path) -> list[dict]:
    history_dir = get_history_dir(target_dir)
    if not history_dir.exists():
        return []
    
    history_files = []
    for file in history_dir.glob("*.json"):
        try:
            content = json.loads(file.read_text(encoding="utf-8"))
            # 确保至少包含 id 字段
            if content.get("id"):
                history_files.append(content)
        except (json.JSONDecodeError, OSError, Exception):
            continue
    
    # 按创建时间倒序排列，使用安全的排序键
    history_files.sort(key=get_safe_sort_key, reverse=True)
    return history_files


def get_history(target_dir: Path, history_id: str) -> dict:
    history_file = get_history_path(target_dir, history_id)
    if not history_file.exists():
        raise HTTPException(status_code=404, detail=f"历史记录不存在：{history_id}")
    
    try:
        return json.loads(history_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"历史记录已损坏：{str(exc)}") from exc


def build_llm_prompt(files: list[FileInfo]) -> str:
    return f"""
你是 Local Data Alchemist 的文件整理智能体。
请根据文件名、扩展名、分类和文件摘要，生成严格 JSON 数组 Action Plan，并从文件摘要中提纯核心数据。
可选 action 只有 rename_and_move、move、delete、keep。
target_path 必须是相对路径，delete 和 keep 使用 null。
每个对象必须包含 file、action、target_path、reason，可选包含 extracted_info。
extracted_info.type 只能是 financial、system_log、none。
如果是报销单、发票、账单等财务内容，请提取 amount 数字；如果是日志，请在 summary 中总结核心问题。
今天日期：{date.today().isoformat()}
""".strip()


def scan_target_files(target_dir: Path) -> list[dict]:
    files_info = []
    ignored_names = {"snapshot.json"}
    ignored_dirs = {".alchemy_trash"}

    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [directory for directory in dirs if directory not in ignored_dirs]
        for filename in files:
            if filename in ignored_names:
                continue

            file_path = Path(root) / filename
            file_rel_path = file_path.relative_to(target_dir).as_posix()
            extension = file_path.suffix.lower()
            files_info.append(
                {
                    "name": filename,
                    "path": file_rel_path,
                    "extension": extension,
                    "category": classify_file(extension),
                    "size": file_path.stat().st_size,
                }
            )

    return files_info


def peek_file_content(file_path: Path, max_bytes: int = 512) -> str:
    if file_path.suffix.lower() not in TEXT_EXTENSIONS:
        return "[Binary File]"

    try:
        with file_path.open("rb") as file:
            return file.read(max_bytes).decode("utf-8", errors="ignore").strip()
    except OSError:
        return "[Unreadable File]"


def get_file_preview(file_path: Path, max_bytes: int = 10240, max_image_bytes: int = 10 * 1024 * 1024) -> dict:
    extension = file_path.suffix.lower()
    file_name = file_path.name
    
    # 安全获取文件大小
    try:
        file_size = file_path.stat().st_size
    except (OSError, Exception):
        file_size = 0

    preview = {
        "name": file_name,
        "path": str(file_path),
        "extension": extension,
        "size": file_size,
        "type": "unknown",
        "content": None,
        "truncated": False,
    }

    # 文本文件预览
    if extension in TEXT_EXTENSIONS:
        preview["type"] = "text"
        try:
            with file_path.open("rb") as file:
                content_bytes = file.read(max_bytes + 1)
                if len(content_bytes) > max_bytes:
                    preview["truncated"] = True
                    content_bytes = content_bytes[:max_bytes]
                preview["content"] = content_bytes.decode("utf-8", errors="ignore")
        except (OSError, Exception):
            preview["content"] = "[无法读取文件]"
        return preview

    # 图片文件预览
    image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
    if extension in image_extensions:
        preview["type"] = "image"
        
        # 检查图片文件大小，避免大图片导致内存问题
        if file_size > max_image_bytes:
            preview["content"] = f"[图片文件过大，超过 {max_image_bytes // 1024 // 1024}MB，不支持预览]"
            return preview
        
        try:
            with file_path.open("rb") as file:
                preview["content"] = base64.b64encode(file.read()).decode("utf-8")
        except (OSError, Exception):
            preview["content"] = None
        return preview

    # PDF文件预览
    if extension == ".pdf":
        preview["type"] = "pdf"
        preview["content"] = "PDF文件预览功能待实现"
        return preview

    # 其他二进制文件
    preview["type"] = "binary"
    preview["content"] = "[二进制文件，不支持预览]"
    return preview


def strip_markdown_fence(content: str) -> str:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    return cleaned


def should_translate_to_zh(text: str | None) -> bool:
    if not isinstance(text, str):
        return False
    stripped = text.strip()
    if not stripped:
        return False
    if re.search(r"[\u4e00-\u9fff]", stripped):
        return False
    if not re.search(r"[A-Za-z]", stripped):
        return False
    ascii_letters = sum(1 for ch in stripped if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))
    return (ascii_letters / max(len(stripped), 1)) >= 0.12


def build_openai_client(timeout_seconds: int) -> OpenAI:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    api_base = (os.getenv("OPENAI_API_BASE") or "").strip()
    return OpenAI(
        api_key=api_key,
        base_url=api_base,
        http_client=httpx.Client(trust_env=False, timeout=timeout_seconds),
    )


def translate_texts_to_zh(texts: list[str], timeout_seconds: int, model: str) -> list[str]:
    if not texts:
        return []

    client = build_openai_client(timeout_seconds)
    system_prompt = (
        "你是专业翻译器。请把输入的 JSON 数组中的每一项翻译为简体中文。"
        "必须保留文件路径、错误码、类名/函数名、代码片段、版本号、数字与时间戳原样，不要擅自改写。"
        "必须只返回合法 JSON 数组（字符串数组），长度必须与输入一致，不要输出任何 Markdown。"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(texts, ensure_ascii=False)},
            ],
            temperature=0,
        )
    except Exception:
        return texts

    content = response.choices[0].message.content or ""
    try:
        translated = json.loads(strip_markdown_fence(content))
    except json.JSONDecodeError:
        translated = None

    if not isinstance(translated, list) or len(translated) != len(texts):
        strict_prompt = (
            "只返回 JSON 字符串数组。禁止输出任何解释、前后缀、Markdown。"
            "必须逐条翻译为简体中文并保持数组长度一致。"
        )
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(texts, ensure_ascii=False)},
                    {"role": "assistant", "content": strict_prompt},
                ],
                temperature=0,
            )
            content = response.choices[0].message.content or ""
            translated = json.loads(strip_markdown_fence(content))
        except Exception:
            return texts
        if not isinstance(translated, list) or len(translated) != len(texts):
            return texts

    out: list[str] = []
    for index, item in enumerate(translated):
        if isinstance(item, str) and item.strip():
            out.append(item)
        else:
            out.append(texts[index])
    return out


def parse_llm_plan(content: str) -> list[ActionPlanItem]:
    try:
        raw_plan = json.loads(strip_markdown_fence(content))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"LLM 返回的计划不是合法 JSON：{exc}") from exc

    if isinstance(raw_plan, dict) and isinstance(raw_plan.get("plan"), list):
        raw_plan = raw_plan["plan"]

    if not isinstance(raw_plan, list):
        raise HTTPException(status_code=502, detail="LLM 返回的计划必须是 JSON 数组。")

    try:
        plan = [ActionPlanItem(**item) for item in raw_plan]
    except (TypeError, ValidationError) as exc:
        raise HTTPException(status_code=502, detail=f"LLM 返回的计划结构不符合约定：{exc}") from exc
    for item in plan:
        if item.action not in ALLOWED_ACTIONS:
            raise HTTPException(status_code=502, detail=f"LLM 返回了不支持的操作：{item.action}")

    return plan


def generate_local_fallback_plan(files: list[FileInfo], reason: str) -> list[ActionPlanItem]:
    today = date.today().isoformat()
    plan = []

    for file in files:
        stem = Path(file.name).stem.lower().replace(" ", "-")

        if file.category == "logs":
            plan.append(
                ActionPlanItem(
                    file=file.path,
                    action="rename_and_move",
                    target_path=f"logs/{today}-{stem}.log",
                    reason=f"本地兜底计划：LLM 不可用（{reason}），该文件被规则识别为日志。",
                    extracted_info={
                        "type": "system_log",
                        "amount": None,
                        "currency": None,
                        "date": None,
                        "merchant": None,
                        "document_id": None,
                        "title": "日志归档",
                        "severity": "medium",
                        "error_code": None,
                        "root_cause": "",
                        "recommended_action": "请检查网络或 LLM 配置后重新生成计划。",
                        "summary": "LLM 不可用，已按日志文件进入归档队列。",
                    },
                )
            )
        elif file.extension in {".csv", ".xlsx", ".xls"}:
            plan.append(
                ActionPlanItem(
                    file=file.path,
                    action="move",
                    target_path=f"financial/{file.name}",
                    reason=f"本地兜底计划：LLM 不可用（{reason}），表格文件疑似财务/结构化数据。",
                    extracted_info={
                        "type": "financial",
                        "amount": None,
                        "currency": "CNY",
                        "date": None,
                        "merchant": None,
                        "document_id": None,
                        "title": "表格疑似财务/结构化数据",
                        "severity": None,
                        "error_code": None,
                        "root_cause": "",
                        "recommended_action": "请检查网络或 LLM 配置后重新生成计划。",
                        "summary": "LLM 不可用，金额未提取。",
                    },
                )
            )
        elif file.name.lower().startswith(("tmp", "temp", "cache")) or file.extension in {".tmp", ".cache"}:
            plan.append(
                ActionPlanItem(
                    file=file.path,
                    action="delete",
                    target_path=None,
                    reason=f"本地兜底计划：LLM 不可用（{reason}），文件名疑似临时缓存。",
                    extracted_info={
                        "type": "none",
                        "amount": None,
                        "currency": None,
                        "date": None,
                        "merchant": None,
                        "document_id": None,
                        "title": "",
                        "severity": None,
                        "error_code": None,
                        "root_cause": "",
                        "recommended_action": "",
                        "summary": "",
                    },
                )
            )
        else:
            plan.append(
                ActionPlanItem(
                    file=file.path,
                    action="keep",
                    target_path=None,
                    reason=f"本地兜底计划：LLM 不可用（{reason}），保留等待人工复核。",
                    extracted_info={
                        "type": "none",
                        "amount": None,
                        "currency": None,
                        "date": None,
                        "merchant": None,
                        "document_id": None,
                        "title": "",
                        "severity": None,
                        "error_code": None,
                        "root_cause": "",
                        "recommended_action": "",
                        "summary": "",
                    },
                )
            )

    return plan


def build_file_snippets(target_dir: Path, files: list[FileInfo]) -> list[dict]:
    snippets = []
    for file in files:
        file_path = resolve_inside_target(target_dir, file.path)
        snippets.append(
            {
                "filename": file.path,
                "extension": file.extension,
                "category": file.category,
                "size": file.size,
                "snippet": peek_file_content(file_path),
            }
        )
    return snippets


def call_llm_generate_plan(file_snippets: list[dict]) -> list[ActionPlanItem]:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    api_base = (os.getenv("OPENAI_API_BASE") or "").strip()
    model = (os.getenv("OPENAI_MODEL") or "").strip()
    timeout_seconds_raw = (os.getenv("OPENAI_TIMEOUT_SECONDS") or "").strip()
    timeout_seconds = 180
    if timeout_seconds_raw:
        try:
            timeout_seconds = int(float(timeout_seconds_raw))
        except ValueError:
            timeout_seconds = 180

    missing = [
        name
        for name, value in {
            "OPENAI_API_KEY": api_key,
            "OPENAI_API_BASE": api_base,
            "OPENAI_MODEL": model,
        }.items()
        if not value
    ]
    if missing:
        raise HTTPException(status_code=500, detail=f"缺少 LLM 环境变量：{', '.join(missing)}")

    client = OpenAI(
        api_key=api_key,
        base_url=api_base,
        http_client=httpx.Client(trust_env=False, timeout=timeout_seconds),
    )
    system_prompt = (
        "你是高级数据整理专家。你需要根据文件名、文件类型、大小和内容摘要生成文件整理 Action Plan，并提纯文件中的核心数据。"
        "必须只返回合法 JSON 数组，不要输出任何 Markdown 标记，不要使用 ```json，不要解释。"
        "所有自然语言字段必须使用简体中文输出：reason、extracted_info.title、extracted_info.summary、extracted_info.root_cause、extracted_info.recommended_action、extracted_info.merchant。"
        "注意：file 必须原样使用输入的文件相对路径；action 与 severity 必须使用约定的英文枚举值；currency 仍使用三位货币码（如 CNY/USD/UNKNOWN）；date 使用 YYYY-MM-DD。"
        "输出数组中的每个对象必须严格包含 file、action、target_path、reason 字段，并可以包含 extracted_info 字段。"
        "extracted_info 必须是对象，并且必须包含 type 字段，type 只能是 financial、system_log、none。"
        "当 type=financial 时：请尽可能提取 amount（纯数字，允许小数；无则为 null）、currency（如 CNY/USD，无法判断用 UNKNOWN）、date（YYYY-MM-DD 或 null）、merchant（商户/主体或 null）、document_id（票据号/发票号/订单号或 null）、title（简短标题）。summary 可选，写 1 句概括。"
        "当 type=system_log 时：请提取 title（简短问题标题）、severity（low|medium|high|critical）、error_code（字符串或 null）、root_cause（推测原因，无法判断为空字符串）、recommended_action（建议动作，无法判断为空字符串）、summary（1-2 句核心现象）。amount/currency/date/merchant/document_id 必须为 null 或空。"
        "当 type=none 时：amount=null、currency=null、date=null、merchant=null、document_id=null、title=\"\"、severity=null、error_code=null、root_cause=\"\"、recommended_action=\"\"、summary=\"\"。"
        "file 字段必须原样使用输入 files[].filename，不要改成 basename。"
        "action 只能是 rename_and_move、move、delete、keep。"
        "target_path 必须是 temp 上传目录内的相对路径；delete 和 keep 的 target_path 必须为 null。"
    )
    user_prompt = {
        "today": date.today().isoformat(),
        "input_format": [{"filename": "error.log", "snippet": "Traceback (most recent call...)"}],
        "files": file_snippets,
    }

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
            ],
            temperature=0,
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=502, detail="LLM 认证失败：百炼返回 invalid_api_key，请检查 backend/.env 中的 OPENAI_API_KEY 是否为当前账号的有效百炼 API Key。") from exc
    except APIConnectionError as exc:
        raise HTTPException(status_code=502, detail=f"LLM 连接失败：{exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM 请求失败：{exc}") from exc

    content = response.choices[0].message.content
    if not content:
        raise HTTPException(status_code=502, detail="LLM 返回为空。")

    return parse_llm_plan(content)


@app.get("/api/llm_debug")
def llm_debug():
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    api_base = (os.getenv("OPENAI_API_BASE") or "").strip()
    model = (os.getenv("OPENAI_MODEL") or "").strip()
    timeout_seconds_raw = (os.getenv("OPENAI_TIMEOUT_SECONDS") or "").strip()
    fingerprint = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:10] if api_key else None
    timeout_seconds = 180
    if timeout_seconds_raw:
        try:
            timeout_seconds = int(float(timeout_seconds_raw))
        except ValueError:
            timeout_seconds = 180
    return {
        "status": "success",
        "env_path": str(ENV_PATH),
        "env_exists": ENV_PATH.exists(),
        "api_base": api_base,
        "model": model,
        "timeout_seconds": timeout_seconds,
        "api_key_len": len(api_key),
        "api_key_fingerprint": fingerprint,
    }


async def generate_plan_impl(request: PlanRequest) -> dict:
    target_dir = get_target_dir(request.target_path)
    files_info = scan_target_files(target_dir)
    files = [FileInfo(**file) for file in files_info]
    prompt = build_llm_prompt(files)
    file_snippets = build_file_snippets(target_dir, files)
    llm_error = None
    mode = "real-llm"
    try:
        plan = call_llm_generate_plan(file_snippets)
    except HTTPException as exc:
        llm_error = exc.detail
        if (os.getenv("ALLOW_MOCK_LLM_FALLBACK", "true") or "").strip().lower() not in {"1", "true", "yes"}:
            raise

        mode = "local-fallback-after-llm-error"
        plan = generate_local_fallback_plan(files, str(exc.detail))

    translation_stats = None
    if (os.getenv("FORCE_ZH_TRANSLATION", "true") or "").strip().lower() in {"1", "true", "yes"}:
        timeout_seconds_raw = (os.getenv("OPENAI_TIMEOUT_SECONDS") or "").strip()
        timeout_seconds = 180
        if timeout_seconds_raw:
            try:
                timeout_seconds = int(float(timeout_seconds_raw))
            except ValueError:
                timeout_seconds = 180
        model = (os.getenv("OPENAI_MODEL") or "").strip()
        translate_model = (os.getenv("OPENAI_TRANSLATE_MODEL") or model).strip() or model

        replacements: dict[str, str] = {}
        texts_to_translate: list[str] = []

        def enqueue(text: str | None) -> None:
            if not should_translate_to_zh(text):
                return
            value = (text or "").strip()
            if not value:
                return
            if value in replacements:
                return
            if value in texts_to_translate:
                return
            texts_to_translate.append(value)

        for item in plan:
            enqueue(item.reason)
            info = item.extracted_info if isinstance(item.extracted_info, dict) else None
            if not info:
                continue
            enqueue(info.get("title"))
            enqueue(info.get("summary"))
            enqueue(info.get("root_cause"))
            enqueue(info.get("recommended_action"))
            enqueue(info.get("merchant"))

        translated = translate_texts_to_zh(texts_to_translate, timeout_seconds=timeout_seconds, model=translate_model)
        replaced_count = 0
        for original, translated_text in zip(texts_to_translate, translated, strict=False):
            replacements[original] = translated_text
            if translated_text != original:
                replaced_count += 1

        for item in plan:
            if isinstance(item.reason, str):
                stripped = item.reason.strip()
                if stripped in replacements:
                    item.reason = replacements[stripped]
            info = item.extracted_info if isinstance(item.extracted_info, dict) else None
            if not info:
                continue
            for key in ("title", "summary", "root_cause", "recommended_action", "merchant"):
                value = info.get(key)
                if isinstance(value, str):
                    stripped = value.strip()
                    if stripped in replacements:
                        info[key] = replacements[stripped]

        translation_stats = {
            "requested": len(texts_to_translate),
            "replaced": replaced_count,
            "model": translate_model,
        }

    return {
        "status": "success",
        "mode": mode,
        "llm_error": llm_error,
        "target_path": str(target_dir),
        "prompt": prompt,
        "analysis": build_analysis(files_info),
        "files": file_snippets,
        "file_inventory": files_info,
        "translation_stats": translation_stats,
        "reasoning_trace": [
            f"已锁定本地目标目录：{target_dir}",
            f"本地扫描完成：共发现 {len(file_snippets)} 个文件",
            "已读取文本文件摘要：每个文件最多 512 字节",
            "已请求生成仅 JSON 的炼金计划（包含 extracted_info）" if not llm_error else f"LLM 不可用，已启用本地兜底计划：{llm_error}",
        ],
        "plan": [item.dict() for item in plan],
    }


async def lock_folder_impl(request: FolderRequest) -> dict:
    target_dir = get_target_dir(request.target_path)
    files_info = scan_target_files(target_dir)
    return {
        "status": "success",
        "target_path": str(target_dir),
        "files": files_info,
        "analysis": build_analysis(files_info),
    }


async def execute_plan_impl(request: ExecutePlanRequest) -> dict:
    target_dir = get_target_dir(request.target_path)
    results = []
    snapshot_path = get_snapshot_path(target_dir)

    if snapshot_path.exists():
        raise HTTPException(status_code=409, detail="检测到未回滚的 snapshot，请先执行 Undo 后再运行新的炼金计划。")

    snapshot_operations = []

    for item in request.plan:
        if item.action not in ALLOWED_ACTIONS:
            raise HTTPException(status_code=400, detail=f"不支持的操作：{item.action}")

        if item.action in {"rename_and_move", "move"}:
            if not item.target_path:
                raise HTTPException(status_code=400, detail=f"{item.action} 操作缺少 target_path。")

            source_path = resolve_inside_target(target_dir, item.file)
            target_path = resolve_inside_target(target_dir, item.target_path)
            if source_path.exists() and target_path.exists():
                raise HTTPException(status_code=409, detail=f"目标路径已存在：{item.target_path}")

    for item in request.plan:
        if item.action not in ALLOWED_ACTIONS:
            raise HTTPException(status_code=400, detail=f"不支持的操作：{item.action}")

        source_path = resolve_inside_target(target_dir, item.file)
        if not source_path.exists():
            results.append(
                {
                    "file": item.file,
                    "action": item.action,
                    "original_path": item.file,
                    "new_path": None,
                    "status": "skipped",
                    "message": "源文件不存在，可能已被处理。",
                }
            )
            continue

        if item.action == "delete":
            trash_path = resolve_inside_target(
                target_dir,
                f".alchemy_trash/{uuid.uuid4().hex}/{Path(item.file).name}",
            )
            trash_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_path), str(trash_path))
            snapshot_operations.append(
                {
                    "action": item.action,
                    "original_path": item.file,
                    "new_path": to_target_relative(target_dir, trash_path),
                }
            )
            results.append(
                {
                    "file": item.file,
                    "action": item.action,
                    "original_path": item.file,
                    "new_path": to_target_relative(target_dir, trash_path),
                    "absolute_original_path": str(source_path),
                    "absolute_new_path": str(trash_path),
                    "status": "success",
                }
            )
            continue

        if item.action == "keep":
            results.append(
                {
                    "file": item.file,
                    "action": item.action,
                    "original_path": item.file,
                    "new_path": item.file,
                    "absolute_original_path": str(source_path),
                    "absolute_new_path": str(source_path),
                    "status": "success",
                }
            )
            continue

        target_path = resolve_inside_target(target_dir, item.target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(source_path), str(target_path))
        snapshot_operations.append(
            {
                "action": item.action,
                "original_path": item.file,
                "new_path": item.target_path,
            }
        )
        results.append(
            {
                "file": item.file,
                "action": item.action,
                "original_path": item.file,
                "target_path": item.target_path,
                "new_path": item.target_path,
                "absolute_original_path": str(source_path),
                "absolute_new_path": str(target_path),
                "status": "success",
            }
        )

    write_snapshot(target_dir, snapshot_operations)

    # 保存操作历史记录
    history_id = uuid.uuid4().hex
    plan_dict = [item.dict() for item in request.plan] if request.plan else []
    
    write_history(
        target_dir=target_dir,
        history_id=history_id,
        operation_type="execute",
        target_path=str(target_dir),
        plan=plan_dict,
        results=results,
        snapshot_path=str(snapshot_path),
    )

    return {
        "status": "success",
        "executed": len(results),
        "results": results,
        "snapshot": snapshot_path.name,
        "snapshot_path": str(snapshot_path),
        "history_id": history_id,
    }


async def undo_plan_impl(request: UndoPlanRequest) -> dict:
    target_dir = get_target_dir(request.target_path)
    snapshot_path = get_snapshot_path(target_dir)

    if not snapshot_path.exists():
        raise HTTPException(status_code=404, detail="未找到可回滚的 snapshot。")

    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"snapshot.json 已损坏：{exc}") from exc

    operations = snapshot.get("operations", [])
    results = []

    for operation in reversed(operations):
        original_path = operation.get("original_path")
        new_path = operation.get("new_path")
        if not original_path or not new_path:
            continue

        current_path = resolve_inside_target(target_dir, new_path)
        restore_path = resolve_inside_target(target_dir, original_path)

        if not current_path.exists():
            results.append(
                {
                    "file": original_path,
                    "status": "skipped",
                    "message": "回滚源文件不存在。",
                }
            )
            continue

        restore_path.parent.mkdir(parents=True, exist_ok=True)
        if restore_path.exists():
            raise HTTPException(status_code=409, detail=f"回滚目标路径已存在：{original_path}")

        shutil.move(str(current_path), str(restore_path))
        results.append(
            {
                "file": original_path,
                "original_path": original_path,
                "restored_from": new_path,
                "absolute_restore_path": str(restore_path),
                "absolute_previous_path": str(current_path),
                "status": "success",
            }
        )

    snapshot_path.unlink()

    trash_dir = target_dir / ".alchemy_trash"
    if trash_dir.exists():
        shutil.rmtree(trash_dir)

    # 保存回滚操作历史记录
    history_id = uuid.uuid4().hex
    
    write_history(
        target_dir=target_dir,
        history_id=history_id,
        operation_type="undo",
        target_path=str(target_dir),
        plan=[],
        results=results,
        snapshot_path=None,
    )

    return {
        "status": "success",
        "message": "已恢复到炼金前状态",
        "restored": len(results),
        "results": results,
        "history_id": history_id,
    }


@app.get("/select_folder")
@app.get("/api/select_folder")
def select_folder():
    root = None
    try:
        # 初始化一个隐藏的 Tkinter 根窗口
        root = tk.Tk()
        # 极客小细节：强行让弹窗置顶，防止它偷偷躲在浏览器网页后面导致你找不到
        root.attributes('-topmost', True)
        root.withdraw() # 隐藏主窗口
        
        # 呼出系统原生的文件夹选择对话框
        selected_path = filedialog.askdirectory(
            title='Select Local Data Alchemist Target',
            initialdir=os.path.expanduser('~')
        )

        # 如果用户点了取消或关掉了弹窗，filedialog.askdirectory 会返回空字符串或空元组
        if not selected_path or selected_path == () or (isinstance(selected_path, str) and not selected_path.strip()):
            return {"status": "cancelled", "target_path": None}

        # --- 以下保留你原有的处理逻辑 ---
        target_dir = get_target_dir(selected_path)
        files_info = scan_target_files(target_dir)
        return {
            "status": "success",
            "target_path": str(target_dir),
            "files": files_info,
            "analysis": build_analysis(files_info),
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"本地文件夹选择器启动失败：{str(exc)}") from exc
    finally:
        # 确保根窗口总是被销毁，释放资源
        if root:
            try:
                root.update()
                root.destroy()
            except Exception:
                # 忽略销毁窗口时的异常
                pass


@app.post("/lock_folder")
@app.post("/api/lock_folder")
async def lock_folder(request: FolderRequest):
    return await lock_folder_impl(request)


@app.post("/generate_plan")
@app.post("/api/generate_plan")
async def generate_plan(request: PlanRequest):
    return await generate_plan_impl(request)


@app.post("/execute_plan")
@app.post("/api/execute_plan")
async def execute_plan(request: ExecutePlanRequest):
    return await execute_plan_impl(request)


@app.post("/undo_plan")
@app.post("/api/undo_plan")
async def undo_plan(request: UndoPlanRequest):
    return await undo_plan_impl(request)


@app.post("/preview_file")
@app.post("/api/preview_file")
async def preview_file(request: FilePreviewRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        file_path = resolve_inside_target(target_dir, request.file_path)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在：{request.file_path}")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail=f"不是文件：{request.file_path}")
        
        preview = get_file_preview(file_path)
        return {
            "status": "success",
            "preview": preview
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文件预览失败：{str(exc)}") from exc


@app.post("/list_history")
@app.post("/api/list_history")
async def list_history(request: ListHistoryRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        history_list = list_history(target_dir)
        
        # 简化返回结果，只返回关键信息
        simplified_history = []
        for item in history_list:
            simplified_history.append({
                "id": item.get("id"),
                "type": item.get("type"),
                "target_path": item.get("target_path"),
                "created_at": item.get("created_at"),
                "results_count": len(item.get("results", [])),
                "snapshot_path": item.get("snapshot_path"),
            })
        
        return {
            "status": "success",
            "history": simplified_history,
            "total": len(simplified_history),
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败：{str(exc)}") from exc


@app.post("/get_history")
@app.post("/api/get_history")
async def get_history_detail(request: GetHistoryRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        history = get_history(target_dir, request.history_id)
        
        return {
            "status": "success",
            "history": history,
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取历史记录详情失败：{str(exc)}") from exc


@app.post("/detect_duplicates")
@app.post("/api/detect_duplicates")
async def api_detect_duplicates(request: DetectDuplicatesRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        result = detect_duplicates(target_dir, request.fast_mode)
        return result
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"检测重复文件失败：{str(exc)}") from exc


@app.post("/keep_duplicate")
@app.post("/api/keep_duplicate")
async def api_keep_duplicate(request: KeepDuplicateRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        
        if not request.keep_file:
            raise HTTPException(status_code=400, detail="请指定要保留的文件")
        
        if not request.duplicate_files or len(request.duplicate_files) == 0:
            raise HTTPException(status_code=400, detail="请指定要删除的重复文件")
        
        keep_path = resolve_inside_target(target_dir, request.keep_file)
        if not keep_path.exists():
            raise HTTPException(status_code=404, detail=f"要保留的文件不存在：{request.keep_file}")
        
        results = []
        snapshot_operations = []
        
        for dup_file in request.duplicate_files:
            dup_path = resolve_inside_target(target_dir, dup_file)
            
            if not dup_path.exists():
                results.append({
                    "file": dup_file,
                    "status": "skipped",
                    "message": "文件不存在"
                })
                continue
            
            trash_path = resolve_inside_target(
                target_dir,
                f".alchemy_trash/{uuid.uuid4().hex}/{Path(dup_file).name}",
            )
            trash_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(dup_path), str(trash_path))
            
            snapshot_operations.append({
                "action": "delete",
                "original_path": dup_file,
                "new_path": to_target_relative(target_dir, trash_path),
            })
            
            results.append({
                "file": dup_file,
                "action": "delete",
                "original_path": dup_file,
                "new_path": to_target_relative(target_dir, trash_path),
                "absolute_original_path": str(dup_path),
                "absolute_new_path": str(trash_path),
                "status": "success",
            })
        
        if snapshot_operations:
            snapshot_path = get_snapshot_path(target_dir)
            if not snapshot_path.exists():
                write_snapshot(target_dir, snapshot_operations)
                
                history_id = uuid.uuid4().hex
                write_history(
                    target_dir=target_dir,
                    history_id=history_id,
                    operation_type="deduplicate",
                    target_path=str(target_dir),
                    plan=[{
                        "file": request.keep_file,
                        "action": "keep",
                        "target_path": None,
                        "reason": "去重操作 - 保留此文件",
                        "extracted_info": None
                    }],
                    results=results,
                    snapshot_path=str(snapshot_path),
                )
        
        return {
            "status": "success",
            "kept_file": request.keep_file,
            "deleted_count": len([r for r in results if r["status"] == "success"]),
            "results": results
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"处理重复文件失败：{str(exc)}") from exc


@app.get("/list_templates")
@app.get("/api/list_templates")
async def api_list_templates():
    try:
        templates = load_all_templates()
        
        simplified = []
        for template in templates:
            simplified.append({
                "id": template.get("id"),
                "name": template.get("name"),
                "description": template.get("description"),
                "icon": template.get("icon", "📁"),
                "is_builtin": template.get("is_builtin", False),
                "created_at": template.get("created_at"),
                "updated_at": template.get("updated_at"),
                "rules_count": len(template.get("rules", [])),
            })
        
        return {
            "status": "success",
            "templates": simplified,
            "total": len(simplified),
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取模板列表失败：{str(exc)}") from exc


@app.post("/get_template")
@app.post("/api/get_template")
async def api_get_template(request: GetTemplateRequest):
    try:
        template = find_template(request.template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"模板不存在：{request.template_id}")
        
        return {
            "status": "success",
            "template": template,
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取模板详情失败：{str(exc)}") from exc


@app.post("/save_template")
@app.post("/api/save_template")
async def api_save_template(request: SaveTemplateRequest):
    try:
        template_data = request.template
        
        if not template_data:
            raise HTTPException(status_code=400, detail="模板数据不能为空")
        
        if not template_data.get("name"):
            raise HTTPException(status_code=400, detail="模板名称不能为空")
        
        saved = save_user_template(template_data)
        
        return {
            "status": "success",
            "template": saved,
            "message": "模板保存成功",
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"保存模板失败：{str(exc)}") from exc


@app.post("/delete_template")
@app.post("/api/delete_template")
async def api_delete_template(request: DeleteTemplateRequest):
    try:
        if request.template_id.startswith("builtin-"):
            raise HTTPException(status_code=400, detail="内置模板不可删除")
        
        success = delete_user_template(request.template_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"模板不存在或无法删除：{request.template_id}")
        
        return {
            "status": "success",
            "message": "模板删除成功",
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"删除模板失败：{str(exc)}") from exc


@app.post("/apply_template")
@app.post("/api/apply_template")
async def api_apply_template(request: ApplyTemplateRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        
        template = find_template(request.template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"模板不存在：{request.template_id}")
        
        files_info = scan_target_files(target_dir)
        
        plan = apply_template_to_files(template, files_info, target_dir)
        
        return {
            "status": "success",
            "mode": "template-apply",
            "template_id": request.template_id,
            "template_name": template.get("name"),
            "target_path": str(target_dir),
            "analysis": build_analysis(files_info),
            "files": build_file_snippets(target_dir, [FileInfo(**f) for f in files_info]),
            "file_inventory": files_info,
            "plan": plan,
            "reasoning_trace": [
                f"已锁定本地目标目录：{target_dir}",
                f"本地扫描完成：共发现 {len(files_info)} 个文件",
                f"应用模板：{template.get('name')}",
                f"生成计划：共 {len(plan)} 条 Action",
            ],
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"应用模板失败：{str(exc)}") from exc


@app.post("/rename_preview")
@app.post("/api/rename_preview")
async def api_rename_preview(request: RenamePreviewRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        
        result = generate_rename_preview(
            target_dir,
            request.selected_files,
            request.rules
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成重命名预览失败：{str(exc)}") from exc


@app.post("/rename_execute")
@app.post("/api/rename_execute")
async def api_rename_execute(request: RenameExecuteRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        
        result = execute_rename_plan(
            target_dir,
            request.rename_plan
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"执行重命名失败：{str(exc)}") from exc


@app.post("/dashboard_stats")
@app.post("/api/dashboard_stats")
async def api_dashboard_stats(request: DashboardStatsRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        
        files_info = scan_target_files(target_dir)
        
        stats = calculate_dashboard_stats(target_dir, files_info)
        
        return {
            "status": "success",
            "target_path": str(target_dir),
            "stats": stats,
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成仪表盘统计失败：{str(exc)}") from exc


@app.post("/preview_plan")
@app.post("/api/preview_plan")
async def api_preview_plan(request: PreviewPlanRequest):
    try:
        if not request.target_path:
            raise HTTPException(status_code=400, detail="缺少目标目录")
        
        if not request.plan or len(request.plan) == 0:
            raise HTTPException(status_code=400, detail="计划为空")
        
        target_dir = get_target_dir(request.target_path)
        
        result = preview_plan_impl(target_dir, request.plan)
        
        return result
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"计划预检查失败：{str(exc)}") from exc


@app.post("/multi_scan")
@app.post("/api/multi_scan")
async def api_multi_scan(request: MultiTargetRequest):
    try:
        if not request.target_paths or len(request.target_paths) == 0:
            raise HTTPException(status_code=400, detail="至少需要指定一个目标目录")
        
        raw_paths = request.target_paths or []
        processed_paths = []
        seen_paths = set()
        ignored_paths_info = []
        
        for path in raw_paths:
            if not path or not isinstance(path, str):
                ignored_paths_info.append({
                    "path": path,
                    "reason": "空路径或非字符串类型"
                })
                continue
            
            path_stripped = path.strip()
            if not path_stripped:
                ignored_paths_info.append({
                    "path": path,
                    "reason": "仅包含空白字符"
                })
                continue
            
            try:
                normalized_path = str(Path(path_stripped).resolve())
            except Exception as path_exc:
                ignored_paths_info.append({
                    "path": path_stripped,
                    "reason": f"路径解析失败: {str(path_exc)}"
                })
                continue
            
            if normalized_path in seen_paths:
                ignored_paths_info.append({
                    "path": path_stripped,
                    "normalized_path": normalized_path,
                    "reason": "重复路径"
                })
                continue
            
            seen_paths.add(normalized_path)
            processed_paths.append(normalized_path)
        
        if len(processed_paths) == 0:
            if len(ignored_paths_info) > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"所有路径都被过滤。原因: {ignored_paths_info[0].get('reason', '未知')}"
                )
            else:
                raise HTTPException(status_code=400, detail="至少需要指定一个有效的目标目录")
        
        results = []
        for i, target_path in enumerate(processed_paths):
            result = scan_and_analyze_single_path(target_path, i)
            results.append(result)
        
        success_count = sum(1 for r in results if r["status"] == "success")
        total_files = sum(r["file_count"] for r in results)
        total_size = sum(r["total_size"] for r in results)
        
        all_files = []
        all_file_inventory = []
        all_categories = {
            "images": {"count": 0, "size": 0},
            "documents": {"count": 0, "size": 0},
            "archives": {"count": 0, "size": 0},
            "code": {"count": 0, "size": 0},
            "logs": {"count": 0, "size": 0},
            "unknown": {"count": 0, "size": 0},
        }
        
        for result in results:
            if result["status"] == "success":
                all_files.extend(result.get("files", []))
                all_file_inventory.extend([
                    {**f, "source_path": result["target_path"]}
                    for f in result.get("file_inventory", [])
                ])
                
                analysis = result.get("analysis")
                if analysis and isinstance(analysis, dict):
                    categories = analysis.get("categories")
                    if categories and isinstance(categories, list):
                        for cat in categories:
                            if isinstance(cat, dict):
                                key = cat.get("key", "unknown")
                                if key in all_categories:
                                    count = cat.get("count", 0)
                                    size = cat.get("size", 0)
                                    if isinstance(count, (int, float)):
                                        all_categories[key]["count"] += count
                                    if isinstance(size, (int, float)):
                                        all_categories[key]["size"] += size
        
        merged_analysis = {
            "mode": "multi-directory-scan",
            "target_paths": [r["target_path"] for r in results if r.get("status") == "success"],
            "total_files": total_files,
            "total_size": total_size,
            "categories": [
                {"key": k, "count": v["count"], "size": v["size"]}
                for k, v in all_categories.items()
                if v["count"] > 0
            ],
            "directories_count": success_count,
            "raw_input_paths": raw_paths,
            "processed_paths_count": len(processed_paths),
            "ignored_paths_count": len(ignored_paths_info),
            "ignored_paths": ignored_paths_info if len(ignored_paths_info) <= 10 else ignored_paths_info[:10] + [{"note": f"还有 {len(ignored_paths_info) - 10} 个被忽略的路径未显示"}],
        }
        
        return {
            "status": "success",
            "results": results,
            "success_count": success_count,
            "failed_count": len(results) - success_count,
            "total_files": total_files,
            "total_size": total_size,
            "merged_files": all_files,
            "merged_file_inventory": all_file_inventory,
            "merged_analysis": merged_analysis,
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"多目录扫描失败：{str(exc)}") from exc


@app.post("/multi_generate_plan")
@app.post("/api/multi_generate_plan")
async def api_multi_generate_plan(request: MultiTargetRequest):
    try:
        if not request.target_paths or len(request.target_paths) == 0:
            raise HTTPException(status_code=400, detail="至少需要指定一个目标目录")
        
        raw_paths = request.target_paths or []
        processed_paths = []
        seen_paths = set()
        ignored_paths_info = []
        
        for path in raw_paths:
            if not path or not isinstance(path, str):
                ignored_paths_info.append({
                    "path": path,
                    "reason": "空路径或非字符串类型"
                })
                continue
            
            path_stripped = path.strip()
            if not path_stripped:
                ignored_paths_info.append({
                    "path": path,
                    "reason": "仅包含空白字符"
                })
                continue
            
            try:
                normalized_path = str(Path(path_stripped).resolve())
            except Exception as path_exc:
                ignored_paths_info.append({
                    "path": path_stripped,
                    "reason": f"路径解析失败: {str(path_exc)}"
                })
                continue
            
            if normalized_path in seen_paths:
                ignored_paths_info.append({
                    "path": path_stripped,
                    "normalized_path": normalized_path,
                    "reason": "重复路径"
                })
                continue
            
            seen_paths.add(normalized_path)
            processed_paths.append(normalized_path)
        
        if len(processed_paths) == 0:
            if len(ignored_paths_info) > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"所有路径都被过滤。原因: {ignored_paths_info[0].get('reason', '未知')}"
                )
            else:
                raise HTTPException(status_code=400, detail="至少需要指定一个有效的目标目录")
        
        scan_results = []
        for i, target_path in enumerate(processed_paths):
            result = scan_and_analyze_single_path(target_path, i)
            scan_results.append(result)
        
        plan_results = []
        for i, scan_result in enumerate(scan_results):
            if scan_result.get("status") == "success":
                plan_result = generate_plan_for_single_path(
                    scan_result.get("target_path"),
                    scan_result.get("files", []),
                    scan_result.get("file_inventory", []),
                    i
                )
                plan_results.append(plan_result)
            else:
                plan_results.append({
                    "status": "skipped",
                    "index": i,
                    "target_path": scan_result.get("target_path", "unknown"),
                    "plan": [],
                    "error": scan_result.get("error", "扫描失败"),
                    "file_count": 0,
                    "action_count": 0,
                })
        
        success_count = sum(1 for r in plan_results if r.get("status") == "success")
        llm_failed_count = sum(1 for r in plan_results if r.get("status") == "llm_failed")
        total_actions = sum(r.get("action_count", 0) for r in plan_results)
        total_files = sum(r.get("file_count", 0) for r in plan_results)
        
        all_plans = []
        for result in plan_results:
            status = result.get("status")
            plan = result.get("plan", [])
            if status in ["success", "llm_failed"] and plan:
                for action in plan:
                    if isinstance(action, dict):
                        all_plans.append({
                            **action,
                            "source_path": result.get("target_path"),
                        })
        
        return {
            "status": "success",
            "plan_results": plan_results,
            "success_count": success_count,
            "llm_failed_count": llm_failed_count,
            "total_files": total_files,
            "total_actions": total_actions,
            "merged_plan": all_plans,
            "mode": "multi-directory-plan",
            "raw_input_paths": raw_paths,
            "processed_paths_count": len(processed_paths),
            "ignored_paths_count": len(ignored_paths_info),
            "ignored_paths": ignored_paths_info if len(ignored_paths_info) <= 10 else ignored_paths_info[:10] + [{"note": f"还有 {len(ignored_paths_info) - 10} 个被忽略的路径未显示"}],
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"多目录计划生成失败：{str(exc)}") from exc


@app.get("/")
async def root():
    return {
        "message": "Local Data Alchemist API is running",
        "version": APP_VERSION,
    }


@app.get("/task_status/{task_id}")
@app.get("/api/task_status/{task_id}")
async def get_task_status(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在：{task_id}")
    
    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        percentage=task.percentage,
        current=task.current,
        total=task.total,
        message=task.message,
        current_file=task.current_file,
        error=task.error,
        result=task.result,
        move_total=task.move_total,
        move_done=task.move_done,
        delete_total=task.delete_total,
        delete_done=task.delete_done,
        rename_total=task.rename_total,
        rename_done=task.rename_done,
        keep_total=task.keep_total,
        keep_done=task.keep_done,
        completed_items=task.completed_items,
        eta_seconds=task.eta_seconds,
        items_per_second=task.items_per_second,
        formatted_eta=format_eta(task.eta_seconds) if task.eta_seconds is not None else "计算中...",
    )


@app.post("/cancel_task")
@app.post("/api/cancel_task")
async def cancel_task_endpoint(request: CancelTaskRequest):
    success = cancel_task(request.task_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"任务不存在：{request.task_id}")
    
    task = get_task(request.task_id)
    return {
        "status": "success",
        "task_id": request.task_id,
        "message": "取消请求已发送",
        "current_status": task.status if task else "unknown",
    }


@app.post("/start_execute_task")
@app.post("/api/start_execute_task")
async def start_execute_task(request: ExecutePlanRequest):
    task_id = create_task("execute_plan", total=len(request.plan), plan=request.plan)
    
    def run_task():
        update_task_progress(task_id, status="running", message="开始执行炼金计划")
        
        move_count = 0
        delete_count = 0
        rename_count = 0
        keep_count = 0
        
        try:
            target_dir = get_target_dir(request.target_path)
            results = []
            snapshot_path = get_snapshot_path(target_dir)
            
            if snapshot_path.exists():
                update_task_progress(task_id, status="failed", error="检测到未回滚的 snapshot，请先执行 Undo 后再运行新的炼金计划。")
                return
            
            snapshot_operations = []
            
            for i, item in enumerate(request.plan):
                if is_task_cancelled(task_id):
                    update_task_progress(task_id, status="cancelled", message=f"任务已取消，已处理 {i} 个文件")
                    return
                
                if item.action not in ALLOWED_ACTIONS:
                    update_task_progress(task_id, status="failed", error=f"不支持的操作：{item.action}")
                    return
                
                if item.action in {"rename_and_move", "move"}:
                    if not item.target_path:
                        update_task_progress(task_id, status="failed", error=f"{item.action} 操作缺少 target_path。")
                        return
            
            total_items = len(request.plan)
            for i, item in enumerate(request.plan):
                if is_task_cancelled(task_id):
                    update_task_progress(task_id, status="cancelled", message=f"任务已取消，已处理 {i} 个文件")
                    return
                
                update_task_progress(
                    task_id,
                    current=i + 1,
                    message=f"正在处理 {i + 1}/{total_items}：{item.file}",
                    current_file=item.file,
                )
                
                if item.action not in ALLOWED_ACTIONS:
                    result_item = {
                        "file": item.file,
                        "action": item.action,
                        "original_path": item.file,
                        "new_path": None,
                        "status": "skipped",
                        "message": f"不支持的操作：{item.action}",
                    }
                    results.append(result_item)
                    continue
                
                source_path = resolve_inside_target(target_dir, item.file)
                if not source_path.exists():
                    result_item = {
                        "file": item.file,
                        "action": item.action,
                        "original_path": item.file,
                        "new_path": None,
                        "status": "skipped",
                        "message": "源文件不存在，可能已被处理。",
                    }
                    results.append(result_item)
                    update_task_progress(task_id, completed_item=result_item)
                    continue
                
                if item.action == "delete":
                    trash_path = resolve_inside_target(
                        target_dir,
                        f".alchemy_trash/{uuid.uuid4().hex}/{Path(item.file).name}",
                    )
                    trash_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source_path), str(trash_path))
                    snapshot_operations.append(
                        {
                            "action": item.action,
                            "original_path": item.file,
                            "new_path": to_target_relative(target_dir, trash_path),
                        }
                    )
                    result_item = {
                        "file": item.file,
                        "action": item.action,
                        "original_path": item.file,
                        "new_path": to_target_relative(target_dir, trash_path),
                        "absolute_original_path": str(source_path),
                        "absolute_new_path": str(trash_path),
                        "status": "success",
                    }
                    results.append(result_item)
                    delete_count += 1
                    update_task_progress(task_id, delete_done=delete_count, completed_item=result_item)
                    continue
                
                if item.action == "keep":
                    result_item = {
                        "file": item.file,
                        "action": item.action,
                        "original_path": item.file,
                        "new_path": item.file,
                        "absolute_original_path": str(source_path),
                        "absolute_new_path": str(source_path),
                        "status": "success",
                    }
                    results.append(result_item)
                    keep_count += 1
                    update_task_progress(task_id, keep_done=keep_count, completed_item=result_item)
                    continue
                
                if item.action == "move":
                    target_path = resolve_inside_target(target_dir, item.target_path)
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    shutil.move(str(source_path), str(target_path))
                    snapshot_operations.append(
                        {
                            "action": item.action,
                            "original_path": item.file,
                            "new_path": item.target_path,
                        }
                    )
                    result_item = {
                        "file": item.file,
                        "action": item.action,
                        "original_path": item.file,
                        "target_path": item.target_path,
                        "new_path": item.target_path,
                        "absolute_original_path": str(source_path),
                        "absolute_new_path": str(target_path),
                        "status": "success",
                    }
                    results.append(result_item)
                    move_count += 1
                    update_task_progress(task_id, move_done=move_count, completed_item=result_item)
                    continue
                
                if item.action == "rename_and_move":
                    target_path = resolve_inside_target(target_dir, item.target_path)
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    shutil.move(str(source_path), str(target_path))
                    snapshot_operations.append(
                        {
                            "action": item.action,
                            "original_path": item.file,
                            "new_path": item.target_path,
                        }
                    )
                    result_item = {
                        "file": item.file,
                        "action": item.action,
                        "original_path": item.file,
                        "target_path": item.target_path,
                        "new_path": item.target_path,
                        "absolute_original_path": str(source_path),
                        "absolute_new_path": str(target_path),
                        "status": "success",
                    }
                    results.append(result_item)
                    rename_count += 1
                    update_task_progress(task_id, rename_done=rename_count, completed_item=result_item)
            
            if is_task_cancelled(task_id):
                update_task_progress(task_id, status="cancelled", message=f"任务已取消，已处理 {len(results)} 个文件")
                return
            
            write_snapshot(target_dir, snapshot_operations)
            
            history_id = uuid.uuid4().hex
            plan_dict = [p.dict() for p in request.plan] if request.plan else []
            
            write_history(
                target_dir=target_dir,
                history_id=history_id,
                operation_type="execute",
                target_path=str(target_dir),
                plan=plan_dict,
                results=results,
                snapshot_path=str(snapshot_path),
            )
            
            final_result = {
                "status": "success",
                "executed": len(results),
                "results": results,
                "snapshot": snapshot_path.name,
                "snapshot_path": str(snapshot_path),
                "history_id": history_id,
            }
            
            update_task_progress(
                task_id,
                current=total_items,
                status="completed",
                message=f"执行完成，共处理 {len(results)} 个文件",
                result=final_result,
                move_done=move_count,
                delete_done=delete_count,
                rename_done=rename_count,
                keep_done=keep_count,
            )
            
        except HTTPException as e:
            update_task_progress(task_id, status="failed", error=str(e.detail))
        except Exception as e:
            update_task_progress(task_id, status="failed", error=str(e))
    
    thread = threading.Thread(target=run_task, daemon=True)
    thread.start()
    
    return {
        "status": "started",
        "task_id": task_id,
        "message": "任务已启动",
        "total_items": len(request.plan),
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
