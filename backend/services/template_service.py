import json
import uuid
import re
from pathlib import Path
from datetime import date, datetime


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


def get_templates_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "templates"


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


def apply_template_to_files(
    template: dict,
    files_info: list[dict],
    target_dir: Path,
) -> list[dict]:
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
