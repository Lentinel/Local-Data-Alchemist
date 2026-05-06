# API Contract

Base URL: `http://127.0.0.1:8002`
All endpoints are available under both `/` and `/api/` prefixes (e.g. `/lock_folder` and `/api/lock_folder`).

---

## 1. POST /api/lock_folder

Lock a target directory and scan its files.

**Request**
```json
{ "target_path": "C:\\Users\\example\\Documents" }
```

**Response**
```json
{
  "status": "success",
  "target_path": "C:\\Users\\example\\Documents",
  "files": [
    {
      "name": "report.pdf",
      "path": "report.pdf",
      "extension": ".pdf",
      "category": "documents",
      "size": 102400
    }
  ],
  "analysis": {
    "total_files": 1,
    "total_size": 102400,
    "categories": [
      { "key": "documents", "count": 1, "size": 102400 }
    ]
  }
}
```

---

## 2. POST /api/generate_plan

Generate an AI-powered file organization plan for a locked directory.

**Request**
```json
{ "target_path": "C:\\Users\\example\\Documents" }
```

**Response**
```json
{
  "status": "success",
  "mode": "real-llm",
  "llm_error": null,
  "target_path": "C:\\Users\\example\\Documents",
  "analysis": { "...same as lock_folder..." },
  "files": [ "..." ],
  "file_inventory": [ "..." ],
  "plan": [
    {
      "file": "report.pdf",
      "action": "rename_and_move",
      "target_path": "documents/2024-report.pdf",
      "reason": "Financial report, renamed with year prefix",
      "extracted_info": {
        "type": "financial",
        "amount": 5000
      }
    }
  ],
  "reasoning_trace": [
    "已锁定本地目标目录：...",
    "本地扫描完成：共发现 N 个文件"
  ],
  "translation_stats": null
}
```

**Action types**: `rename_and_move` | `move` | `delete` | `keep`

---

## 3. POST /api/execute_plan

Execute a plan synchronously (blocks until complete). Returns 409 if an uncommitted snapshot exists.

**Request**
```json
{
  "target_path": "C:\\Users\\example\\Documents",
  "plan": [
    {
      "file": "report.pdf",
      "action": "move",
      "target_path": "documents/report.pdf",
      "reason": "",
      "extracted_info": null
    }
  ]
}
```

**Response**
```json
{
  "status": "success",
  "executed": 1,
  "results": [
    {
      "file": "report.pdf",
      "action": "move",
      "original_path": "report.pdf",
      "target_path": "documents/report.pdf",
      "new_path": "documents/report.pdf",
      "absolute_original_path": "C:\\...\\report.pdf",
      "absolute_new_path": "C:\\...\\documents\\report.pdf",
      "status": "success"
    }
  ],
  "snapshot": "snapshot.json",
  "snapshot_path": "C:\\...\\.alchemy\\snapshot.json",
  "history_id": "abc123"
}
```

---

## 4. POST /api/start_execute_task

Execute a plan asynchronously. Returns immediately with a task ID; poll `/api/task_status/{task_id}` for progress.

**Request**
```json
{
  "target_path": "C:\\Users\\example\\Documents",
  "plan": [ "..." ]
}
```

**Response**
```json
{
  "status": "started",
  "message": "任务已启动",
  "task_id": "task_abc123",
  "total_items": 5,
  "task": {
    "task_id": "task_abc123",
    "task_type": "execute_plan",
    "status": "running",
    "percentage": 0.0,
    "total": 5,
    "current": 0,
    "message": "任务已创建，等待执行",
    "current_file": "",
    "start_time": "2026-05-05T10:00:00",
    "end_time": null,
    "error": null,
    "result": null
  }
}
```

---

## 5. GET /api/task_status/{task_id}

Poll task progress.

**Response**
```json
{
  "task_id": "task_abc123",
  "task_type": "execute_plan",
  "status": "running",
  "percentage": 60.0,
  "total": 5,
  "current": 3,
  "message": "正在处理 3/5：report.pdf",
  "current_file": "report.pdf",
  "start_time": "2026-05-05T10:00:00",
  "end_time": null,
  "error": null,
  "result": null,
  "move_total": 3,
  "move_done": 2,
  "delete_total": 1,
  "delete_done": 0,
  "rename_total": 1,
  "rename_done": 1,
  "keep_total": 0,
  "keep_done": 0,
  "completed_items": [
    {
      "file": "old.txt",
      "action": "rename_and_move",
      "original_path": "old.txt",
      "new_path": "new.txt",
      "status": "success"
    }
  ],
  "eta_seconds": 2.5,
  "items_per_second": 1.2,
  "formatted_eta": "2秒"
}
```

**Status values**: `pending` | `running` | `completed` | `cancelled` | `failed`

When `status` is `completed`, the `result` field contains the same structure as the synchronous `execute_plan` response.

---

## 6. POST /api/cancel_task

Cancel a running task.

**Request**
```json
{ "task_id": "task_abc123" }
```

**Response**
```json
{
  "status": "success",
  "message": "任务已取消：task_abc123"
}
```

---

## 7. POST /api/preview_file

Preview file content (text snippet or binary info).

**Request**
```json
{
  "target_path": "C:\\Users\\example\\Documents",
  "file_path": "report.pdf"
}
```

**Response**
```json
{
  "status": "success",
  "preview": {
    "type": "text",
    "content": "First 512 bytes of file content..."
  }
}
```

---

## 8. POST /api/detect_duplicates

Detect duplicate files by size + hash.

**Request**
```json
{
  "target_path": "C:\\Users\\example\\Documents",
  "fast_mode": true
}
```

**Response**
```json
{
  "status": "success",
  "total_files_scanned": 42,
  "groups": [
    {
      "hash": "a1b2c3...",
      "size": 102400,
      "files": [
        { "name": "copy1.pdf", "path": "copy1.pdf", "extension": ".pdf", "category": "documents", "size": 102400 },
        { "name": "copy2.pdf", "path": "subdir/copy2.pdf", "extension": ".pdf", "category": "documents", "size": 102400 }
      ],
      "recommended_keep": 0
    }
  ],
  "duplicate_groups": [ "..." ],
  "total_duplicate_count": 1,
  "total_duplicate_size": 102400,
  "fast_mode": true
}
```

> `groups` and `duplicate_groups` contain the same data. Use `groups`.

---

## 9. POST /api/keep_duplicate

Keep one file from a duplicate group, delete the rest (moves to `.alchemy_trash`).

**Request**
```json
{
  "target_path": "C:\\Users\\example\\Documents",
  "keep_file": "copy1.pdf",
  "duplicate_files": ["subdir/copy2.pdf"]
}
```

**Response**
```json
{
  "status": "success",
  "kept_file": "copy1.pdf",
  "deleted_count": 1,
  "results": [
    {
      "file": "subdir/copy2.pdf",
      "action": "delete",
      "original_path": "subdir/copy2.pdf",
      "new_path": ".alchemy_trash/uuid/copy2.pdf",
      "absolute_original_path": "C:\\...\\subdir\\copy2.pdf",
      "absolute_new_path": "C:\\...\\.alchemy_trash\\uuid\\copy2.pdf",
      "status": "success"
    }
  ]
}
```

---

## 10. POST /api/rename_preview

Preview batch rename results before executing.

**Request**
```json
{
  "target_path": "C:\\Users\\example\\Documents",
  "selected_files": ["report.pdf", "data.csv"],
  "rules": [
    {
      "rule_type": "prefix",
      "prefix": "2024_",
      "suffix": "",
      "find_text": "",
      "replace_text": "",
      "regex_pattern": "",
      "regex_replacement": "",
      "start_number": 1,
      "number_padding": 3,
      "number_separator": "_",
      "number_position": "prefix"
    }
  ]
}
```

**Rule types**: `prefix` | `suffix` | `find_replace` | `regex` | `numbering` | `date_prefix` | `date_suffix`

**Response**
```json
{
  "status": "success",
  "previews": [
    {
      "original_path": "report.pdf",
      "original_name": "report.pdf",
      "new_name": "2024_report.pdf",
      "new_path": "2024_report.pdf",
      "has_change": true,
      "conflict": false,
      "validation_warning": null,
      "sanitized": false,
      "index": 0
    }
  ],
  "conflicts": [],
  "warnings": [],
  "has_conflicts": false,
  "has_warnings": false,
  "total_files": 2,
  "changed_count": 2
}
```

---

## 11. POST /api/rename_execute

Execute a rename plan (based on preview results).

**Request**
```json
{
  "target_path": "C:\\Users\\example\\Documents",
  "rename_plan": [
    {
      "original_path": "report.pdf",
      "original_name": "report.pdf",
      "new_name": "2024_report.pdf",
      "new_path": "2024_report.pdf",
      "has_change": true,
      "conflict": false
    }
  ]
}
```

**Response**
```json
{
  "status": "success",
  "results": [
    {
      "original_path": "report.pdf",
      "original_name": "report.pdf",
      "new_path": "2024_report.pdf",
      "new_name": "2024_report.pdf",
      "status": "success",
      "absolute_original_path": "C:\\...\\report.pdf",
      "absolute_new_path": "C:\\...\\2024_report.pdf"
    }
  ],
  "executed": 1,
  "success_count": 1,
  "failed_count": 0,
  "message": "重命名完成：成功 1 个，失败 0 个"
}
```

---

## 12. POST /api/multi_scan

Scan multiple directories in one call.

**Request**
```json
{
  "target_paths": [
    "C:\\Users\\example\\Documents",
    "C:\\Users\\example\\Downloads"
  ]
}
```

**Response**
```json
{
  "status": "success",
  "results": [
    {
      "status": "success",
      "index": 0,
      "target_path": "C:\\Users\\example\\Documents",
      "files": [ "..." ],
      "file_inventory": [ "..." ],
      "analysis": { "..." },
      "file_count": 10,
      "total_size": 512000
    }
  ],
  "success_count": 2,
  "failed_count": 0,
  "total_files": 25,
  "total_size": 1024000,
  "merged_files": [ "..." ],
  "merged_file_inventory": [ "..." ],
  "merged_analysis": {
    "mode": "multi-directory-scan",
    "target_paths": [ "..." ],
    "total_files": 25,
    "total_size": 1024000,
    "categories": [ "..." ],
    "directories_count": 2
  }
}
```

---

## 13. POST /api/multi_generate_plan

Generate organization plans for multiple directories.

**Request**
```json
{
  "target_paths": [
    "C:\\Users\\example\\Documents",
    "C:\\Users\\example\\Downloads"
  ]
}
```

**Response**
```json
{
  "status": "success",
  "results": [
    {
      "status": "success",
      "index": 0,
      "target_path": "C:\\Users\\example\\Documents",
      "plan": [ "..." ],
      "error": null,
      "file_count": 10,
      "action_count": 5,
      "translation_stats": null
    }
  ],
  "plan_results": [ "..." ],
  "success_count": 2,
  "llm_failed_count": 0,
  "total_files": 25,
  "total_actions": 12,
  "merged_plan": [ "..." ],
  "mode": "multi-directory-plan"
}
```

> `results` and `plan_results` contain the same data. Use `results`.

---

## 14. POST /api/undo_plan

Roll back the last executed plan using the snapshot.

**Request**
```json
{ "target_path": "C:\\Users\\example\\Documents" }
```

**Response**
```json
{
  "status": "success",
  "message": "已恢复到炼金前状态",
  "restored": 3,
  "results": [ "..." ],
  "history_id": "abc123"
}
```

---

## 15. POST /api/preview_plan

Dry-run a plan to check for conflicts and safety issues without executing.

**Request**
```json
{
  "target_path": "C:\\Users\\example\\Documents",
  "plan": [ "..." ]
}
```

**Response** (structure varies, includes safety analysis)
```json
{
  "safety_level": "safe",
  "total_actions": 5,
  "by_action": { "move": 3, "delete": 1, "keep": 1 },
  "conflicts": [],
  "warnings": [],
  "move_actions": [ "..." ],
  "delete_actions": [ "..." ],
  "keep_actions": [ "..." ]
}
```

---

## 16. GET /api/llm_health

Lightweight LLM configuration self-check. By default this endpoint only inspects configuration completeness and does not make a real LLM request. Pass `check_connection=true` to run a minimal connectivity test with the current `OPENAI_API_KEY`, `OPENAI_API_BASE`, and `OPENAI_MODEL`.

**Query params**
- `check_connection` (optional, boolean) - defaults to `false`

**Response**
```json
{
  "env_file_exists": true,
  "has_api_key": true,
  "api_key_preview": "sk-1...9abc",
  "has_api_base": true,
  "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "has_model": true,
  "model": "qwen-max",
  "timeout_seconds": 180,
  "status": "ok",
  "suggestions": [],
  "has_placeholder_values": false,
  "placeholder_fields": [],
  "connection_status": null,
  "connection_error": null,
  "checked_at": null
}
```

**Response when placeholder values are detected**
```json
{
  "env_file_exists": true,
  "has_api_key": false,
  "api_key_preview": "your...here",
  "has_api_base": false,
  "api_base": "https://your-openai-compatible-base-url/v1",
  "has_model": false,
  "model": "your_model_name_here",
  "timeout_seconds": 180,
  "status": "warning",
  "suggestions": [
    "OPENAI_API_KEY 仍是示例占位值，请替换为真实值",
    "OPENAI_API_BASE 仍是示例占位值，请替换为真实值",
    "OPENAI_MODEL 仍是示例占位值，请替换为真实值"
  ],
  "has_placeholder_values": true,
  "placeholder_fields": ["OPENAI_API_KEY", "OPENAI_API_BASE", "OPENAI_MODEL"],
  "connection_status": null,
  "connection_error": null,
  "checked_at": null
}
```

**Response when `check_connection=true`**
```json
{
  "env_file_exists": true,
  "has_api_key": true,
  "api_key_preview": "sk-1...9abc",
  "has_api_base": true,
  "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "has_model": true,
  "model": "qwen-max",
  "timeout_seconds": 180,
  "status": "ok",
  "suggestions": [],
  "has_placeholder_values": false,
  "placeholder_fields": [],
  "connection_status": "ok",
  "connection_error": null,
  "checked_at": "2026-05-06T12:34:56+00:00"
}
```

- `api_key_preview` is always masked and never returns the full key.
- `has_api_key` / `has_api_base` / `has_model` mean effectively configured. Placeholder values are treated as invalid.
- `has_placeholder_values` indicates whether any known example placeholder values were detected.
- `placeholder_fields` lists which fields are still using example placeholder values.
- `connection_error` is sanitized and never returns the raw upstream error or any secret value.
  - `placeholder_config_detected`: connection test was requested but example placeholder values were still present
- `connection_status` values:
  - `null`: no connection test was requested
  - `ok`: minimal connectivity test succeeded
  - `error`: connectivity test failed
  - `skipped`: connectivity test was requested but required config was missing or placeholder-valued
- `status` values:
  - `ok`: required configuration is complete and effective
  - `warning`: one or more required fields are missing, placeholder-valued, or timeout parsing fell back to the default

---

## Error Response Format

All error responses follow FastAPI's standard format:

```json
{
  "detail": "错误描述信息"
}
```

Common HTTP status codes:
- `400` - Bad request (missing fields, invalid data)
- `404` - Resource not found (task, file, template)
- `409` - Conflict (snapshot exists, target path already exists)
- `500` - Internal server error

---

## Contract Verification

Run automated contract verification (no real server needed):

```bash
python tools/verify_api_contract.py
```

### What's Verified

1. **Normal Response Contracts** - Frontend-dependent fields exist with correct types for:
   - `/api/lock_folder`, `/api/generate_plan`, `/api/preview_file`
   - `/api/detect_duplicates`, `/api/rename_preview`
   - `/api/multi_scan`, `/api/multi_generate_plan`

2. **Error Response Contracts** - 4xx/5xx responses include `detail` field:
   - Invalid `target_path` (404)
   - Invalid `file_path` (404)
   - Empty `target_paths` (422)
   - Non-existent `task_id` (404)

3. **Async Task Contract** - Start task with keep-only plan, poll status:
   - `/api/start_execute_task` returns `task_id` and `total_items`
   - `/api/task_status/{task_id}` returns all 24 progress fields

4. **Route Coverage** - All endpoints in this document exist in app routes

### Quick Smoke Test

```bash
python tools/smoke_api_contract.py
```
