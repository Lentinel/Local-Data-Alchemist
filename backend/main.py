import os
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models.schemas import (
    FileInfo,
    PlanRequest,
    FolderRequest,
    ActionPlanItem,
    ExecutePlanRequest,
    UndoPlanRequest,
    FilePreviewRequest,
    ListHistoryRequest,
    GetHistoryRequest,
    DetectDuplicatesRequest,
    KeepDuplicateRequest,
    TemplateRule,
    AlchemyTemplate,
    ListTemplatesRequest,
    GetTemplateRequest,
    SaveTemplateRequest,
    DeleteTemplateRequest,
    ApplyTemplateRequest,
    RenameRule,
    RenamePreviewRequest,
    RenameExecuteRequest,
    DashboardStatsRequest,
    MultiTargetRequest,
    MultiExecuteRequest,
    TaskProgress,
    TaskStatusResponse,
    CancelTaskRequest,
    PreviewPlanRequest,
    TaskStatus,
    TaskType,
)

from utils.security import (
    get_target_dir,
    resolve_inside_target,
    to_target_relative,
)

from utils.storage import (
    list_history,
    get_history,
)

from utils.task_manager import (
    create_task,
    get_task,
    update_task_progress,
    is_task_cancelled,
    cancel_task,
    cleanup_old_tasks,
)

from services import (
    scan_target_files,
    get_file_preview,
    build_analysis,
    build_file_snippets,
    calculate_dashboard_stats,
    preview_plan_impl,
    preview_file_impl,
    load_all_templates,
    find_template,
    save_user_template,
    delete_user_template,
    apply_template_to_files,
    generate_rename_preview,
    execute_rename_plan,
    detect_duplicates,
    keep_duplicate,
    generate_plan_impl,
    lock_folder_impl,
    execute_plan_impl,
    undo_plan_impl,
    execute_plan_async,
    llm_debug_info,
    multi_scan,
    multi_generate_plan,
)


ENV_PATH = Path(__file__).resolve().with_name(".env")
load_dotenv(dotenv_path=ENV_PATH, override=True)

app = FastAPI()
APP_VERSION = "phase7-native-fs-stable-2026-04-11"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "version": APP_VERSION,
        "message": "Local Data Alchemist Backend API - Refactored Structure",
    }


@app.get("/llm_debug")
@app.get("/api/llm_debug")
async def llm_debug():
    return llm_debug_info()


@app.get("/select_folder")
@app.get("/api/select_folder")
def select_folder():
    root = None
    try:
        root = tk.Tk()
        root.attributes('-topmost', True)
        root.withdraw()
        
        selected_path = filedialog.askdirectory(
            title='Select Local Data Alchemist Target',
            initialdir=os.path.expanduser('~')
        )

        if not selected_path or selected_path == () or (isinstance(selected_path, str) and not selected_path.strip()):
            return {"status": "cancelled", "target_path": None}

        target_dir = get_target_dir(selected_path)
        files_info = scan_target_files(target_dir)
        return {
            "status": "success",
            "target_path": str(target_dir),
            "files": files_info,
            "analysis": build_analysis(files_info),
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"本地文件夹选择器启动失败：{str(exc)}") from exc
    finally:
        if root:
            try:
                root.update()
                root.destroy()
            except Exception:
                pass


@app.post("/lock_folder")
@app.post("/api/lock_folder")
async def lock_folder(request: FolderRequest):
    return await lock_folder_impl(request)


@app.post("/generate_plan")
@app.post("/api/generate_plan")
async def generate_plan(request: PlanRequest):
    return await generate_plan_impl(request)


@app.post("/execute_plan")
@app.post("/api/execute_plan")
async def execute_plan(request: ExecutePlanRequest):
    return await execute_plan_impl(request)


@app.post("/undo_plan")
@app.post("/api/undo_plan")
async def undo_plan(request: UndoPlanRequest):
    return await undo_plan_impl(request)


@app.post("/preview_file")
@app.post("/api/preview_file")
async def preview_file(request: FilePreviewRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        return preview_file_impl(target_dir, request.file_path)
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文件预览失败：{str(exc)}") from exc


@app.post("/list_history")
@app.post("/api/list_history")
async def api_list_history(request: ListHistoryRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        history_list = list_history(target_dir)
        
        simplified_history = []
        for item in history_list:
            simplified_history.append({
                "id": item.get("id"),
                "type": item.get("type"),
                "target_path": item.get("target_path"),
                "created_at": item.get("created_at"),
                "results_count": len(item.get("results", [])),
                "snapshot_path": item.get("snapshot_path"),
            })
        
        return {
            "status": "success",
            "history": simplified_history,
            "total": len(simplified_history),
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败：{str(exc)}") from exc


@app.post("/get_history")
@app.post("/api/get_history")
async def get_history_detail(request: GetHistoryRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        history = get_history(target_dir, request.history_id)
        
        return {
            "status": "success",
            "history": history,
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取历史记录详情失败：{str(exc)}") from exc


@app.post("/detect_duplicates")
@app.post("/api/detect_duplicates")
async def api_detect_duplicates(request: DetectDuplicatesRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        return detect_duplicates(target_dir, request.fast_mode)
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"检测重复文件失败：{str(exc)}") from exc


@app.post("/keep_duplicate")
@app.post("/api/keep_duplicate")
async def api_keep_duplicate(request: KeepDuplicateRequest):
    try:
        return keep_duplicate(request)
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"处理重复文件失败：{str(exc)}") from exc


@app.get("/list_templates")
@app.get("/api/list_templates")
async def api_list_templates():
    try:
        templates = load_all_templates()
        
        simplified = []
        for template in templates:
            simplified.append({
                "id": template.get("id"),
                "name": template.get("name"),
                "description": template.get("description"),
                "icon": template.get("icon", "📁"),
                "is_builtin": template.get("is_builtin", False),
                "created_at": template.get("created_at"),
                "updated_at": template.get("updated_at"),
                "rules_count": len(template.get("rules", [])),
            })
        
        return {
            "status": "success",
            "templates": simplified,
            "total": len(simplified),
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取模板列表失败：{str(exc)}") from exc


@app.post("/get_template")
@app.post("/api/get_template")
async def api_get_template(request: GetTemplateRequest):
    try:
        template = find_template(request.template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"模板不存在：{request.template_id}")
        
        return {
            "status": "success",
            "template": template,
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取模板详情失败：{str(exc)}") from exc


@app.post("/save_template")
@app.post("/api/save_template")
async def api_save_template(request: SaveTemplateRequest):
    try:
        template_data = request.template
        
        if not template_data:
            raise HTTPException(status_code=400, detail="模板数据不能为空")
        
        if not template_data.get("name"):
            raise HTTPException(status_code=400, detail="模板名称不能为空")
        
        saved = save_user_template(template_data)
        
        return {
            "status": "success",
            "template": saved,
            "message": "模板保存成功",
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"保存模板失败：{str(exc)}") from exc


@app.post("/delete_template")
@app.post("/api/delete_template")
async def api_delete_template(request: DeleteTemplateRequest):
    try:
        if request.template_id.startswith("builtin-"):
            raise HTTPException(status_code=400, detail="内置模板不可删除")
        
        success = delete_user_template(request.template_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"模板不存在或无法删除：{request.template_id}")
        
        return {
            "status": "success",
            "message": "模板删除成功",
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"删除模板失败：{str(exc)}") from exc


@app.post("/apply_template")
@app.post("/api/apply_template")
async def api_apply_template(request: ApplyTemplateRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        
        template = find_template(request.template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"模板不存在：{request.template_id}")
        
        files_info = scan_target_files(target_dir)
        
        plan = apply_template_to_files(template, files_info, target_dir)
        
        return {
            "status": "success",
            "mode": "template-apply",
            "template_id": request.template_id,
            "template_name": template.get("name"),
            "target_path": str(target_dir),
            "analysis": build_analysis(files_info),
            "files": build_file_snippets(target_dir, [FileInfo(**f) for f in files_info]),
            "file_inventory": files_info,
            "plan": plan,
            "reasoning_trace": [
                f"已锁定本地目标目录：{target_dir}",
                f"本地扫描完成：共发现 {len(files_info)} 个文件",
                f"应用模板：{template.get('name')}",
                f"生成计划：共 {len(plan)} 条 Action",
            ],
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"应用模板失败：{str(exc)}") from exc


@app.post("/rename_preview")
@app.post("/api/rename_preview")
async def api_rename_preview(request: RenamePreviewRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        
        result = generate_rename_preview(
            target_dir=target_dir,
            selected_files=request.selected_files,
            rules=request.rules
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成重命名预览失败：{str(exc)}") from exc


@app.post("/rename_execute")
@app.post("/api/rename_execute")
async def api_rename_execute(request: RenameExecuteRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        
        results = execute_rename_plan(
            target_dir=target_dir,
            rename_plan=request.rename_plan
        )
        
        success_count = len([r for r in results if r.get("status") == "success"])
        failed_count = len([r for r in results if r.get("status") == "failed"])
        
        return {
            "status": "success",
            "results": results,
            "success_count": success_count,
            "failed_count": failed_count,
            "message": f"重命名完成：成功 {success_count} 个，失败 {failed_count} 个",
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"执行重命名失败：{str(exc)}") from exc


@app.post("/dashboard_stats")
@app.post("/api/dashboard_stats")
async def api_dashboard_stats(request: DashboardStatsRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        files_info = scan_target_files(target_dir)
        
        stats = calculate_dashboard_stats(
            target_dir=target_dir,
            files_info=files_info,
            include_history=True
        )
        
        return {
            "status": "success",
            "target_path": str(target_dir),
            "stats": stats,
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取仪表盘统计失败：{str(exc)}") from exc


@app.post("/preview_plan")
@app.post("/api/preview_plan")
async def api_preview_plan(request: PreviewPlanRequest):
    try:
        target_dir = get_target_dir(request.target_path)
        
        preview = preview_plan_impl(
            target_dir=target_dir,
            plan=request.plan
        )
        
        return preview
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"预览计划失败：{str(exc)}") from exc


@app.post("/multi_scan")
@app.post("/api/multi_scan")
async def api_multi_scan(request: MultiTargetRequest):
    try:
        return multi_scan(request.target_paths)
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"多目录扫描失败：{str(exc)}") from exc


@app.post("/multi_generate_plan")
@app.post("/api/multi_generate_plan")
async def api_multi_generate_plan(request: MultiTargetRequest):
    try:
        return multi_generate_plan(request.target_paths)
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"多目录计划生成失败：{str(exc)}") from exc


@app.get("/task_status/{task_id}")
@app.get("/api/task_status/{task_id}")
async def get_task_status(task_id: str):
    try:
        task = get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在：{task_id}")
        
        return {
            "status": "success",
            "task_id": task.task_id,
            "task_type": task.task_type,
            "current_status": task.status,
            "percentage": task.percentage,
            "total": task.total,
            "current": task.current,
            "message": task.message,
            "current_file": task.current_file,
            "start_time": task.start_time,
            "end_time": task.end_time,
            "error": task.error,
            "result": task.result,
            "move_total": task.move_total,
            "move_done": task.move_done,
            "delete_total": task.delete_total,
            "delete_done": task.delete_done,
            "rename_total": task.rename_total,
            "rename_done": task.rename_done,
            "keep_total": task.keep_total,
            "keep_done": task.keep_done,
            "completed_items": task.completed_items if len(task.completed_items) <= 50 else task.completed_items[-50:],
            "eta_seconds": task.eta_seconds,
            "items_per_second": task.items_per_second,
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取任务状态失败：{str(exc)}") from exc


@app.post("/cancel_task")
@app.post("/api/cancel_task")
async def api_cancel_task(request: CancelTaskRequest):
    try:
        success = cancel_task(request.task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"任务不存在或无法取消：{request.task_id}")
        
        return {
            "status": "success",
            "message": f"任务已取消：{request.task_id}",
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"取消任务失败：{str(exc)}") from exc


@app.post("/start_execute_task")
@app.post("/api/start_execute_task")
async def api_start_execute_task(request: ExecutePlanRequest):
    try:
        task_id = create_task(
            task_type="execute_plan",
            total=len(request.plan),
            plan=request.plan
        )
        
        thread = threading.Thread(
            target=execute_plan_async,
            args=(
                task_id,
                request.target_path,
                request.plan,
            ),
            daemon=True
        )
        thread.start()
        
        task = get_task(task_id)
        
        return {
            "status": "success",
            "message": "任务已启动",
            "task_id": task_id,
            "task": {
                "task_id": task.task_id if task else task_id,
                "task_type": "execute_plan" if task else task.task_type,
                "status": "running" if task else task.status,
                "percentage": 0.0,
                "total": len(request.plan),
                "current": 0,
                "message": "任务已创建，等待执行",
                "current_file": "",
                "start_time": task.start_time if task else None,
                "end_time": None,
                "error": None,
                "result": None,
            },
        }
    
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"启动任务失败：{str(exc)}") from exc


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
