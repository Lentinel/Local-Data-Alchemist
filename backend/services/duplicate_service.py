import hashlib
from pathlib import Path
from collections import defaultdict


def calculate_file_hash(file_path: Path, fast_mode: bool = True, block_size: int = 65536) -> str:
    hasher = hashlib.md5()
    
    if fast_mode:
        try:
            file_size = file_path.stat().st_size
            if file_size == 0:
                return hasher.hexdigest()
            
            sample_size = min(file_size, 8192)
            with file_path.open("rb") as f:
                hasher.update(f.read(sample_size))
        except (OSError, Exception):
            return ""
    else:
        try:
            with file_path.open("rb") as f:
                while True:
                    data = f.read(block_size)
                    if not data:
                        break
                    hasher.update(data)
        except (OSError, Exception):
            return ""
    
    return hasher.hexdigest()


def detect_duplicates(target_dir: Path, files: list[dict], fast_mode: bool = True) -> list[dict]:
    hash_groups = defaultdict(list)
    
    for file_info in files:
        file_path = target_dir / file_info.get("path", "")
        file_hash = calculate_file_hash(file_path, fast_mode)
        
        if file_hash:
            hash_groups[file_hash].append({
                "path": file_info.get("path", ""),
                "name": file_info.get("name", ""),
                "size": file_info.get("size", 0),
                "extension": file_info.get("extension", ""),
            })
    
    duplicate_groups = []
    for file_hash, group_files in hash_groups.items():
        if len(group_files) > 1:
            total_size = sum(f.get("size", 0) for f in group_files)
            duplicate_groups.append({
                "hash": file_hash,
                "files": group_files,
                "count": len(group_files),
                "size": total_size,
                "wasted_space": total_size - group_files[0].get("size", 0) if group_files else 0,
                "processed": False,
            })
    
    return duplicate_groups
