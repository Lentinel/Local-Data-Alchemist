import re
from pathlib import Path

from fastapi import HTTPException


def get_target_dir(target_path: str | None) -> Path:
    if not target_path:
        raise HTTPException(status_code=400, detail="缺少 target_path 参数。")
    
    if not isinstance(target_path, str):
        raise HTTPException(status_code=400, detail="target_path 必须是字符串类型。")
    
    path_stripped = target_path.strip()
    if not path_stripped:
        raise HTTPException(status_code=400, detail="target_path 不能为空或仅包含空白字符。")
    
    try:
        target_dir = Path(path_stripped).expanduser().resolve()
    except (OSError, ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=400, 
            detail=f"无效的路径格式：{str(exc)}"
        ) from exc
    
    try:
        if not target_dir.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"目标文件夹不存在：{str(target_dir)}"
            )
        
        if not target_dir.is_dir():
            raise HTTPException(
                status_code=400, 
                detail=f"路径指向的不是文件夹：{str(target_dir)}"
            )
    except HTTPException:
        raise
    except OSError as exc:
        raise HTTPException(
            status_code=500, 
            detail=f"访问路径时发生错误：{str(exc)}"
        ) from exc

    return target_dir


def resolve_inside_target(target_dir: Path, relative_path: str | None) -> Path:
    if relative_path is None:
        raise HTTPException(status_code=400, detail="缺少路径参数。")
    
    if not isinstance(relative_path, str):
        raise HTTPException(status_code=400, detail="路径参数必须是字符串类型。")
    
    path_stripped = relative_path.strip()
    if not path_stripped:
        raise HTTPException(status_code=400, detail="路径参数不能为空或仅包含空白字符。")
    
    if ".." in path_stripped.split("/") or ".." in path_stripped.split("\\"):
        raise HTTPException(
            status_code=400, 
            detail=f"不允许使用父目录引用(..)：{path_stripped}"
        )
    
    try:
        normalized_target = target_dir.resolve()
        resolved_path = (normalized_target / path_stripped).resolve()
    except (OSError, ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=400, 
            detail=f"无效的路径格式：{str(exc)}"
        ) from exc
    
    try:
        if not resolved_path.is_relative_to(normalized_target):
            raise HTTPException(
                status_code=400, 
                detail=f"计划包含不安全路径：{path_stripped}（可能导致目录遍历攻击）"
            )
    except HTTPException:
        raise
    except OSError as exc:
        raise HTTPException(
            status_code=500, 
            detail=f"路径验证时发生错误：{str(exc)}"
        ) from exc
    
    return resolved_path


def to_target_relative(target_dir: Path, path: Path) -> str:
    return path.resolve().relative_to(target_dir.resolve()).as_posix()


def is_valid_history_id(history_id: str) -> bool:
    if not history_id or not isinstance(history_id, str):
        return False
    if len(history_id) != 32:
        return False
    if not re.match(r'^[0-9a-f]+$', history_id):
        return False
    return True
