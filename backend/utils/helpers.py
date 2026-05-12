import re
from datetime import datetime
from pathlib import Path

from .constants import (
    CATEGORY_RULES,
    WINDOWS_RESERVED_NAMES,
    WINDOWS_INVALID_CHARS,
    MAX_FILENAME_LENGTH,
)


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


def classify_file(extension: str, filename: str = "") -> str:
    """智能文件分类：先按文件名模式匹配，再按扩展名匹配。
    
    Args:
        extension: 文件扩展名
        filename: 文件名（可选，用于模式匹配）
        
    Returns:
        分类名称
    """
    from .constants import FILENAME_PATTERNS
    
    # 优先按文件名模式匹配
    if filename:
        for category, patterns in FILENAME_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, filename):
                    return category
    
    # 再按扩展名匹配
    ext = extension.lower()
    for category, extensions in CATEGORY_RULES.items():
        if ext in extensions:
            return category
    
    return "unknown"


def is_temp_file(filename: str) -> bool:
    """判断文件是否为临时/缓存文件。
    
    Args:
        filename: 文件名
        
    Returns:
        如果是临时文件返回 True
    """
    from .constants import TEMP_FILE_PATTERNS
    
    for pattern in TEMP_FILE_PATTERNS:
        if re.search(pattern, filename):
            return True
    return False


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


def get_safe_sort_key(history_item: dict) -> tuple:
    """获取历史记录的安全排序键。
    
    Args:
        history_item: 历史记录字典
        
    Returns:
        排序元组，用于按时间排序
    """
    created_at = history_item.get("created_at", "")
    
    if not created_at or not isinstance(created_at, str):
        return (0, "")
    
    try:
        if "T" in created_at:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            return (2, dt.isoformat())
        else:
            return (1, created_at)
    except (ValueError, TypeError):
        return (0, created_at)


def strip_markdown_fence(content: str) -> str:
    """移除 Markdown 代码围栏。
    
    Args:
        content: 可能包含 Markdown 代码围栏的文本
        
    Returns:
        移除围栏后的文本
    """
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
    """判断文本是否需要翻译为中文。
    
    Args:
        text: 待判断的文本
        
    Returns:
        如果文本是英文且需要翻译则返回 True
    """
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
