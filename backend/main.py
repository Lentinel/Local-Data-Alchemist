import os
import json
import shutil
import subprocess
import uuid
from collections import Counter
from datetime import date, datetime
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
from pydantic import BaseModel, Field, ValidationError

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
    name: str
    path: str
    extension: str = ""
    category: str = "unknown"
    size: int = 0


class PlanRequest(BaseModel):
    target_path: str


class FolderRequest(BaseModel):
    target_path: str


class ActionPlanItem(BaseModel):
    file: str
    action: str
    target_path: str | None = None
    reason: str
    extracted_info: dict | None = None


class ExecutePlanRequest(BaseModel):
    target_path: str
    plan: list[ActionPlanItem] = Field(default_factory=list)


class UndoPlanRequest(BaseModel):
    target_path: str


class FilePreviewRequest(BaseModel):
    target_path: str
    file_path: str


class ListHistoryRequest(BaseModel):
    target_path: str


class GetHistoryRequest(BaseModel):
    target_path: str
    history_id: str


class DetectDuplicatesRequest(BaseModel):
    target_path: str
    fast_mode: bool = True


class KeepDuplicateRequest(BaseModel):
    target_path: str
    keep_file: str
    duplicate_files: list[str]


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
            
            with file_path.open("rb") as f:
                start_bytes = f.read(8192)
                hasher.update(start_bytes)
                
                if file_size > 16384:
                    f.seek(file_size - 8192)
                    end_bytes = f.read(8192)
                    hasher.update(end_bytes)
            
            return hasher.hexdigest()
        
        hasher = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
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


def get_target_dir(target_path: str) -> Path:
    if not target_path:
        raise HTTPException(status_code=400, detail="缺少 target_path。")

    target_dir = Path(target_path).expanduser().resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="未找到目标文件夹。")

    return target_dir


def resolve_inside_target(target_dir: Path, relative_path: str) -> Path:
    resolved_path = (target_dir / relative_path).resolve()
    if not resolved_path.is_relative_to(target_dir.resolve()):
        raise HTTPException(status_code=400, detail=f"计划包含不安全路径：{relative_path}")
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


@app.get("/")
async def root():
    return {
        "message": "Local Data Alchemist API is running",
        "version": APP_VERSION,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
