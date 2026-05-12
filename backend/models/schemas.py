from datetime import date, datetime, timedelta
from typing import Literal, Optional

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)


ActionType = Literal["rename_and_move", "move", "delete", "keep"]
TaskStatus = Literal["pending", "running", "completed", "cancelled", "failed"]
TaskType = Literal["execute_plan", "undo_plan", "rename_execute", "deduplicate"]


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


class SelectiveUndoRequest(BaseModel):
    target_path: str = Field(..., min_length=1, description="目标目录路径")
    files: list[str] = Field(..., min_length=1, description="要回滚的文件原始路径列表")

    @field_validator("target_path")
    @classmethod
    def validate_target_path_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("目标路径不能为空或仅包含空白字符")
        return v

    @field_validator("files")
    @classmethod
    def validate_files_not_empty(cls, v: list[str]) -> list[str]:
        if not v or len(v) == 0:
            raise ValueError("文件列表不能为空")
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


RenameRuleType = Literal[
    "prefix", "suffix", "find_replace", "regex", 
    "numbering", "date_prefix", "date_suffix"
]


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
    formatted_eta: Optional[str] = Field(default=None, description="格式化的预计剩余时间")

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
