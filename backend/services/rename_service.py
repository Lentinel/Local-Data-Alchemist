import re
import shutil
import uuid
from pathlib import Path
from datetime import date

from fastapi import HTTPException

from models.schemas import RenameRule, RenamePreviewRequest, RenameExecuteRequest
from utils.security import resolve_inside_target, to_target_relative
from utils.storage import get_snapshot_path, write_snapshot, write_history
from utils.helpers import validate_filename, sanitize_filename


def apply_rename_rules(
    original_name: str,
    rules: list[RenameRule],
    index: int = 0,
    total_count: int = 1,
    sanitize: bool = True
) -> tuple[str, str | None]:
    name_stem = Path(original_name).stem
    extension = Path(original_name).suffix
    current_name = name_stem
    
    for rule in rules:
        rule_type = rule.rule_type
        
        if rule_type == "prefix":
            prefix = rule.prefix or ""
            current_name = prefix + current_name
        
        elif rule_type == "suffix":
            suffix = rule.suffix or ""
            current_name = current_name + suffix
        
        elif rule_type == "find_replace":
            find_text = rule.find_text or ""
            replace_text = rule.replace_text or ""
            if find_text:
                current_name = current_name.replace(find_text, replace_text)
        
        elif rule_type == "regex":
            pattern = rule.regex_pattern or ""
            replacement = rule.regex_replacement or ""
            if pattern:
                try:
                    current_name = re.sub(pattern, replacement, current_name)
                except re.error:
                    pass
        
        elif rule_type == "numbering":
            start_num = rule.start_number or 1
            padding = rule.number_padding or 3
            separator = rule.number_separator or "_"
            position = rule.number_position or "prefix"
            
            num_str = str(start_num + index).zfill(padding)
            
            if position == "prefix":
                current_name = num_str + separator + current_name
            elif position == "suffix":
                current_name = current_name + separator + num_str
            elif position == "replace":
                current_name = num_str
        
        elif rule_type == "date_prefix":
            today = date.today().isoformat()
            separator = rule.number_separator or "_"
            current_name = today + separator + current_name
        
        elif rule_type == "date_suffix":
            today = date.today().isoformat()
            separator = rule.number_separator or "_"
            current_name = current_name + separator + today
    
    final_name = current_name + extension
    
    is_valid, error_reason = validate_filename(final_name)
    
    if not is_valid and sanitize:
        sanitized_name = sanitize_filename(final_name, fallback_prefix=name_stem or "file")
        if sanitized_name != final_name:
            return sanitized_name, f"自动修正: {error_reason}"
    
    if not is_valid:
        return final_name, error_reason
    
    return final_name, None


def generate_rename_preview(
    target_dir: Path,
    selected_files: list[str],
    rules: list[RenameRule]
) -> dict:
    results = []
    conflicts = []
    warnings = []
    new_names = set()
    file_info_map = {}
    
    for file_path in selected_files:
        full_path = resolve_inside_target(target_dir, file_path)
        if not full_path.exists():
            continue
        
        original_name = full_path.name
        file_info_map[file_path] = {
            "path": file_path,
            "original_name": original_name,
            "full_path": full_path
        }
    
    sorted_files = sorted(file_info_map.items(), key=lambda x: x[1]["original_name"])
    
    for index, (file_path, info) in enumerate(sorted_files):
        original_name = info["original_name"]
        new_name, validation_warning = apply_rename_rules(
            original_name,
            rules,
            index,
            len(sorted_files)
        )
        
        parent_dir = Path(file_path).parent
        if parent_dir == Path("."):
            new_path = new_name
        else:
            new_path = str(parent_dir / new_name)
        
        conflict = False
        if new_name != original_name:
            if new_name in new_names:
                conflict = True
                conflicts.append({
                    "file": file_path,
                    "original_name": original_name,
                    "new_name": new_name,
                    "reason": "与其他重命名文件冲突"
                })
            
            new_full_path = resolve_inside_target(target_dir, new_path)
            if new_full_path.exists() and new_path != file_path:
                conflict = True
                conflicts.append({
                    "file": file_path,
                    "original_name": original_name,
                    "new_name": new_name,
                    "reason": "目标文件已存在"
                })
            
            new_names.add(new_name)
        
        if validation_warning:
            warnings.append({
                "file": file_path,
                "original_name": original_name,
                "new_name": new_name,
                "warning": validation_warning
            })
        
        results.append({
            "original_path": file_path,
            "original_name": original_name,
            "new_name": new_name,
            "new_path": new_path,
            "has_change": new_name != original_name,
            "conflict": conflict,
            "validation_warning": validation_warning,
            "sanitized": validation_warning and validation_warning.startswith("自动修正"),
            "index": index
        })
    
    return {
        "status": "success",
        "previews": results,
        "conflicts": conflicts,
        "warnings": warnings,
        "has_conflicts": len(conflicts) > 0,
        "has_warnings": len(warnings) > 0,
        "total_files": len(results),
        "changed_count": sum(1 for r in results if r["has_change"])
    }


def execute_rename_plan(
    target_dir: Path,
    rename_plan: list[dict]
) -> dict:
    snapshot_path = get_snapshot_path(target_dir)
    if snapshot_path.exists():
        raise HTTPException(
            status_code=409,
            detail="检测到未回滚的 snapshot，请先执行 Undo 后再运行重命名操作。"
        )
    
    results = []
    snapshot_operations = []
    errors = []
    
    valid_plans = [p for p in rename_plan if p.get("has_change") and not p.get("conflict")]
    
    for item in valid_plans:
        original_path = item.get("original_path")
        new_path = item.get("new_path")
        
        if not original_path or not new_path:
            results.append({
                "original_path": original_path,
                "new_path": new_path,
                "status": "skipped",
                "message": "缺少必要的路径参数"
            })
            continue
        
        try:
            original_name = Path(original_path).name
            new_name = Path(new_path).name
            
            if new_name != original_name:
                is_valid, error_reason = validate_filename(new_name)
                if not is_valid:
                    sanitized_name = sanitize_filename(new_name, fallback_prefix=Path(original_name).stem or "file")
                    if sanitized_name != new_name:
                        parent_dir = Path(new_path).parent
                        if parent_dir == Path("."):
                            new_path = sanitized_name
                        else:
                            new_path = str(parent_dir / sanitized_name)
                        
                        errors.append({
                            "original_path": original_path,
                            "original_name": original_name,
                            "original_new_name": new_name,
                            "corrected_name": sanitized_name,
                            "reason": error_reason
                        })
            
            source_path = resolve_inside_target(target_dir, original_path)
            dest_path = resolve_inside_target(target_dir, new_path)
            
            if not source_path.exists():
                results.append({
                    "original_path": original_path,
                    "new_path": new_path,
                    "status": "skipped",
                    "message": "源文件不存在"
                })
                continue
            
            if dest_path.exists() and new_path != original_path:
                results.append({
                    "original_path": original_path,
                    "new_path": new_path,
                    "status": "skipped",
                    "message": "目标路径已存在"
                })
                continue
            
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                shutil.move(str(source_path), str(dest_path))
            except OSError as e:
                error_msg = str(e)
                if "already exists" in error_msg.lower() or "exists" in error_msg.lower():
                    results.append({
                        "original_path": original_path,
                        "new_path": new_path,
                        "status": "skipped",
                        "message": f"目标文件已存在: {error_msg}"
                    })
                elif "permission" in error_msg.lower():
                    results.append({
                        "original_path": original_path,
                        "new_path": new_path,
                        "status": "error",
                        "message": f"权限不足: {error_msg}"
                    })
                else:
                    results.append({
                        "original_path": original_path,
                        "new_path": new_path,
                        "status": "error",
                        "message": f"重命名失败: {error_msg}"
                    })
                continue
            
            snapshot_operations.append({
                "action": "rename_and_move",
                "original_path": original_path,
                "new_path": new_path,
            })
            
            results.append({
                "original_path": original_path,
                "original_name": Path(original_path).name,
                "new_path": new_path,
                "new_name": Path(new_path).name,
                "status": "success",
                "absolute_original_path": str(source_path),
                "absolute_new_path": str(dest_path),
            })
        except Exception as e:
            results.append({
                "original_path": original_path,
                "new_path": new_path,
                "status": "error",
                "message": f"处理失败: {str(e)}"
            })
            errors.append({
                "original_path": original_path,
                "error": str(e)
            })
    
    if snapshot_operations:
        write_snapshot(target_dir, snapshot_operations)
        
        history_id = uuid.uuid4().hex
        write_history(
            target_dir=target_dir,
            history_id=history_id,
            operation_type="rename",
            target_path=str(target_dir),
            plan=rename_plan,
            results=results,
            snapshot_path=str(snapshot_path),
        )
    
    return {
        "status": "success",
        "executed": len([r for r in results if r["status"] == "success"]),
        "total": len(results),
        "results": results,
        "errors": errors,
        "has_errors": len(errors) > 0,
        "snapshot_path": str(snapshot_path),
        "history_id": history_id if snapshot_operations else None,
    }
