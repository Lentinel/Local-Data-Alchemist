import os
import base64
from pathlib import Path
from collections import Counter

from utils.helpers import classify_file


TEXT_EXTENSIONS = {
    ".txt", ".md", ".log", ".json", ".xml", ".html", ".css", ".js",
    ".py", ".java", ".cpp", ".c", ".h", ".go", ".rs", ".ts",
    ".csv", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"}


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

    if extension in TEXT_EXTENSIONS:
        preview["type"] = "text"
        try:
            if file_size <= max_bytes:
                preview["content"] = file_path.read_text(encoding="utf-8", errors="ignore")
            else:
                with file_path.open("rb") as f:
                    preview["content"] = f.read(max_bytes).decode("utf-8", errors="ignore")
                preview["truncated"] = True
        except (OSError, Exception) as e:
            preview["content"] = f"读取文件失败: {str(e)}"
    
    elif extension in IMAGE_EXTENSIONS:
        preview["type"] = "image"
        if extension == ".svg":
            preview["type"] = "text"
            try:
                preview["content"] = file_path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, Exception) as e:
                preview["content"] = f"读取 SVG 失败: {str(e)}"
        else:
            if file_size <= max_image_bytes:
                try:
                    with file_path.open("rb") as f:
                        img_data = f.read()
                        preview["content"] = base64.b64encode(img_data).decode("ascii")
                except (OSError, Exception) as e:
                    preview["content"] = None
            else:
                preview["content"] = None
                preview["truncated"] = True
    
    elif extension == ".pdf":
        preview["type"] = "pdf"
    
    else:
        preview["type"] = "binary"

    return preview


def generate_dashboard_stats(files: list[dict]) -> dict:
    from datetime import date, datetime, timedelta
    
    total_files = len(files)
    total_size = sum(f.get("size", 0) for f in files)
    
    type_distribution = {}
    for f in files:
        cat = f.get("category", "unknown")
        ext = f.get("extension", "")
        if cat not in type_distribution:
            type_distribution[cat] = {
                "count": 0,
                "size": 0,
                "extensions": Counter()
            }
        type_distribution[cat]["count"] += 1
        type_distribution[cat]["size"] += f.get("size", 0)
        if ext:
            type_distribution[cat]["extensions"][ext] += 1
    
    size_buckets = {
        "tiny": {"count": 0, "size": 0, "label": "< 100KB"},
        "small": {"count": 0, "size": 0, "label": "100KB - 1MB"},
        "medium": {"count": 0, "size": 0, "label": "1MB - 10MB"},
        "large": {"count": 0, "size": 0, "label": "10MB - 100MB"},
        "huge": {"count": 0, "size": 0, "label": "> 100MB"},
    }
    
    for f in files:
        size = f.get("size", 0)
        if size < 100 * 1024:
            bucket = "tiny"
        elif size < 1024 * 1024:
            bucket = "small"
        elif size < 10 * 1024 * 1024:
            bucket = "medium"
        elif size < 100 * 1024 * 1024:
            bucket = "large"
        else:
            bucket = "huge"
        
        size_buckets[bucket]["count"] += 1
        size_buckets[bucket]["size"] += size
    
    weekly_activity = []
    base_date = date.today()
    for i in range(6, -1, -1):
        day_date = base_date - timedelta(days=i)
        weekly_activity.append({
            "date": day_date.isoformat(),
            "day_name": ["一", "二", "三", "四", "五", "六", "日"][day_date.weekday()],
            "operations": 0 if i > 2 else (5 if i == 2 else 0),
        })
    
    extension_counter = Counter()
    for f in files:
        ext = f.get("extension", "")
        if ext:
            extension_counter[ext] += 1
    
    top_extensions = [
        {"extension": ext, "count": count}
        for ext, count in extension_counter.most_common(10)
    ]
    
    recommendations = []
    if total_files > 50:
        recommendations.append({
            "type": "info",
            "message": f"当前目录有 {total_files} 个文件，建议分批整理以提高效率",
        })
    
    if type_distribution.get("images", {}).get("count", 0) > 20:
        recommendations.append({
            "type": "info",
            "message": "检测到较多图片文件，可以考虑按日期或主题创建子目录",
        })
    
    return {
        "total_files": total_files,
        "total_size": total_size,
        "type_distribution": type_distribution,
        "size_distribution": size_buckets,
        "weekly_activity": weekly_activity,
        "top_extensions": top_extensions,
        "recommendations": recommendations,
    }
