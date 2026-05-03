from datetime import datetime


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


def classify_file(extension: str) -> str:
    ext = extension.lower().lstrip('.')
    
    if ext in {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico', 'tiff'}:
        return 'images'
    elif ext in {'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'm4v'}:
        return 'videos'
    elif ext in {'mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'wma'}:
        return 'audio'
    elif ext in {'doc', 'docx', 'pdf', 'txt', 'rtf', 'odt', 'xls', 'xlsx', 'ppt', 'pptx', 'md'}:
        return 'documents'
    elif ext in {'zip', 'rar', '7z', 'tar', 'gz', 'bz2'}:
        return 'archives'
    elif ext in {'exe', 'msi', 'apk', 'dmg', 'pkg'}:
        return 'executables'
    elif ext in {'js', 'py', 'java', 'cpp', 'c', 'h', 'go', 'rs', 'ts', 'html', 'css', 'json', 'xml', 'yaml', 'yml'}:
        return 'code'
    else:
        return 'others'


def get_safe_sort_key(history_item: dict) -> tuple:
    created_at = history_item.get("created_at", "")
    try:
        dt = datetime.fromisoformat(created_at)
        return (dt, history_item.get("id", ""))
    except (ValueError, TypeError):
        return (datetime.min, created_at or history_item.get("id", ""))


def strip_markdown_fence(content: str) -> str:
    if not content:
        return content
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if len(lines) > 1:
            if lines[0].startswith("```json") or lines[0].startswith("```javascript"):
                lines = lines[1:]
            else:
                if lines[0].strip() == "```":
                    lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines).strip()
    return content


def should_translate_to_zh(text: str | None) -> bool:
    if not text or not text.strip():
        return False
    text = text.strip()
    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
    if has_chinese:
        return False
    if len(text) < 20:
        return False
    return True
