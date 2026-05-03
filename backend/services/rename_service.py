import re
import os
from pathlib import Path
from datetime import date
from collections import defaultdict


def apply_rename_rules(
    file_name: str,
    extension: str,
    rules: list,
    index: int = 0,
    total_count: int = 0,
) -> str:
    base_name = file_name
    if extension and base_name.endswith(extension):
        base_name = base_name[:-len(extension)]
    
    for rule in rules:
        rule_type = rule.get("rule_type", "")
        params = rule.get("params", {})
        
        if rule_type == "prefix":
            prefix = params.get("prefix", "")
            if prefix:
                base_name = prefix + base_name
        
        elif rule_type == "suffix":
            suffix = params.get("suffix", "")
            if suffix:
                base_name = base_name + suffix
        
        elif rule_type == "find_replace":
            find_text = params.get("find_text", "")
            replace_text = params.get("replace_text", "")
            if find_text:
                base_name = base_name.replace(find_text, replace_text)
        
        elif rule_type == "regex":
            pattern = params.get("regex_pattern", "")
            replacement = params.get("regex_replacement", "")
            if pattern:
                try:
                    base_name = re.sub(pattern, replacement, base_name)
                except re.error:
                    pass
        
        elif rule_type == "numbering":
            start_number = params.get("start_number", 1)
            padding = params.get("number_padding", 3)
            separator = params.get("number_separator", "_")
            position = params.get("number_position", "prefix")
            
            number_str = str(start_number + index).zfill(padding)
            
            if position == "prefix":
                base_name = number_str + separator + base_name
            elif position == "suffix":
                base_name = base_name + separator + number_str
            elif position == "replace":
                base_name = number_str
        
        elif rule_type == "date_prefix":
            today = date.today().isoformat()
            base_name = today + "_" + base_name
        
        elif rule_type == "date_suffix":
            today = date.today().isoformat()
            base_name = base_name + "_" + today
    
    return base_name + extension


def generate_rename_preview(
    target_dir: Path,
    files: list,
    rules: list,
) -> dict:
    previews = []
    name_map = {}
    conflicts = []
    
    for index, file_info in enumerate(files):
        original_name = file_info.get("name", "")
        extension = file_info.get("extension", "")
        file_path = file_info.get("path", "")
        
        new_name = apply_rename_rules(
            original_name, extension, rules, index, len(files)
        )
        
        original_full_path = str(target_dir / file_path)
        new_full_path = str(target_dir / (Path(file_path).parent / new_name)) if "/" in file_path else str(target_dir / new_name)
        
        preview_item = {
            "original_name": original_name,
            "original_path": file_path,
            "new_name": new_name,
            "new_path": str(Path(file_path).parent / new_name) if "/" in file_path else new_name,
            "has_changes": original_name != new_name,
        }
        previews.append(preview_item)
        
        if original_name != new_name:
            if new_full_path in name_map:
                conflicts.append({
                    "type": "duplicate",
                    "new_name": new_name,
                    "files": [name_map[new_full_path], file_path],
                })
            else:
                name_map[new_full_path] = file_path
    
    for preview in previews:
        if preview["has_changes"]:
            new_path = preview["new_path"]
            full_path = target_dir / new_path
            if full_path.exists() and str(full_path) != (target_dir / preview["original_path"]):
                conflicts.append({
                    "type": "exists",
                    "new_name": preview["new_name"],
                    "new_path": new_path,
                })
    
    conflict_names = set()
    unique_conflicts = []
    for c in conflicts:
        name_key = c.get("new_name", "") or c.get("new_path", "")
        if name_key and name_key not in conflict_names:
            conflict_names.add(name_key)
            unique_conflicts.append(c)
    
    return {
        "previews": previews,
        "conflicts": unique_conflicts,
        "has_conflicts": len(unique_conflicts) > 0,
        "total_changes": sum(1 for p in previews if p["has_changes"]),
    }
