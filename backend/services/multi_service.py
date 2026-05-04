import os
from pathlib import Path

from fastapi import HTTPException

from models.schemas import FileInfo
from utils.security import get_target_dir
from services.file_service import scan_target_files, build_analysis, build_file_snippets
from services.llm_service import (
    call_llm_generate_plan,
    generate_local_fallback_plan,
    translate_texts_to_zh,
    should_translate_to_zh,
    build_llm_prompt,
)


def scan_and_analyze_single_path(
    target_path: str,
    index: int = 0
) -> dict:
    try:
        target_dir = get_target_dir(target_path)
        files_info = scan_target_files(target_dir)
        analysis_result = build_analysis(files_info)
        file_snippets = build_file_snippets(target_dir, [FileInfo(**f) for f in files_info])
        
        return {
            "status": "success",
            "index": index,
            "target_path": str(target_dir),
            "files": file_snippets,
            "file_inventory": files_info,
            "analysis": analysis_result,
            "file_count": len(files_info),
            "total_size": analysis_result.get("total_size", 0) if analysis_result else 0,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "index": index,
            "target_path": target_path,
            "error": str(exc),
            "files": [],
            "file_inventory": [],
            "analysis": None,
            "file_count": 0,
            "total_size": 0,
        }


def normalize_and_deduplicate_paths(raw_paths: list[str]) -> tuple[list[str], list[dict]]:
    processed_paths = []
    seen_paths = set()
    ignored_paths_info = []
    
    for path in raw_paths:
        if not path or not isinstance(path, str):
            ignored_paths_info.append({
                "path": path,
                "reason": "空路径或非字符串类型"
            })
            continue
        
        path_stripped = path.strip()
        if not path_stripped:
            ignored_paths_info.append({
                "path": path,
                "reason": "仅包含空白字符"
            })
            continue
        
        try:
            normalized_path = str(Path(path_stripped).resolve())
        except Exception as path_exc:
            ignored_paths_info.append({
                "path": path_stripped,
                "reason": f"路径解析失败: {str(path_exc)}"
            })
            continue
        
        if normalized_path in seen_paths:
            ignored_paths_info.append({
                "path": path_stripped,
                "normalized_path": normalized_path,
                "reason": "重复路径"
            })
            continue
        
        seen_paths.add(normalized_path)
        processed_paths.append(normalized_path)
    
    return processed_paths, ignored_paths_info


def multi_scan(raw_paths: list[str]) -> dict:
    processed_paths, ignored_paths_info = normalize_and_deduplicate_paths(raw_paths)
    
    if len(processed_paths) == 0:
        if len(ignored_paths_info) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"所有路径都被过滤。原因: {ignored_paths_info[0].get('reason', '未知')}"
            )
        else:
            raise HTTPException(status_code=400, detail="至少需要指定一个有效的目标目录")
    
    results = []
    for i, target_path in enumerate(processed_paths):
        result = scan_and_analyze_single_path(target_path, i)
        results.append(result)
    
    success_count = sum(1 for r in results if r["status"] == "success")
    total_files = sum(r["file_count"] for r in results)
    total_size = sum(r["total_size"] for r in results)
    
    all_files = []
    all_file_inventory = []
    all_categories = {
        "images": {"count": 0, "size": 0},
        "documents": {"count": 0, "size": 0},
        "archives": {"count": 0, "size": 0},
        "code": {"count": 0, "size": 0},
        "logs": {"count": 0, "size": 0},
        "unknown": {"count": 0, "size": 0},
    }
    
    for result in results:
        if result["status"] == "success":
            all_files.extend(result.get("files", []))
            all_file_inventory.extend([
                {**f, "source_path": result["target_path"]}
                for f in result.get("file_inventory", [])
            ])
            
            analysis = result.get("analysis")
            if analysis and isinstance(analysis, dict):
                categories = analysis.get("categories")
                if categories and isinstance(categories, list):
                    for cat in categories:
                        if isinstance(cat, dict):
                            key = cat.get("key", "unknown")
                            if key in all_categories:
                                count = cat.get("count", 0)
                                size = cat.get("size", 0)
                                if isinstance(count, (int, float)):
                                    all_categories[key]["count"] += count
                                if isinstance(size, (int, float)):
                                    all_categories[key]["size"] += size
    
    merged_analysis = {
        "mode": "multi-directory-scan",
        "target_paths": [r["target_path"] for r in results if r.get("status") == "success"],
        "total_files": total_files,
        "total_size": total_size,
        "categories": [
            {"key": k, "count": v["count"], "size": v["size"]}
            for k, v in all_categories.items()
            if v["count"] > 0
        ],
        "directories_count": success_count,
        "raw_input_paths": raw_paths,
        "processed_paths_count": len(processed_paths),
        "ignored_paths_count": len(ignored_paths_info),
        "ignored_paths": ignored_paths_info if len(ignored_paths_info) <= 10 else ignored_paths_info[:10] + [{"note": f"还有 {len(ignored_paths_info) - 10} 个被忽略的路径未显示"}],
    }
    
    return {
        "status": "success",
        "results": results,
        "success_count": success_count,
        "failed_count": len(results) - success_count,
        "total_files": total_files,
        "total_size": total_size,
        "merged_files": all_files,
        "merged_file_inventory": all_file_inventory,
        "merged_analysis": merged_analysis,
    }


def generate_plan_for_single_path_v2(
    target_path: str,
    files_info: list[dict],
    index: int = 0
) -> dict:
    try:
        target_dir = get_target_dir(target_path)
        
        files = [FileInfo(**f) for f in files_info]
        file_snippets = build_file_snippets(target_dir, files)
        llm_error = None
        mode = "real-llm"
        
        try:
            plan = call_llm_generate_plan(file_snippets)
        except HTTPException as exc:
            llm_error = exc.detail
            if (os.getenv("ALLOW_MOCK_LLM_FALLBACK", "true") or "").strip().lower() not in {"1", "true", "yes"}:
                return {
                    "status": "failed",
                    "index": index,
                    "target_path": str(target_dir),
                    "plan": [],
                    "error": str(llm_error),
                    "file_count": len(files_info),
                    "action_count": 0,
                }
            
            mode = "local-fallback-after-llm-error"
            plan = generate_local_fallback_plan(files, str(exc.detail))
        
        translation_stats = None
        if (os.getenv("FORCE_ZH_TRANSLATION", "true") or "").strip().lower() in {"1", "true", "yes"}:
            timeout_seconds_raw = (os.getenv("OPENAI_TIMEOUT_SECONDS") or "").strip()
            timeout_seconds = 180
            if timeout_seconds_raw:
                try:
                    timeout_seconds = int(float(timeout_seconds_raw))
                except ValueError:
                    timeout_seconds = 180
            model = (os.getenv("OPENAI_MODEL") or "").strip()
            translate_model = (os.getenv("OPENAI_TRANSLATE_MODEL") or model).strip() or model
            
            replacements: dict[str, str] = {}
            texts_to_translate: list[str] = []
            
            def enqueue(text: str | None) -> None:
                if not should_translate_to_zh(text):
                    return
                value = (text or "").strip()
                if not value:
                    return
                if value in replacements:
                    return
                if value in texts_to_translate:
                    return
                texts_to_translate.append(value)
            
            for item in plan:
                enqueue(item.reason)
                info = item.extracted_info if isinstance(item.extracted_info, dict) else None
                if not info:
                    continue
                enqueue(info.get("title"))
                enqueue(info.get("summary"))
                enqueue(info.get("root_cause"))
                enqueue(info.get("recommended_action"))
                enqueue(info.get("merchant"))
            
            translated = translate_texts_to_zh(texts_to_translate, timeout_seconds=timeout_seconds, model=translate_model)
            replaced_count = 0
            for original, translated_text in zip(texts_to_translate, translated, strict=False):
                replacements[original] = translated_text
                if translated_text != original:
                    replaced_count += 1
            
            for item in plan:
                if isinstance(item.reason, str):
                    stripped = item.reason.strip()
                    if stripped in replacements:
                        item.reason = replacements[stripped]
                info = item.extracted_info if isinstance(item.extracted_info, dict) else None
                if not info:
                    continue
                for key in ("title", "summary", "root_cause", "recommended_action", "merchant"):
                    value = info.get(key)
                    if isinstance(value, str):
                        stripped = value.strip()
                        if stripped in replacements:
                            info[key] = replacements[stripped]
            
            translation_stats = {
                "requested": len(texts_to_translate),
                "replaced": replaced_count,
                "model": translate_model,
            }
        
        plan_status = "success" if mode == "real-llm" else "llm_failed"
        plan_error = llm_error if mode != "real-llm" else None
        
        return {
            "status": plan_status,
            "index": index,
            "target_path": str(target_dir),
            "plan": [item.dict() for item in plan],
            "error": plan_error,
            "file_count": len(files_info),
            "action_count": len(plan),
            "translation_stats": translation_stats,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "index": index,
            "target_path": target_path,
            "plan": [],
            "error": str(exc),
            "file_count": 0,
            "action_count": 0,
        }


def multi_generate_plan(raw_paths: list[str]) -> dict:
    processed_paths, ignored_paths_info = normalize_and_deduplicate_paths(raw_paths)
    
    if len(processed_paths) == 0:
        if len(ignored_paths_info) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"所有路径都被过滤。原因: {ignored_paths_info[0].get('reason', '未知')}"
            )
        else:
            raise HTTPException(status_code=400, detail="至少需要指定一个有效的目标目录")
    
    scan_results = []
    for i, target_path in enumerate(processed_paths):
        result = scan_and_analyze_single_path(target_path, i)
        scan_results.append(result)
    
    plan_results = []
    for i, scan_result in enumerate(scan_results):
        if scan_result.get("status") == "success":
            plan_result = generate_plan_for_single_path_v2(
                scan_result.get("target_path"),
                scan_result.get("file_inventory", []),
                i
            )
            plan_results.append(plan_result)
        else:
            plan_results.append({
                "status": "skipped",
                "index": i,
                "target_path": scan_result.get("target_path", "unknown"),
                "plan": [],
                "error": scan_result.get("error", "扫描失败"),
                "file_count": 0,
                "action_count": 0,
            })
    
    success_count = sum(1 for r in plan_results if r.get("status") == "success")
    llm_failed_count = sum(1 for r in plan_results if r.get("status") == "llm_failed")
    total_actions = sum(r.get("action_count", 0) for r in plan_results)
    total_files = sum(r.get("file_count", 0) for r in plan_results)
    
    all_plans = []
    for result in plan_results:
        status = result.get("status")
        plan = result.get("plan", [])
        if status in ["success", "llm_failed"] and plan:
            for action in plan:
                if isinstance(action, dict):
                    all_plans.append({
                        **action,
                        "source_path": result.get("target_path"),
                    })
    
    return {
        "status": "success",
        "plan_results": plan_results,
        "success_count": success_count,
        "llm_failed_count": llm_failed_count,
        "total_files": total_files,
        "total_actions": total_actions,
        "merged_plan": all_plans,
        "mode": "multi-directory-plan",
        "raw_input_paths": raw_paths,
        "processed_paths_count": len(processed_paths),
        "ignored_paths_count": len(ignored_paths_info),
        "ignored_paths": ignored_paths_info if len(ignored_paths_info) <= 10 else ignored_paths_info[:10] + [{"note": f"还有 {len(ignored_paths_info) - 10} 个被忽略的路径未显示"}],
    }
