import threading
import uuid
from datetime import datetime

from models.schemas import TaskProgress, TaskType, TaskStatus


_task_store: dict[str, TaskProgress] = {}
_task_lock = threading.Lock()
_task_cancellation_flags: dict[str, bool] = {}


def _format_eta(seconds: float) -> str:
    if seconds is None or seconds < 0:
        return "计算中..."
    if seconds < 1:
        return "即将完成"
    if seconds < 60:
        return f"{int(seconds)}秒"
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}分{secs}秒" if secs > 0 else f"{minutes}分钟"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}小时{minutes}分" if minutes > 0 else f"{hours}小时"


def create_task(
    task_type: TaskType, 
    total: int = 0,
    plan: list | None = None,
) -> str:
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    
    move_total = 0
    delete_total = 0
    rename_total = 0
    keep_total = 0
    
    if plan:
        for item in plan:
            action = getattr(item, "action", None) or (item.get("action") if isinstance(item, dict) else None)
            if action == "move":
                move_total += 1
            elif action == "delete":
                delete_total += 1
            elif action == "rename_and_move":
                rename_total += 1
            elif action == "keep":
                keep_total += 1
    
    with _task_lock:
        _task_store[task_id] = TaskProgress(
            task_id=task_id,
            task_type=task_type,
            status="pending",
            total=total,
            current=0,
            message="任务已创建，等待执行",
            current_file="",
            start_time=datetime.now().isoformat(),
            end_time=None,
            error=None,
            result=None,
            move_total=move_total,
            move_done=0,
            delete_total=delete_total,
            delete_done=0,
            rename_total=rename_total,
            rename_done=0,
            keep_total=keep_total,
            keep_done=0,
            completed_items=[],
            eta_seconds=None,
            items_per_second=None,
            formatted_eta="计算中...",
        )
        _task_cancellation_flags[task_id] = False
    return task_id


def get_task(task_id: str) -> TaskProgress | None:
    with _task_lock:
        return _task_store.get(task_id)


def update_task_progress(
    task_id: str,
    current: int | None = None,
    message: str | None = None,
    current_file: str | None = None,
    status: TaskStatus | None = None,
    error: str | None = None,
    result: dict | None = None,
    move_done: int | None = None,
    delete_done: int | None = None,
    rename_done: int | None = None,
    keep_done: int | None = None,
    completed_item: dict | None = None,
):
    with _task_lock:
        task = _task_store.get(task_id)
        if not task:
            return
        
        if current is not None:
            task.current = current

            if task.current > 0 and task.start_time:
                try:
                    start_dt = datetime.fromisoformat(task.start_time)
                    elapsed = (datetime.now() - start_dt).total_seconds()
                    if elapsed > 0:
                        task.items_per_second = task.current / elapsed
                        remaining = task.total - task.current
                        if task.items_per_second > 0:
                            task.eta_seconds = remaining / task.items_per_second
                            task.formatted_eta = _format_eta(task.eta_seconds)
                        else:
                            task.eta_seconds = None
                            task.formatted_eta = "计算中..."
                    else:
                        task.eta_seconds = None
                        task.formatted_eta = "计算中..."
                except (ValueError, TypeError):
                    task.eta_seconds = None
                    task.formatted_eta = "计算中..."
        
        if message is not None:
            task.message = message
        if current_file is not None:
            task.current_file = current_file
        if status is not None:
            task.status = status
            if status in {"completed", "cancelled", "failed"}:
                task.end_time = datetime.now().isoformat()
                task.eta_seconds = 0
                task.formatted_eta = "已完成" if status == "completed" else ("已取消" if status == "cancelled" else "失败")
        if error is not None:
            task.error = error
        if result is not None:
            task.result = result
        
        if move_done is not None:
            task.move_done = move_done
        if delete_done is not None:
            task.delete_done = delete_done
        if rename_done is not None:
            task.rename_done = rename_done
        if keep_done is not None:
            task.keep_done = keep_done
        
        if completed_item is not None:
            task.completed_items.append(completed_item)
            if len(task.completed_items) > 100:
                task.completed_items = task.completed_items[-50:]


def is_task_cancelled(task_id: str) -> bool:
    with _task_lock:
        return _task_cancellation_flags.get(task_id, False)


def cancel_task(task_id: str) -> bool:
    with _task_lock:
        if task_id not in _task_store:
            return False
        _task_cancellation_flags[task_id] = True
        task = _task_store[task_id]
        if task.status in {"pending", "running"}:
            task.status = "cancelled"
            task.end_time = datetime.now().isoformat()
        return True


def cleanup_old_tasks(max_age_hours: int = 24):
    with _task_lock:
        now = datetime.now()
        task_ids_to_remove = []
        for task_id, task in _task_store.items():
            if task.end_time:
                try:
                    end_time = datetime.fromisoformat(task.end_time)
                    if (now - end_time).total_seconds() > max_age_hours * 3600:
                        task_ids_to_remove.append(task_id)
                except (ValueError, TypeError):
                    task_ids_to_remove.append(task_id)
        for task_id in task_ids_to_remove:
            del _task_store[task_id]
            if task_id in _task_cancellation_flags:
                del _task_cancellation_flags[task_id]
