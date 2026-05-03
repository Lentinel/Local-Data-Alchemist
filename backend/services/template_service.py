import json
import uuid
from pathlib import Path
from datetime import datetime
from collections import defaultdict


BUILTIN_TEMPLATES = [
    {
        "id": "builtin-standard",
        "name": "标准分类模板",
        "description": "按文件类型自动分类到标准目录（图片、文档、视频等）",
        "icon": "📁",
        "is_builtin": True,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "rules": [
            {
                "rule_id": "rule-images",
                "name": "图片文件",
                "match_extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"],
                "match_pattern": "",
                "match_category": "images",
                "action": "move",
                "target_path": "images",
                "reason": "图片文件",
                "priority": 1,
            },
            {
                "rule_id": "rule-documents",
                "name": "文档文件",
                "match_extensions": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md"],
                "match_pattern": "",
                "match_category": "documents",
                "action": "move",
                "target_path": "documents",
                "reason": "文档文件",
                "priority": 1,
            },
            {
                "rule_id": "rule-videos",
                "name": "视频文件",
                "match_extensions": [".mp4", ".avi", ".mkv", ".mov", ".wmv"],
                "match_pattern": "",
                "match_category": "videos",
                "action": "move",
                "target_path": "videos",
                "reason": "视频文件",
                "priority": 1,
            },
            {
                "rule_id": "rule-audio",
                "name": "音频文件",
                "match_extensions": [".mp3", ".wav", ".flac", ".aac"],
                "match_pattern": "",
                "match_category": "audio",
                "action": "move",
                "target_path": "audio",
                "reason": "音频文件",
                "priority": 1,
            },
            {
                "rule_id": "rule-archives",
                "name": "压缩文件",
                "match_extensions": [".zip", ".rar", ".7z", ".tar", ".gz"],
                "match_pattern": "",
                "match_category": "archives",
                "action": "move",
                "target_path": "archives",
                "reason": "压缩文件",
                "priority": 1,
            },
        ],
    },
    {
        "id": "builtin-date",
        "name": "按日期整理模板",
        "description": "按文件修改日期创建子目录整理",
        "icon": "📅",
        "is_builtin": True,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "rules": [
            {
                "rule_id": "rule-by-date",
                "name": "按日期整理",
                "match_extensions": [],
                "match_pattern": "",
                "match_category": "",
                "action": "move",
                "target_path": "files_by_date",
                "reason": "按日期整理",
                "priority": 1,
            },
        ],
    },
    {
        "id": "builtin-cleanup",
        "name": "清理临时文件",
        "description": "识别并清理临时文件、缓存文件",
        "icon": "🧹",
        "is_builtin": True,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "rules": [
            {
                "rule_id": "rule-temp",
                "name": "临时文件",
                "match_extensions": [".tmp", ".temp", ".log", ".cache"],
                "match_pattern": "",
                "match_category": "",
                "action": "delete",
                "target_path": None,
                "reason": "临时文件",
                "priority": 1,
            },
            {
                "rule_id": "rule-ds-store",
                "name": "系统文件",
                "match_pattern": r"^\.DS_Store$|^Thumbs\.db$",
                "match_extensions": [],
                "match_category": "",
                "action": "delete",
                "target_path": None,
                "reason": "系统生成的隐藏文件",
                "priority": 2,
            },
        ],
    },
]


def get_builtin_templates() -> list:
    return BUILTIN_TEMPLATES.copy()


def get_user_templates_path() -> Path:
    return Path(__file__).resolve().parent.parent / "user_templates.json"


def load_user_templates() -> list:
    templates_path = get_user_templates_path()
    if not templates_path.exists():
        return []
    
    try:
        content = templates_path.read_text(encoding="utf-8")
        data = json.loads(content)
        return data.get("templates", [])
    except (json.JSONDecodeError, OSError, Exception):
        return []


def save_user_templates(templates: list) -> None:
    templates_path = get_user_templates_path()
    data = {
        "version": 1,
        "updated_at": datetime.now().isoformat(),
        "templates": templates,
    }
    templates_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_all_templates() -> list:
    builtin = get_builtin_templates()
    user = load_user_templates()
    return builtin + user


def save_user_template(template_data: dict) -> dict:
    user_templates = load_user_templates()
    
    template_id = template_data.get("id")
    is_new = False
    
    if not template_id:
        template_id = f"template-{uuid.uuid4().hex[:8]}"
        is_new = True
    
    template = {
        "id": template_id,
        "name": template_data.get("name", "未命名模板"),
        "description": template_data.get("description", ""),
        "icon": template_data.get("icon", "📁"),
        "is_builtin": False,
        "created_at": template_data.get("created_at") or datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "rules": template_data.get("rules", []),
    }
    
    if is_new:
        user_templates.append(template)
    else:
        for i, t in enumerate(user_templates):
            if t.get("id") == template_id:
                user_templates[i] = template
                break
        else:
            user_templates.append(template)
    
    save_user_templates(user_templates)
    return template


def delete_user_template(template_id: str) -> bool:
    user_templates = load_user_templates()
    original_count = len(user_templates)
    
    user_templates = [t for t in user_templates if t.get("id") != template_id]
    
    if len(user_templates) < original_count:
        save_user_templates(user_templates)
        return True
    return False


def apply_template_to_files(
    template: dict,
    files: list,
    target_dir: Path,
) -> list:
    plan = []
    rules = template.get("rules", [])
    
    for file_info in files:
        file_path = file_info.get("path", "")
        file_name = file_info.get("name", "")
        extension = file_info.get("extension", "")
        category = file_info.get("category", "")
        
        matched_rule = None
        
        for rule in rules:
            match_extensions = rule.get("match_extensions", [])
            match_pattern = rule.get("match_pattern", "")
            match_category = rule.get("match_category", "")
            
            matches = False
            
            if match_extensions and extension in match_extensions:
                matches = True
            
            if match_pattern and not matches:
                try:
                    if re.match(match_pattern, file_name):
                        matches = True
                except re.error:
                    pass
            
            if match_category and category == match_category:
                matches = True
            
            if matches:
                matched_rule = rule
                break
        
        if matched_rule:
            action = matched_rule.get("action", "keep")
            target_path = matched_rule.get("target_path")
            reason = matched_rule.get("reason", "应用模板规则")
            
            if action == "move" and target_path:
                file_name_only = file_path.split("/")[-1]
                final_target = f"{target_path.rstrip('/')}/{file_name_only}"
            else:
                final_target = target_path
            
            plan.append({
                "file": file_path,
                "action": action,
                "target_path": final_target if action != "keep" else None,
                "reason": reason,
            })
    
    return plan
