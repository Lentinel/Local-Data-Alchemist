import os
import json
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, APIConnectionError, AuthenticationError

from utils.helpers import strip_markdown_fence, should_translate_to_zh


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)


def get_openai_client():
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    if not openai_api_key:
        return None, None, openai_model
    
    try:
        client = OpenAI(
            api_key=openai_api_key,
            base_url=openai_base_url,
        )
        return client, openai_api_key, openai_model
    except Exception:
        return None, None, openai_model


def build_llm_prompt(files: list) -> str:
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


def call_llm_generate_plan(files: list) -> list:
    client, api_key, model = get_openai_client()
    
    if not client or not api_key:
        return generate_fallback_plan(files)
    
    system_prompt = build_llm_prompt(files)
    
    user_parts = []
    for f in files:
        ext = f.get("extension", "")
        cat = f.get("category", "")
        user_parts.append(f"- {f['name']} (ext={ext}, cat={cat}, size={f.get('size', 0)})")
    
    user_prompt = "\n".join(user_parts)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        
        raw_content = response.choices[0].message.content
        if not raw_content:
            return generate_fallback_plan(files)
        
        json_str = strip_markdown_fence(raw_content)
        
        try:
            plan = json.loads(json_str)
            if isinstance(plan, dict) and "plan" in plan:
                plan = plan["plan"]
            if not isinstance(plan, list):
                return generate_fallback_plan(files)
            return plan
        except json.JSONDecodeError:
            return generate_fallback_plan(files)
            
    except APIConnectionError:
        return generate_fallback_plan(files)
    except AuthenticationError:
        return generate_fallback_plan(files)
    except Exception:
        return generate_fallback_plan(files)


def generate_fallback_plan(files: list) -> list:
    plan = []
    
    folder_mapping = {
        "images": "pictures",
        "documents": "documents",
        "videos": "videos",
        "audio": "music",
        "archives": "archives",
        "code": "code",
        "executables": "programs",
    }
    
    for f in files:
        cat = f.get("category", "unknown")
        target_folder = folder_mapping.get(cat, "others")
        action = "move"
        
        if cat == "unknown":
            action = "keep"
            target_folder = None
        
        plan.append({
            "file": f.get("path", ""),
            "action": action,
            "target_path": f"{target_folder}/{f.get('name', '')}" if target_folder else None,
            "reason": f"按分类整理: {cat}",
        })
    
    return plan
