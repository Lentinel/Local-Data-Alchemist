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


def selective_undo_impl(target_path: str, files_to_restore: list[str]) -> dict:
    """选择性回滚：仅回滚指定的文件。
    
    Args:
        target_path: 目标目录路径
        files_to_restore: 要回滚的文件原始路径列表
        
    Returns:
        回滚结果
    """
    from utils.security import get_target_dir
    
    target_dir = get_target_dir(target_path)
    snapshot_path = get_snapshot_path(target_dir)

    if not snapshot_path.exists():
        raise HTTPException(status_code=404, detail="未找到可回滚的 snapshot。")

    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"snapshot.json 已损坏：{exc}") from exc

    operations = snapshot.get("operations", [])
    files_set = set(files_to_restore)
    results = []
    remaining_operations = []

    for operation in operations:
        original_path = operation.get("original_path")
        new_path = operation.get("new_path")
        
        if original_path not in files_set:
            remaining_operations.append(operation)
            continue
        
        if not original_path or not new_path:
            results.append({
                "file": original_path,
                "status": "skipped",
                "message": "操作记录不完整",
            })
            continue

        current_path = resolve_inside_target(target_dir, new_path)
        restore_path = resolve_inside_target(target_dir, original_path)

        if not current_path.exists():
            results.append({
                "file": original_path,
                "status": "skipped",
                "message": "回滚源文件不存在",
            })
            continue

        try:
            restore_path.parent.mkdir(parents=True, exist_ok=True)
            if restore_path.exists():
                results.append({
                    "file": original_path,
                    "status": "skipped",
                    "message": f"回滚目标路径已存在：{original_path}",
                })
                remaining_operations.append(operation)
                continue
            
            shutil.move(str(current_path), str(restore_path))
            results.append({
                "file": original_path,
                "original_path": original_path,
                "restored_from": new_path,
                "status": "success",
            })
        except Exception as e:
            results.append({
                "file": original_path,
                "status": "failed",
                "message": str(e),
            })
            remaining_operations.append(operation)

    # 更新 snapshot（保留未回滚的操作）
    if remaining_operations:
        write_snapshot(target_dir, remaining_operations)
    else:
        # 全部回滚完成，删除 snapshot
        snapshot_path.unlink()
        trash_dir = target_dir / ".alchemy_trash"
        if trash_dir.exists():
            shutil.rmtree(trash_dir)

    success_count = sum(1 for r in results if r["status"] == "success")
    
    history_id = uuid.uuid4().hex
    write_history(
        target_dir=target_dir,
        history_id=history_id,
        operation_type="selective_undo",
        target_path=str(target_dir),
        plan=[{"file": f, "action": "restore"} for f in files_to_restore],
        results=results,
        snapshot_path=str(snapshot_path) if remaining_operations else None,
    )

    return {
        "status": "success",
        "message": f"选择性回滚完成：成功 {success_count} 个，共 {len(results)} 个",
        "restored": success_count,
        "total": len(results),
        "results": results,
        "has_remaining": len(remaining_operations) > 0,
        "remaining_count": len(remaining_operations),
        "history_id": history_id,
    }


def execute_plan_async(task_id: str, target_path: str, plan: list) -> None:
    from models.schemas import ActionPlanItem
    from utils.security import get_target_dir
    
    update_task_progress(task_id, status="running", message="开始执行炼金计划")
    
    move_count = 0
    delete_count = 0
    rename_count = 0
    keep_count = 0
    
    try:
        target_dir = get_target_dir(target_path)
        results = []
        snapshot_path = get_snapshot_path(target_dir)
        
        if snapshot_path.exists():
            update_task_progress(task_id, status="failed", error="检测到未回滚的 snapshot，请先执行 Undo 后再运行新的炼金计划。")
            return
        
        snapshot_operations = []
        
        for i, item in enumerate(plan):
            if is_task_cancelled(task_id):
                update_task_progress(task_id, status="cancelled", message=f"任务已取消，已处理 {i} 个文件")
                return
            
            action = getattr(item, "action", None) or (item.get("action") if isinstance(item, dict) else None)
            if action not in ALLOWED_ACTIONS:
                update_task_progress(task_id, status="failed", error=f"不支持的操作：{action}")
                return
            
            if action in {"rename_and_move", "move"}:
                target_path_item = getattr(item, "target_path", None) or (item.get("target_path") if isinstance(item, dict) else None)
                if not target_path_item:
                    update_task_progress(task_id, status="failed", error=f"{action} 操作缺少 target_path。")
                    return
        
        total_items = len(plan)
        for i, item in enumerate(plan):
            if is_task_cancelled(task_id):
                update_task_progress(task_id, status="cancelled", message=f"任务已取消，已处理 {i} 个文件")
                return
            
            file_name = getattr(item, "file", None) or (item.get("file") if isinstance(item, dict) else "")
            action = getattr(item, "action", None) or (item.get("action") if isinstance(item, dict) else None)
            
            update_task_progress(
                task_id,
                current=i + 1,
                message=f"正在处理 {i + 1}/{total_items}：{file_name}",
                current_file=file_name,
            )
            
            if action not in ALLOWED_ACTIONS:
                result_item = {
                    "file": file_name,
                    "action": action,
                    "original_path": file_name,
                    "new_path": None,
                    "status": "skipped",
                    "message": f"不支持的操作：{action}",
                }
                results.append(result_item)
                continue
            
            source_path = resolve_inside_target(target_dir, file_name)
            if not source_path.exists():
                result_item = {
                    "file": file_name,
                    "action": action,
                    "original_path": file_name,
                    "new_path": None,
                    "status": "skipped",
                    "message": "源文件不存在，可能已被处理。",
                }
                results.append(result_item)
                update_task_progress(task_id, completed_item=result_item)
                continue
            
            if action == "delete":
                trash_path = resolve_inside_target(
                    target_dir,
                    f".alchemy_trash/{uuid.uuid4().hex}/{Path(file_name).name}",
                )
                trash_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source_path), str(trash_path))
                snapshot_operations.append(
                    {
                        "action": action,
                        "original_path": file_name,
                        "new_path": to_target_relative(target_dir, trash_path),
                    }
                )
                result_item = {
                    "file": file_name,
                    "action": action,
                    "original_path": file_name,
                    "new_path": to_target_relative(target_dir, trash_path),
                    "absolute_original_path": str(source_path),
                    "absolute_new_path": str(trash_path),
                    "status": "success",
                }
                results.append(result_item)
                delete_count += 1
                update_task_progress(task_id, delete_done=delete_count, completed_item=result_item)
                continue
            
            if action == "keep":
                result_item = {
                    "file": file_name,
                    "action": action,
                    "original_path": file_name,
                    "new_path": file_name,
                    "absolute_original_path": str(source_path),
                    "absolute_new_path": str(source_path),
                    "status": "success",
                }
                results.append(result_item)
                keep_count += 1
                update_task_progress(task_id, keep_done=keep_count, completed_item=result_item)
                continue
            
            target_path_item = getattr(item, "target_path", None) or (item.get("target_path") if isinstance(item, dict) else None)
            
            if action == "move":
                target_path_resolved = resolve_inside_target(target_dir, target_path_item)
                target_path_resolved.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.move(str(source_path), str(target_path_resolved))
                snapshot_operations.append(
                    {
                        "action": action,
                        "original_path": file_name,
                        "new_path": target_path_item,
                    }
                )
                result_item = {
                    "file": file_name,
                    "action": action,
                    "original_path": file_name,
                    "target_path": target_path_item,
                    "new_path": target_path_item,
                    "absolute_original_path": str(source_path),
                    "absolute_new_path": str(target_path_resolved),
                    "status": "success",
                }
                results.append(result_item)
                move_count += 1
                update_task_progress(task_id, move_done=move_count, completed_item=result_item)
                continue
            
            if action == "rename_and_move":
                target_path_resolved = resolve_inside_target(target_dir, target_path_item)
                target_path_resolved.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.move(str(source_path), str(target_path_resolved))
                snapshot_operations.append(
                    {
                        "action": action,
                        "original_path": file_name,
                        "new_path": target_path_item,
                    }
                )
                result_item = {
                    "file": file_name,
                    "action": action,
                    "original_path": file_name,
                    "target_path": target_path_item,
                    "new_path": target_path_item,
                    "absolute_original_path": str(source_path),
                    "absolute_new_path": str(target_path_resolved),
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
        plan_dict = []
        for p in plan:
            if isinstance(p, ActionPlanItem):
                plan_dict.append(p.dict())
            elif isinstance(p, dict):
                plan_dict.append(p)
            else:
                plan_dict.append({})
        
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


def score_plan_confidence(plan: list[dict], files_info: list[dict]) -> list[dict]:
    """为计划中的每条操作计算置信度评分。
    
    评分规则：
    - keep 操作默认高置信度 (0.9)
    - delete 操作基于文件名模式（临时文件高置信度）
    - move/rename_and_move 基于分类匹配度和路径合理性
    
    Args:
        plan: 计划列表
        files_info: 文件信息列表
        
    Returns:
        带置信度的计划列表
    """
    from utils.helpers import is_temp_file, classify_file
    
    file_map = {f["path"]: f for f in files_info}
    
    scored_plan = []
    for item in plan:
        confidence = 0.7  # 基础置信度
        confidence_reasons = []
        
        action = item.get("action", "")
        file_path = item.get("file", "")
        target_path = item.get("target_path", "")
        file_info = file_map.get(file_path, {})
        filename = file_info.get("name", file_path.split("/")[-1])
        category = file_info.get("category", "unknown")
        
        # keep 操作：高置信度
        if action == "keep":
            confidence = 0.9
            confidence_reasons.append("保留操作通常安全")
        
        # delete 操作：基于临时文件模式
        elif action == "delete":
            if is_temp_file(filename):
                confidence = 0.95
                confidence_reasons.append("匹配临时文件模式")
            elif filename.startswith("."):
                confidence = 0.85
                confidence_reasons.append("隐藏文件")
            else:
                confidence = 0.5
                confidence_reasons.append("非临时文件删除，建议确认")
        
        # move/rename_and_move 操作
        elif action in {"move", "rename_and_move"}:
            if target_path:
                # 检查目标路径是否与文件分类一致
                target_lower = target_path.lower()
                if category == "logs" and "log" in target_lower:
                    confidence = 0.9
                    confidence_reasons.append("目标路径与日志分类匹配")
                elif category == "images" and "image" in target_lower:
                    confidence = 0.9
                    confidence_reasons.append("目标路径与图片分类匹配")
                elif category == "documents" and "doc" in target_lower:
                    confidence = 0.85
                    confidence_reasons.append("目标路径与文档分类匹配")
                elif category == "code" and "code" in target_lower:
                    confidence = 0.85
                    confidence_reasons.append("目标路径与代码分类匹配")
                else:
                    confidence = 0.7
                    confidence_reasons.append("目标路径与文件分类未明确匹配")
                
                # 检查是否有 extracted_info（LLM 提取了信息）
                extracted = item.get("extracted_info")
                if extracted and isinstance(extracted, dict):
                    info_type = extracted.get("type", "none")
                    if info_type in {"financial", "system_log"}:
                        confidence = min(confidence + 0.1, 1.0)
                        confidence_reasons.append(f"LLM 提取了 {info_type} 信息")
            else:
                confidence = 0.4
                confidence_reasons.append("缺少目标路径")
        
        scored_item = {**item}
        scored_item["confidence"] = round(confidence, 2)
        scored_item["confidence_level"] = (
            "high" if confidence >= 0.85 else
            "medium" if confidence >= 0.65 else
            "low"
        )
        scored_item["confidence_reasons"] = confidence_reasons
        scored_plan.append(scored_item)
    
    return scored_plan


def detect_plan_conflicts(plan: list[dict], target_dir: Path) -> dict:
    """检测计划中的冲突。
    
    检测项目：
    1. 目标路径重复（多个文件移到同一位置）
    2. 目标路径已存在
    3. 源文件不存在
    4. 循环依赖（A -> B, B -> A）
    
    Args:
        plan: 计划列表
        target_dir: 目标目录
        
    Returns:
        冲突检测结果
    """
    conflicts = []
    warnings = []
    
    # 检测目标路径重复
    target_paths = {}
    for i, item in enumerate(plan):
        target = item.get("target_path")
        if target and item.get("action") in {"move", "rename_and_move"}:
            if target in target_paths:
                conflicts.append({
                    "type": "duplicate_target",
                    "severity": "error",
                    "message": f"目标路径冲突：'{item['file']}' 和 '{target_paths[target]}' 都要移到 '{target}'",
                    "files": [item["file"], target_paths[target]],
                    "target_path": target,
                })
            else:
                target_paths[target] = item["file"]
    
    # 检测目标路径已存在
    for item in plan:
        target = item.get("target_path")
        if target and item.get("action") in {"move", "rename_and_move"}:
            try:
                full_target = resolve_inside_target(target_dir, target)
                if full_target.exists():
                    # 检查是否是源文件本身（rename 操作）
                    source = resolve_inside_target(target_dir, item["file"])
                    if full_target.resolve() != source.resolve():
                        conflicts.append({
                            "type": "target_exists",
                            "severity": "error",
                            "message": f"目标路径已存在：'{target}'",
                            "file": item["file"],
                            "target_path": target,
                        })
            except Exception:
                pass
    
    # 检测源文件不存在
    for item in plan:
        try:
            source = resolve_inside_target(target_dir, item["file"])
            if not source.exists():
                warnings.append({
                    "type": "source_missing",
                    "severity": "warning",
                    "message": f"源文件不存在：'{item['file']}'（可能已被处理）",
                    "file": item["file"],
                })
        except Exception:
            pass
    
    # 检测循环依赖
    move_map = {}
    for item in plan:
        if item.get("action") in {"move", "rename_and_move"} and item.get("target_path"):
            move_map[item["file"]] = item["target_path"]
    
    for source, target in move_map.items():
        if target in move_map:
            conflicts.append({
                "type": "circular_dependency",
                "severity": "error",
                "message": f"循环依赖：'{source}' -> '{target}'，而 '{target}' 也在移动计划中",
                "files": [source, target],
            })
    
    return {
        "has_conflicts": len(conflicts) > 0,
        "has_warnings": len(warnings) > 0,
        "conflicts": conflicts,
        "warnings": warnings,
        "total_conflicts": len(conflicts),
        "total_warnings": len(warnings),
    }
