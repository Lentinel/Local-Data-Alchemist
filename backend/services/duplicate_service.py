import hashlib
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException

from models.schemas import KeepDuplicateRequest
from utils.security import resolve_inside_target, to_target_relative
from utils.storage import get_snapshot_path, write_snapshot, write_history


def calculate_file_hash(file_path: Path, fast_mode: bool = True) -> str:
    try:
        if not file_path.exists() or not file_path.is_file():
            return ""
        
        file_size = file_path.stat().st_size
        
        if fast_mode and file_size > 10 * 1024 * 1024:
            hasher = hashlib.sha256()
            hasher.update(str(file_size).encode())
            hasher.update(b"|")
            
            with file_path.open("rb") as f:
                start_bytes = f.read(16384)
                hasher.update(start_bytes)
                hasher.update(b"|")
                
                if file_size > 65536:
                    num_samples = min(8, file_size // (2 * 1024 * 1024))
                    num_samples = max(2, num_samples)
                    
                    step = file_size // (num_samples + 1)
                    
                    for i in range(1, num_samples + 1):
                        sample_pos = step * i
                        try:
                            f.seek(sample_pos)
                            sample_bytes = f.read(4096)
                            hasher.update(sample_bytes)
                            hasher.update(b"|")
                        except (OSError, ValueError):
                            continue
                
                if file_size > 32768:
                    try:
                        end_pos = max(0, file_size - 16384)
                        f.seek(end_pos)
                        end_bytes = f.read(16384)
                        hasher.update(end_bytes)
                    except (OSError, ValueError):
                        pass
            
            return hasher.hexdigest()
        
        hasher = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(131072), b""):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    except (OSError, Exception):
        return ""


def detect_duplicates(target_dir: Path, fast_mode: bool = True) -> dict:
    from services.file_service import scan_target_files
    
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
        "groups": duplicate_groups,
        "duplicate_groups": duplicate_groups,
        "total_duplicate_count": total_duplicate_count,
        "total_duplicate_size": total_duplicate_size,
        "fast_mode": fast_mode
    }


def keep_duplicate(request: KeepDuplicateRequest) -> dict:
    from utils.security import get_target_dir
    
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
