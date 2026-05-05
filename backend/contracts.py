"""
响应组装函数：确保接口返回结构与前端契约一致。
"""


def rename_preview_response(result: dict) -> dict:
    """
    组装 /api/rename_preview 响应。
    确保前端依赖的字段都在顶层。
    """
    previews = result.get("previews", [])
    conflicts = result.get("conflicts", [])
    warnings = result.get("warnings", [])

    return {
        "status": result.get("status", "success"),
        "previews": previews,
        "conflicts": conflicts,
        "warnings": warnings,
        "has_conflicts": result.get("has_conflicts", len(conflicts) > 0),
        "has_warnings": result.get("has_warnings", len(warnings) > 0),
        "total_files": result.get("total_files", len(previews)),
        "changed_count": result.get("changed_count", sum(1 for p in previews if p.get("has_change"))),
    }


def rename_execute_response(result: dict) -> dict:
    """
    组装 /api/rename_execute 响应。
    确保前端依赖的字段都在顶层。
    """
    results = result.get("results", [])
    success_count = len([r for r in results if r.get("status") == "success"])
    failed_count = len([r for r in results if r.get("status") in ("failed", "error")])

    return {
        "status": result.get("status", "success"),
        "results": results,
        "executed": result.get("executed", success_count),
        "success_count": success_count,
        "failed_count": failed_count,
        "message": f"重命名完成：成功 {success_count} 个，失败 {failed_count} 个",
        "has_errors": result.get("has_errors", failed_count > 0),
        "errors": result.get("errors", []),
        "snapshot_path": result.get("snapshot_path"),
        "history_id": result.get("history_id"),
    }
