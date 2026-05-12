"""Local Data Alchemist 后端入口。

提供文件扫描、AI 计划生成、执行/回滚、重命名、去重、模板管理等功能。
"""

import os
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog

from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models.schemas import (
    FileInfo,
    PlanRequest,
    FolderRequest,
    ActionPlanItem,
    ExecutePlanRequest,
    UndoPlanRequest,
    SelectiveUndoRequest,
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
    selective_undo_impl,
    execute_plan_async,
    llm_debug_info,
    llm_health_info,
    build_directory_tree,
    score_plan_confidence,
    detect_plan_conflicts,
    multi_scan,
    multi_generate_plan,
)

from contracts import rename_preview_response, rename_execute_response
from services.export_service import generate_pdf_report, generate_excel_export


# ---------------------------------------------------------------------------
# 环境变量加载
# ---------------------------------------------------------------------------
ENV_PATH = Path(__file__).resolve().with_name(".env")
load_dotenv(dotenv_path=ENV_PATH, override=True)

# ---------------------------------------------------------------------------
# CORS 允许来源（可通过环境变量 CORS_ORIGINS 配置，默认仅允许本地开发）
# ---------------------------------------------------------------------------
_cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
CORS_ORIGINS: list[str] = [o.strip() for o in _cors_origins_str.split(",") if o.strip()]

# ---------------------------------------------------------------------------
# FastAPI 应用
# ---------------------------------------------------------------------------
app = FastAPI(title="Local Data Alchemist", version="phase7-refactored")
APP_VERSION = "phase7-native-fs-stable-2026-04-11"

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API Router（统一 /api 前缀，消除重复路由注册）
# ---------------------------------------------------------------------------
api_router = APIRouter(prefix="/api")


# ========================= 根路由 & 健康检查 =========================

@app.get("/")
async def root():
    """根路由健康检查。"""
    return {
        "status": "ok",
        "version": APP_VERSION,
        "message": "Local Data Alchemist Backend API - Refactored Structure",
    }


@api_router.get("/llm_debug")
async def llm_debug():
    """LLM 调试信息。"""
    return llm_debug_info()


@api_router.get("/llm_health")
async def llm_health(check_connection: bool = False):
    """LLM 健康检查。"""
    return llm_health_info(check_connection=check_connection)


# ========================= 目录选择 =========================

@api_router.get("/select_folder")
def select_folder():
    """唤起系统目录选择器并扫描文件。"""
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


# ========================= 核心操作 =========================

@api_router.post("/lock_folder")
async def lock_folder(request: FolderRequest):
    """锁定目标目录并扫描文件。"""
    return await lock_folder_impl(request)


@api_router.post("/generate_plan")
async def generate_plan(request: PlanRequest):
    """生成 AI 整理计划。"""
    return await generate_plan_impl(request)


@api_router.post("/execute_plan")
async def execute_plan(request: ExecutePlanRequest):
    """同步执行计划。"""
    return await execute_plan_impl(request)


@api_router.post("/undo_plan")
async def undo_plan(request: UndoPlanRequest):
    """回滚已执行的计划。"""
    return await undo_plan_impl(request)


@api_router.post("/selective_undo")
async def api_selective_undo(request: SelectiveUndoRequest):
    """选择性回滚：仅回滚指定的文件。"""
    try:
        return selective_undo_impl(request.target_path, request.files)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"选择性回滚失败：{str(exc)}") from exc


# ========================= 导出功能 =========================

@api_router.post("/export_pdf")
async def api_export_pdf(request: FolderRequest):
    """导出 PDF 整理报告。"""
    try:
        target_dir = get_target_dir(request.target_path)
        files_info = scan_target_files(target_dir)
        analysis = build_analysis(files_info)
        return generate_pdf_report(
            target_path=str(target_dir),
            files_info=files_info,
            analysis=analysis,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"导出 PDF 失败：{str(exc)}") from exc


@api_router.post("/export_excel")
async def api_export_excel(request: FolderRequest):
    """导出 Excel 文件清单。"""
    try:
        target_dir = get_target_dir(request.target_path)
        files_info = scan_target_files(target_dir)
        return generate_excel_export(
            target_path=str(target_dir),
            files_info=files_info,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"导出 Excel 失败：{str(exc)}") from exc


# ========================= 文件预览 =========================

@api_router.post("/preview_file")
async def preview_file(request: FilePreviewRequest):
    """预览文件内容。"""
    try:
        target_dir = get_target_dir(request.target_path)
        return preview_file_impl(target_dir, request.file_path)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文件预览失败：{str(exc)}") from exc


# ========================= 历史记录 =========================

@api_router.post("/list_history")
async def api_list_history(request: ListHistoryRequest):
    """列出操作历史记录。"""
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


@api_router.post("/get_history")
async def get_history_detail(request: GetHistoryRequest):
    """获取历史记录详情。"""
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


# ========================= 目录树预览 =========================

@api_router.post("/directory_tree")
async def api_directory_tree(request: FolderRequest):
    """获取目录树结构，可选包含计划预览。"""
    try:
        target_dir = get_target_dir(request.target_path)
        tree = build_directory_tree(target_dir)
        return {
            "status": "success",
            "target_path": str(target_dir),
            "tree": tree,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取目录树失败：{str(exc)}") from exc


# ========================= 计划分析 =========================

@api_router.post("/analyze_plan")
async def api_analyze_plan(request: ExecutePlanRequest):
    """分析计划：置信度评分 + 冲突检测。"""
    try:
        target_dir = get_target_dir(request.target_path)
        files_info = scan_target_files(target_dir)
        
        plan_dicts = [item.dict() for item in request.plan]
        
        scored_plan = score_plan_confidence(plan_dicts, files_info)
        conflict_result = detect_plan_conflicts(plan_dicts, target_dir)
        
        return {
            "status": "success",
            "scored_plan": scored_plan,
            "conflicts": conflict_result,
            "summary": {
                "total_items": len(scored_plan),
                "high_confidence": sum(1 for s in scored_plan if s.get("confidence_level") == "high"),
                "medium_confidence": sum(1 for s in scored_plan if s.get("confidence_level") == "medium"),
                "low_confidence": sum(1 for s in scored_plan if s.get("confidence_level") == "low"),
                "has_conflicts": conflict_result["has_conflicts"],
                "has_warnings": conflict_result["has_warnings"],
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"分析计划失败：{str(exc)}") from exc


# ========================= 重复文件检测 =========================

@api_router.post("/detect_duplicates")
async def api_detect_duplicates(request: DetectDuplicatesRequest):
    """检测重复文件。"""
    try:
        target_dir = get_target_dir(request.target_path)
        return detect_duplicates(target_dir, request.fast_mode)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"检测重复文件失败：{str(exc)}") from exc


@api_router.post("/keep_duplicate")
async def api_keep_duplicate(request: KeepDuplicateRequest):
    """保留指定文件，删除其余重复文件。"""
    try:
        return keep_duplicate(request)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"处理重复文件失败：{str(exc)}") from exc


# ========================= 模板管理 =========================

@api_router.get("/list_templates")
async def api_list_templates():
    """列出所有模板。"""
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


@api_router.post("/get_template")
async def api_get_template(request: GetTemplateRequest):
    """获取模板详情。"""
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


@api_router.post("/save_template")
async def api_save_template(request: SaveTemplateRequest):
    """保存用户模板。"""
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


@api_router.post("/delete_template")
async def api_delete_template(request: DeleteTemplateRequest):
    """删除用户模板。"""
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


@api_router.post("/apply_template")
async def api_apply_template(request: ApplyTemplateRequest):
    """应用模板生成计划。"""
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


# ========================= 批量重命名 =========================

@api_router.post("/rename_preview")
async def api_rename_preview(request: RenamePreviewRequest):
    """预览批量重命名结果。"""
    try:
        target_dir = get_target_dir(request.target_path)

        result = generate_rename_preview(
            target_dir=target_dir,
            selected_files=request.selected_files,
            rules=request.rules
        )

        return rename_preview_response(result)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成重命名预览失败：{str(exc)}") from exc


@api_router.post("/rename_execute")
async def api_rename_execute(request: RenameExecuteRequest):
    """执行批量重命名。"""
    try:
        target_dir = get_target_dir(request.target_path)

        result = execute_rename_plan(
            target_dir=target_dir,
            rename_plan=request.rename_plan
        )

        return rename_execute_response(result)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"执行重命名失败：{str(exc)}") from exc


# ========================= 仪表盘 =========================

@api_router.post("/dashboard_stats")
async def api_dashboard_stats(request: DashboardStatsRequest):
    """获取仪表盘统计数据。"""
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


# ========================= 计划预览 =========================

@api_router.post("/preview_plan")
async def api_preview_plan(request: PreviewPlanRequest):
    """预览计划执行效果。"""
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


# ========================= 多目录处理 =========================

@api_router.post("/multi_scan")
async def api_multi_scan(request: MultiTargetRequest):
    """多目录扫描。"""
    try:
        return multi_scan(request.target_paths)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"多目录扫描失败：{str(exc)}") from exc


@api_router.post("/multi_generate_plan")
async def api_multi_generate_plan(request: MultiTargetRequest):
    """多目录计划生成。"""
    try:
        return multi_generate_plan(request.target_paths)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"多目录计划生成失败：{str(exc)}") from exc


# ========================= 任务管理 =========================

@api_router.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    """查询异步任务状态。"""
    try:
        task = get_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在：{task_id}")

        return {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "status": task.status,
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
            "formatted_eta": task.formatted_eta,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取任务状态失败：{str(exc)}") from exc


@api_router.post("/cancel_task")
async def api_cancel_task(request: CancelTaskRequest):
    """取消运行中的任务。"""
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


@api_router.post("/start_execute_task")
async def api_start_execute_task(request: ExecutePlanRequest):
    """启动异步执行任务。"""
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
            "status": "started",
            "message": "任务已启动",
            "task_id": task_id,
            "total_items": len(request.plan),
            "task": {
                "task_id": task.task_id if task else task_id,
                "task_type": task.task_type if task else "execute_plan",
                "status": task.status if task else "running",
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


# ---------------------------------------------------------------------------
# 注册 API Router
# ---------------------------------------------------------------------------
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8002))
    uvicorn.run(app, host="127.0.0.1", port=port)
