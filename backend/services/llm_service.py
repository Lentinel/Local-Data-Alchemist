import os
import json
import re
import hashlib
import httpx
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import dotenv_values, load_dotenv
from openai import APIConnectionError, AuthenticationError, OpenAI
from pydantic import ValidationError
from fastapi import HTTPException

from models.schemas import ActionPlanItem, FileInfo
from utils.constants import ALLOWED_ACTIONS
from utils.helpers import classify_file, strip_markdown_fence, should_translate_to_zh
from utils.security import resolve_inside_target
from services.file_service import peek_file_content


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)


def build_openai_client(timeout_seconds: int, api_key: str | None = None, api_base: str | None = None) -> OpenAI:
    api_key = (api_key if api_key is not None else (os.getenv("OPENAI_API_KEY") or "")).strip()
    api_base = (api_base if api_base is not None else (os.getenv("OPENAI_API_BASE") or "")).strip()
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


def analyze_image_with_llm(image_path: Path, max_retries: int = 1) -> str:
    """使用多模态 LLM 分析图片内容。
    
    Args:
        image_path: 图片文件路径
        max_retries: 最大重试次数
        
    Returns:
        图片内容描述文本
    """
    import base64
    
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    api_base = (os.getenv("OPENAI_API_BASE") or "").strip()
    model = (os.getenv("OPENAI_MODEL") or "").strip()
    timeout_seconds_raw = (os.getenv("OPENAI_TIMEOUT_SECONDS") or "").strip()
    timeout_seconds = 60  # 图片分析使用较短超时
    if timeout_seconds_raw:
        try:
            timeout_seconds = min(int(float(timeout_seconds_raw)), 120)
        except ValueError:
            timeout_seconds = 60

    if not api_key or not api_base or not model:
        return "[图片分析不可用：LLM 配置不完整]"

    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        extension = image_path.suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
        }
        mime_type = mime_map.get(extension, "image/png")

        client = OpenAI(
            api_key=api_key,
            base_url=api_base,
            http_client=httpx.Client(trust_env=False, timeout=timeout_seconds),
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是图片内容分析专家。请用简体中文描述图片内容，重点关注："
                        "1) 如果是票据/发票/收据，提取商户名、金额、日期、票据号"
                        "2) 如果是截图，描述截图内容和关键信息"
                        "3) 如果是照片，描述场景和主要内容"
                        "4) 如果是图表/数据可视化，描述数据趋势和关键数值"
                        "请用简洁的中文描述，不超过200字。"
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}",
                            },
                        },
                        {
                            "type": "text",
                            "text": "请分析这张图片的内容。",
                        },
                    ],
                },
            ],
            temperature=0,
            max_tokens=500,
        )

        content = response.choices[0].message.content or ""
        return content.strip() if content.strip() else "[图片分析返回为空]"

    except Exception as e:
        return f"[图片分析失败: {str(e)[:100]}]"


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


def _is_placeholder_value(field_name: str, value: str) -> bool:
    normalized = (value or "").strip().lower()
    if not normalized:
        return False
    if field_name == "OPENAI_API_KEY":
        return normalized == "your_openai_api_key_here"
    if field_name == "OPENAI_API_BASE":
        return "your-openai-compatible-base-url" in normalized
    if field_name == "OPENAI_MODEL":
        return normalized == "your_model_name_here"
    return False



def _build_placeholder_summary(api_key: str, api_base: str, model: str) -> tuple[bool, list[str]]:
    placeholder_fields: list[str] = []
    for field_name, value in {
        "OPENAI_API_KEY": api_key,
        "OPENAI_API_BASE": api_base,
        "OPENAI_MODEL": model,
    }.items():
        if _is_placeholder_value(field_name, value):
            placeholder_fields.append(field_name)
    return bool(placeholder_fields), placeholder_fields



def _build_connection_result(connection_status: str | None = None, connection_error: str | None = None, checked_at: str | None = None) -> dict:
    return {
        "connection_status": connection_status,
        "connection_error": connection_error,
        "checked_at": checked_at,
    }



def _sanitize_connection_error(exc: Exception) -> str:
    if isinstance(exc, AuthenticationError):
        return "authentication_failed"
    if exc.__class__.__name__ == "APITimeoutError" or isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        return "request_timed_out"
    if isinstance(exc, (APIConnectionError, httpx.NetworkError, httpx.ConnectError)):
        return "connection_failed"
    return "request_failed"



def _check_llm_connection(api_key: str, api_base: str, model: str, timeout_seconds: int) -> dict:
    checked_at = datetime.now(timezone.utc).isoformat()
    if not api_key or not api_base or not model:
        return _build_connection_result(
            connection_status="skipped",
            connection_error="missing_required_config",
            checked_at=checked_at,
        )

    client = build_openai_client(timeout_seconds, api_key=api_key, api_base=api_base)

    try:
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            temperature=0,
        )
        return _build_connection_result(
            connection_status="ok",
            connection_error=None,
            checked_at=checked_at,
        )
    except Exception as exc:
        return _build_connection_result(
            connection_status="error",
            connection_error=_sanitize_connection_error(exc),
            checked_at=checked_at,
        )



def _parse_timeout_seconds(timeout_seconds_raw: str) -> tuple[int, bool]:
    timeout_seconds = 180
    timeout_valid = True
    if timeout_seconds_raw:
        try:
            timeout_seconds = int(float(timeout_seconds_raw))
        except ValueError:
            timeout_seconds = 180
            timeout_valid = False
    return timeout_seconds, timeout_valid



def _mask_api_key(api_key: str) -> str | None:
    if not api_key:
        return None
    if len(api_key) <= 4:
        return f"{api_key[:1]}***"
    if len(api_key) <= 8:
        return f"{api_key[:2]}***"
    return f"{api_key[:4]}...{api_key[-4:]}"



def llm_debug_info() -> dict:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    api_base = (os.getenv("OPENAI_API_BASE") or "").strip()
    model = (os.getenv("OPENAI_MODEL") or "").strip()
    timeout_seconds_raw = (os.getenv("OPENAI_TIMEOUT_SECONDS") or "").strip()
    fingerprint = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:10] if api_key else None
    timeout_seconds, _ = _parse_timeout_seconds(timeout_seconds_raw)
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



def llm_health_info(check_connection: bool = False) -> dict:
    env_file_exists = ENV_PATH.exists()
    env_values = dotenv_values(ENV_PATH) if env_file_exists else {}
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip() or (env_values.get("OPENAI_API_KEY") or "").strip()
    api_base = (os.getenv("OPENAI_API_BASE") or "").strip() or (env_values.get("OPENAI_API_BASE") or "").strip()
    model = (os.getenv("OPENAI_MODEL") or "").strip() or (env_values.get("OPENAI_MODEL") or "").strip()
    timeout_seconds_raw = (os.getenv("OPENAI_TIMEOUT_SECONDS") or "").strip() or (env_values.get("OPENAI_TIMEOUT_SECONDS") or "").strip()
    timeout_seconds, timeout_valid = _parse_timeout_seconds(timeout_seconds_raw)
    has_placeholder_values, placeholder_fields = _build_placeholder_summary(api_key, api_base, model)

    has_api_key = bool(api_key) and "OPENAI_API_KEY" not in placeholder_fields
    has_api_base = bool(api_base) and "OPENAI_API_BASE" not in placeholder_fields
    has_model = bool(model) and "OPENAI_MODEL" not in placeholder_fields

    suggestions: list[str] = []
    if not env_file_exists:
        suggestions.append("backend/.env 不存在")
    if not api_key:
        suggestions.append("OPENAI_API_KEY 未配置")
    if not api_base:
        suggestions.append("OPENAI_API_BASE 未配置")
    if not model:
        suggestions.append("OPENAI_MODEL 未配置")
    if timeout_seconds_raw and not timeout_valid:
        suggestions.append("OPENAI_TIMEOUT_SECONDS 非法，已回退为 180")
    for field_name in placeholder_fields:
        suggestions.append(f"{field_name} 仍是示例占位值，请替换为真实值")

    config_complete = has_api_key and has_api_base and has_model
    connection_result = _build_connection_result()
    if check_connection:
        if has_placeholder_values:
            connection_result = _build_connection_result(
                connection_status="skipped",
                connection_error="placeholder_config_detected",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        else:
            connection_result = _check_llm_connection(api_key, api_base, model, timeout_seconds)

    return {
        "env_file_exists": env_file_exists,
        "has_api_key": has_api_key,
        "api_key_preview": _mask_api_key(api_key),
        "has_api_base": has_api_base,
        "api_base": api_base or None,
        "has_model": has_model,
        "model": model or None,
        "timeout_seconds": timeout_seconds,
        "status": "ok" if config_complete and timeout_valid else "warning",
        "suggestions": suggestions,
        "has_placeholder_values": has_placeholder_values,
        "placeholder_fields": placeholder_fields,
        **connection_result,
    }



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


async def generate_plan_impl(request) -> dict:
    from models.schemas import PlanRequest
    from utils.security import get_target_dir
    from services.file_service import scan_target_files, build_analysis
    
    if not isinstance(request, PlanRequest):
        raise ValueError("Invalid request type")
    
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
