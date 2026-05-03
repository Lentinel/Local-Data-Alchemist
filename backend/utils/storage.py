import json
from datetime import date, datetime
from pathlib import Path

from fastapi import HTTPException

from .security import is_valid_history_id


def get_snapshot_path(target_dir: Path) -> Path:
    return target_dir / "snapshot.json"


def get_history_dir(target_dir: Path) -> Path:
    return target_dir / ".alchemy_history"


def get_history_path(target_dir: Path, history_id: str) -> Path:
    if not is_valid_history_id(history_id):
        raise HTTPException(status_code=400, detail=f"无效的历史记录ID：{history_id}")
    
    history_dir = get_history_dir(target_dir)
    return history_dir / f"{history_id}.json"


def write_snapshot(target_dir: Path, operations: list[dict]) -> None:
    snapshot_path = get_snapshot_path(target_dir)
    snapshot = {
        "version": 1,
        "created_at": date.today().isoformat(),
        "operations": operations,
    }
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")


def write_history(
    target_dir: Path,
    history_id: str,
    operation_type: str,
    target_path: str,
    plan: list[dict],
    results: list[dict],
    snapshot_path: str = None,
) -> None:
    try:
        history_dir = get_history_dir(target_dir)
        history_dir.mkdir(parents=True, exist_ok=True)
        
        history_record = {
            "id": history_id,
            "type": operation_type,
            "target_path": target_path,
            "created_at": datetime.now().isoformat(),
            "plan": plan,
            "results": results,
            "snapshot_path": snapshot_path,
        }
        
        history_file = get_history_path(target_dir, history_id)
        history_file.write_text(json.dumps(history_record, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, Exception) as exc:
        print(f"警告：历史记录写入失败：{str(exc)}")


def get_safe_sort_key(history_item: dict) -> tuple:
    created_at = history_item.get("created_at", "")
    
    if not created_at or not isinstance(created_at, str):
        return (0, "")
    
    try:
        if "T" in created_at:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            return (2, dt.isoformat())
        else:
            return (1, created_at)
    except (ValueError, TypeError, Exception):
        return (0, created_at)


def list_history(target_dir: Path) -> list[dict]:
    history_dir = get_history_dir(target_dir)
    if not history_dir.exists():
        return []
    
    history_files = []
    for file in history_dir.glob("*.json"):
        try:
            content = json.loads(file.read_text(encoding="utf-8"))
            if content.get("id"):
                history_files.append(content)
        except (json.JSONDecodeError, OSError, Exception):
            continue
    
    history_files.sort(key=get_safe_sort_key, reverse=True)
    return history_files


def get_history(target_dir: Path, history_id: str) -> dict:
    history_file = get_history_path(target_dir, history_id)
    if not history_file.exists():
        raise HTTPException(status_code=404, detail=f"历史记录不存在：{history_id}")
    
    try:
        return json.loads(history_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"历史记录已损坏：{str(exc)}") from exc
