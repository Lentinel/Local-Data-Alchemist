import json
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException

from models.schemas import ActionPlanItem, ExecutePlanRequest, UndoPlanRequest
from utils.security import resolve_inside_target, to_target_relative
from utils.storage import get_snapshot_path, write_snapshot, write_history
from utils.task_manager import (
    create_task,
    update_task_progress,
    is_task_cancelled,
)
from utils.constants import ALLOWED_ACTIONS


def execute_plan_impl(request: ExecutePlanRequest) -> dict:
    from utils.security import get_target_dir
    
    target_dir = get_target_dir(request.target_path)
    results = []
    snapshot_path = get_snapshot_path(target_dir)

    if snapshot_path.exists():
        raise HTTPException(status_code=409, detail="检测到未回滚的 snapshot，请先执行 Undo 后再运行新的炼金计划。")

    snapshot_operations = []

    for item in request.plan:
        if item.action not in ALLOWED_ACTIONS:
            raise HTTPException(status_code=400, detail=f"不支持的操作：{item.action}")

        if item.action in {"rename_and_move", "move"}:
            if not item.target_path:
                raise HTTPException(status_code=400, detail=f"{item.action} 操作缺少 target_path。")

            source_path = resolve_inside_target(target_dir, item.file)
            target_path = resolve_inside_target(target_dir, item.target_path)
            if source_path.exists() and target_path.exists():
                raise HTTPException(status_code=409, detail=f"目标路径已存在：{item.target_path}")

    for item in request.plan:
        if item.action not in ALLOWED_ACTIONS:
            raise HTTPException(status_code=400, detail=f"不支持的操作：{item.action}")

        source_path = resolve_inside_target(target_dir, item.file)
        if not source_path.exists():
            results.append(
                {
                    "file": item.file,
                    "action": item.action,
                    "original_path": item.file,
                    "new_path": None,
                    "status": "skipped",
                    "message": "源文件不存在，可能已被处理。",
                }
            )
            continue

        if item.action == "delete":
            trash_path = resolve_inside_target(
                target_dir,
                f".alchemy_trash/{uuid.uuid4().hex}/{Path(item.file).name}",
            )
            trash_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_path), str(trash_path))
            snapshot_operations.append(
                {
                    "action": item.action,
                    "original_path": item.file,
                    "new_path": to_target_relative(target_dir, trash_path),
                }
            )
            results.append(
                {
                    "file": item.file,
                    "action": item.action,
                    "original_path": item.file,
                    "new_path": to_target_relative(target_dir, trash_path),
                    "absolute_original_path": str(source_path),
                    "absolute_new_path": str(trash_path),
                    "status": "success",
                }
            )
            continue

        if item.action == "keep":
            results.append(
                {
                    "file": item.file,
                    "action": item.action,
                    "original_path": item.file,
                    "new_path": item.file,
                    "absolute_original_path": str(source_path),
                    "absolute_new_path": str(source_path),
                    "status": "success",
                }
            )
            continue

        target_path = resolve_inside_target(target_dir, item.target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(source_path), str(target_path))
        snapshot_operations.append(
            {
                "action": item.action,
                "original_path": item.file,
                "new_path": item.target_path,
            }
        )
        results.append(
            {
                "file": item.file,
                "action": item.action,
                "original_path": item.file,
                "target_path": item.target_path,
                "new_path": item.target_path,
                "absolute_original_path": str(source_path),
                "absolute_new_path": str(target_path),
                "status": "success",
            }
        )

    write_snapshot(target_dir, snapshot_operations)

    history_id = uuid.uuid4().hex
    plan_dict = [item.dict() for item in request.plan] if request.plan else []
    
    write_history(
        target_dir=target_dir,
        history_id=history_id,
        operation_type="execute",
        target_path=str(target_dir),
        plan=plan_dict,
        results=results,
        snapshot_path=str(snapshot_path),
    )

    return {
        "status": "success",
        "executed": len(results),
        "results": results,
        "snapshot": snapshot_path.name,
        "snapshot_path": str(snapshot_path),
        "history_id": history_id,
    }


def undo_plan_impl(request: UndoPlanRequest) -> dict:
    from utils.security import get_target_dir
    
    target_dir = get_target_dir(request.target_path)
    snapshot_path = get_snapshot_path(target_dir)

    if not snapshot_path.exists():
        raise HTTPException(status_code=404, detail="未找到可回滚的 snapshot。")

    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"snapshot.json 已损坏：{exc}") from exc

    operations = snapshot.get("operations", [])
    results = []

    for operation in reversed(operations):
        original_path = operation.get("original_path")
        new_path = operation.get("new_path")
        if not original_path or not new_path:
            continue

        current_path = resolve_inside_target(target_dir, new_path)
        restore_path = resolve_inside_target(target_dir, original_path)

        if not current_path.exists():
            results.append(
                {
                    "file": original_path,
                    "status": "skipped",
                    "message": "回滚源文件不存在。",
                }
            )
            continue

        restore_path.parent.mkdir(parents=True, exist_ok=True)
        if restore_path.exists():
            raise HTTPException(status_code=409, detail=f"回滚目标路径已存在：{original_path}")

        shutil.move(str(current_path), str(restore_path))
        results.append(
            {
                "file": original_path,
                "original_path": original_path,
                "restored_from": new_path,
                "absolute_restore_path": str(restore_path),
                "absolute_previous_path": str(current_path),
                "status": "success",
            }
        )

    snapshot_path.unlink()

    trash_dir = target_dir / ".alchemy_trash"
    if trash_dir.exists():
        shutil.rmtree(trash_dir)

    history_id = uuid.uuid4().hex
    
    write_history(
        target_dir=target_dir,
        history_id=history_id,
        operation_type="undo",
        target_path=str(target_dir),
        plan=[],
        results=results,
        snapshot_path=None,
    )

    return {
        "status": "success",
        "message": "已恢复到炼金前状态",
        "restored": len(results),
        "results": results,
        "history_id": history_id,
    }


def execute_plan_async(request: ExecutePlanRequest, task_id: str) -> None:
    from utils.security import get_target_dir
    
    update_task_progress(task_id, status="running", message="开始执行炼金计划")
    
    move_count = 0
    delete_count = 0
    rename_count = 0
    keep_count = 0
    
    try:
        target_dir = get_target_dir(request.target_path)
        results = []
        snapshot_path = get_snapshot_path(target_dir)
        
        if snapshot_path.exists():
            update_task_progress(task_id, status="failed", error="检测到未回滚的 snapshot，请先执行 Undo 后再运行新的炼金计划。")
            return
        
        snapshot_operations = []
        
        for i, item in enumerate(request.plan):
            if is_task_cancelled(task_id):
                update_task_progress(task_id, status="cancelled", message=f"任务已取消，已处理 {i} 个文件")
                return
            
            if item.action not in ALLOWED_ACTIONS:
                update_task_progress(task_id, status="failed", error=f"不支持的操作：{item.action}")
                return
            
            if item.action in {"rename_and_move", "move"}:
                if not item.target_path:
                    update_task_progress(task_id, status="failed", error=f"{item.action} 操作缺少 target_path。")
                    return
        
        total_items = len(request.plan)
        for i, item in enumerate(request.plan):
            if is_task_cancelled(task_id):
                update_task_progress(task_id, status="cancelled", message=f"任务已取消，已处理 {i} 个文件")
                return
            
            update_task_progress(
                task_id,
                current=i + 1,
                message=f"正在处理 {i + 1}/{total_items}：{item.file}",
                current_file=item.file,
            )
            
            if item.action not in ALLOWED_ACTIONS:
                result_item = {
                    "file": item.file,
                    "action": item.action,
                    "original_path": item.file,
                    "new_path": None,
                    "status": "skipped",
                    "message": f"不支持的操作：{item.action}",
                }
                results.append(result_item)
                continue
            
            source_path = resolve_inside_target(target_dir, item.file)
            if not source_path.exists():
                result_item = {
                    "file": item.file,
                    "action": item.action,
                    "original_path": item.file,
                    "new_path": None,
                    "status": "skipped",
                    "message": "源文件不存在，可能已被处理。",
                }
                results.append(result_item)
                update_task_progress(task_id, completed_item=result_item)
                continue
            
            if item.action == "delete":
                trash_path = resolve_inside_target(
                    target_dir,
                    f".alchemy_trash/{uuid.uuid4().hex}/{Path(item.file).name}",
                )
                trash_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source_path), str(trash_path))
                snapshot_operations.append(
                    {
                        "action": item.action,
                        "original_path": item.file,
                        "new_path": to_target_relative(target_dir, trash_path),
                    }
                )
                result_item = {
                    "file": item.file,
                    "action": item.action,
                    "original_path": item.file,
                    "new_path": to_target_relative(target_dir, trash_path),
                    "absolute_original_path": str(source_path),
                    "absolute_new_path": str(trash_path),
                    "status": "success",
                }
                results.append(result_item)
                delete_count += 1
                update_task_progress(task_id, delete_done=delete_count, completed_item=result_item)
                continue
            
            if item.action == "keep":
                result_item = {
                    "file": item.file,
                    "action": item.action,
                    "original_path": item.file,
                    "new_path": item.file,
                    "absolute_original_path": str(source_path),
                    "absolute_new_path": str(source_path),
                    "status": "success",
                }
                results.append(result_item)
                keep_count += 1
                update_task_progress(task_id, keep_done=keep_count, completed_item=result_item)
                continue
            
            if item.action == "move":
                target_path = resolve_inside_target(target_dir, item.target_path)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.move(str(source_path), str(target_path))
                snapshot_operations.append(
                    {
                        "action": item.action,
                        "original_path": item.file,
                        "new_path": item.target_path,
                    }
                )
                result_item = {
                    "file": item.file,
                    "action": item.action,
                    "original_path": item.file,
                    "target_path": item.target_path,
                    "new_path": item.target_path,
                    "absolute_original_path": str(source_path),
                    "absolute_new_path": str(target_path),
                    "status": "success",
                }
                results.append(result_item)
                move_count += 1
                update_task_progress(task_id, move_done=move_count, completed_item=result_item)
                continue
            
            if item.action == "rename_and_move":
                target_path = resolve_inside_target(target_dir, item.target_path)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.move(str(source_path), str(target_path))
                snapshot_operations.append(
                    {
                        "action": item.action,
                        "original_path": item.file,
                        "new_path": item.target_path,
                    }
                )
                result_item = {
                    "file": item.file,
                    "action": item.action,
                    "original_path": item.file,
                    "target_path": item.target_path,
                    "new_path": item.target_path,
                    "absolute_original_path": str(source_path),
                    "absolute_new_path": str(target_path),
                    "status": "success",
                }
                results.append(result_item)
                rename_count += 1
                update_task_progress(task_id, rename_done=rename_count, completed_item=result_item)
        
        if is_task_cancelled(task_id):
            update_task_progress(task_id, status="cancelled", message=f"任务已取消，已处理 {len(results)} 个文件")
            return
        
        write_snapshot(target_dir, snapshot_operations)
        
        history_id = uuid.uuid4().hex
        plan_dict = [p.dict() for p in request.plan] if request.plan else []
        
        write_history(
            target_dir=target_dir,
            history_id=history_id,
            operation_type="execute",
            target_path=str(target_dir),
            plan=plan_dict,
            results=results,
            snapshot_path=str(snapshot_path),
        )
        
        final_result = {
            "status": "success",
            "executed": len(results),
            "results": results,
            "snapshot": snapshot_path.name,
            "snapshot_path": str(snapshot_path),
            "history_id": history_id,
        }
        
        update_task_progress(
            task_id,
            current=total_items,
            status="completed",
            message="执行完成",
            result=final_result,
        )
    
    except Exception as e:
        update_task_progress(task_id, status="failed", error=str(e))
