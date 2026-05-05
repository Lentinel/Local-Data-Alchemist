#!/usr/bin/env python3
"""
前后端契约冒烟验证：断言前端依赖的关键字段存在且类型合理。
使用 FastAPI TestClient，不启动真实服务器。
只读验证，不执行移动/删除/重命名。

验证内容：
1. 正常响应契约（前端依赖字段存在且类型合理）
2. 错误响应契约（4xx/5xx 时包含 detail 字段）
3. 异步任务契约（start_execute_task + task_status 轮询）
4. 路由存在性（API_CONTRACT.md 中的路径都在 app 路由中）
"""
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
SAMPLE_DIR = str(ROOT / "sample_messy_folder")

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# 前端依赖的字段及期望类型
# 格式: (field_path, expected_type, required)
CONTRACTS = {
    "/api/lock_folder": [
        ("status", str, True),
        ("target_path", str, True),
        ("files", list, True),
        ("files[].name", str, True),
        ("files[].path", str, True),
        ("files[].extension", str, True),
        ("files[].category", str, True),
        ("files[].size", int, True),
        ("analysis", dict, True),
    ],
    "/api/generate_plan": [
        ("status", str, True),
        ("target_path", str, True),
        ("files", list, True),
        ("file_inventory", list, True),
        ("analysis", dict, True),
        ("plan", list, True),
        ("plan[].file", str, True),
        ("plan[].action", str, True),
        ("plan[].target_path", (str, type(None)), False),
        ("plan[].reason", str, True),
        ("reasoning_trace", list, True),
        ("llm_error", (str, type(None)), False),
    ],
    "/api/preview_file": [
        ("status", str, True),
        ("preview", dict, True),
        ("preview.type", str, True),
        ("preview.content", str, True),
    ],
    "/api/detect_duplicates": [
        ("status", str, True),
        ("total_files_scanned", int, True),
        ("groups", list, True),
        ("groups[].hash", str, True),
        ("groups[].size", int, True),
        ("groups[].files", list, True),
        ("duplicate_groups", list, True),
        ("total_duplicate_count", int, True),
        ("total_duplicate_size", int, True),
        ("fast_mode", bool, True),
    ],
    "/api/rename_preview": [
        ("status", str, True),
        ("previews", list, True),
        ("previews[].original_path", str, True),
        ("previews[].original_name", str, True),
        ("previews[].new_name", str, True),
        ("previews[].new_path", str, True),
        ("previews[].has_change", bool, True),
        ("previews[].conflict", bool, True),
        ("conflicts", list, True),
        ("warnings", list, True),
        ("has_conflicts", bool, True),
        ("has_warnings", bool, True),
        ("total_files", int, True),
        ("changed_count", int, True),
    ],
    "/api/rename_execute": [
        ("status", str, True),
        ("results", list, True),
        ("results[].original_path", str, True),
        ("results[].new_path", str, True),
        ("results[].status", str, True),
        ("executed", int, True),
        ("success_count", int, True),
        ("failed_count", int, True),
        ("message", str, True),
    ],
    "/api/multi_scan": [
        ("status", str, True),
        ("results", list, True),
        ("results[].status", str, True),
        ("results[].target_path", str, True),
        ("results[].files", list, True),
        ("results[].analysis", dict, True),
        ("success_count", int, True),
        ("failed_count", int, True),
        ("total_files", int, True),
        ("total_size", int, True),
        ("merged_files", list, True),
        ("merged_analysis", dict, True),
    ],
    "/api/multi_generate_plan": [
        ("status", str, True),
        ("results", list, True),
        ("results[].status", str, True),
        ("results[].target_path", str, True),
        ("results[].plan", list, True),
        ("plan_results", list, True),
        ("success_count", int, True),
        ("llm_failed_count", int, True),
        ("total_files", int, True),
        ("total_actions", int, True),
        ("merged_plan", list, True),
        ("mode", str, True),
    ],
}


def get_nested(data, path):
    """获取嵌套字段，支持 items[].field 语法"""
    parts = path.split(".")
    current = data
    for part in parts:
        if part.endswith("[]"):
            key = part[:-2]
            if not isinstance(current, dict) or key not in current:
                return None, False
            current = current[key]
            if not isinstance(current, list) or len(current) == 0:
                return None, True
            current = current[0]
        else:
            if not isinstance(current, dict) or part not in current:
                return None, False
            current = current[part]
    return current, True


def check_type(value, expected_type):
    if isinstance(expected_type, tuple):
        return isinstance(value, expected_type)
    return isinstance(value, expected_type)


def verify_endpoint(endpoint, request_data, contracts):
    """验证单个端点"""
    print(f"\n{YELLOW}{endpoint}{RESET}")

    # rename_execute 需要先清理 snapshot
    if endpoint == "/api/rename_execute":
        snapshot = Path(SAMPLE_DIR) / "snapshot.json"
        if snapshot.exists():
            snapshot.unlink()

    if endpoint == "/api/lock_folder":
        resp = client.post(endpoint, json=request_data)
    elif endpoint.startswith("/api/task_status/"):
        resp = client.get(endpoint)
    else:
        resp = client.post(endpoint, json=request_data)

    if resp.status_code != 200:
        print(f"  {RED}FAIL{RESET} HTTP {resp.status_code}")
        return False

    data = resp.json()
    failures = []

    for field_path, expected_type, required in contracts:
        value, found = get_nested(data, field_path)

        if not found:
            if required:
                failures.append(f"missing: {field_path}")
            continue

        if value is not None and not check_type(value, expected_type):
            actual = type(value).__name__
            failures.append(f"type mismatch: {field_path} expected {expected_type}, got {actual}")

    if failures:
        print(f"  {RED}FAIL{RESET}")
        for f in failures:
            print(f"    - {f}")
        return False
    else:
        print(f"  {GREEN}PASS{RESET} ({len(contracts)} fields verified)")
        return True


def get_request_data(endpoint):
    """获取各端点的测试请求数据"""
    if endpoint == "/api/lock_folder":
        return {"target_path": SAMPLE_DIR}
    elif endpoint == "/api/generate_plan":
        return {"target_path": SAMPLE_DIR}
    elif endpoint == "/api/preview_file":
        return {"target_path": SAMPLE_DIR, "file_path": "documents/meeting_notes.md"}
    elif endpoint == "/api/detect_duplicates":
        return {"target_path": SAMPLE_DIR, "fast_mode": True}
    elif endpoint == "/api/rename_preview":
        return {
            "target_path": SAMPLE_DIR,
            "selected_files": ["documents/meeting_notes.md", "receipt_april.pdf"],
            "rules": [{
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
            }]
        }
    elif endpoint == "/api/rename_execute":
        # 使用一个不会实际执行的空计划（has_change=false）
        return {
            "target_path": SAMPLE_DIR,
            "rename_plan": [{
                "original_path": "documents/meeting_notes.md",
                "original_name": "meeting_notes.md",
                "new_name": "meeting_notes.md",
                "new_path": "documents/meeting_notes.md",
                "has_change": False,
                "conflict": False
            }]
        }
    elif endpoint == "/api/multi_scan":
        return {"target_paths": [SAMPLE_DIR]}
    elif endpoint == "/api/multi_generate_plan":
        return {"target_paths": [SAMPLE_DIR]}
    return {}


# ──────────────────────────────────────────────────────────────
# 第二类：错误响应契约
# ──────────────────────────────────────────────────────────────
ERROR_CASES = [
    {
        "name": "lock_folder: 不存在的 target_path",
        "method": "POST",
        "endpoint": "/api/lock_folder",
        "request": {"target_path": "X:\\nonexistent_path_12345"},
        "expect_status_range": (400, 599),
    },
    {
        "name": "preview_file: 不存在的 file_path",
        "method": "POST",
        "endpoint": "/api/preview_file",
        "request": {"target_path": SAMPLE_DIR, "file_path": "nonexistent/file.txt"},
        "expect_status_range": (400, 599),
    },
    {
        "name": "multi_scan: 空 target_paths",
        "method": "POST",
        "endpoint": "/api/multi_scan",
        "request": {"target_paths": []},
        "expect_status_range": (400, 599),
    },
    {
        "name": "task_status: 不存在的 task_id",
        "method": "GET",
        "endpoint": "/api/task_status/nonexistent-task-id",
        "request": None,
        "expect_status_range": (400, 599),
    },
]


def verify_error_contracts():
    """验证错误响应契约：4xx/5xx 时必须包含 detail 字段"""
    print(f"\n{YELLOW}{'=' * 60}{RESET}")
    print(f"{YELLOW}Error Response Contracts{RESET}")
    print(f"{YELLOW}{'=' * 60}{RESET}")

    results = []
    for case in ERROR_CASES:
        print(f"\n  {case['name']}")
        if case["method"] == "GET":
            resp = client.get(case["endpoint"])
        else:
            resp = client.post(case["endpoint"], json=case["request"])

        lo, hi = case["expect_status_range"]
        status_ok = lo <= resp.status_code <= hi
        has_detail = "detail" in resp.json() if resp.status_code >= 400 else True

        passed = status_ok and has_detail
        results.append(passed)

        if not status_ok:
            print(f"    {RED}FAIL{RESET} expected {lo}-{hi}, got {resp.status_code}")
        elif not has_detail:
            print(f"    {RED}FAIL{RESET} missing 'detail' field in error response")
        else:
            print(f"    {GREEN}PASS{RESET} status={resp.status_code}, has detail")

    return all(results)


# ──────────────────────────────────────────────────────────────
# 第三类：异步任务契约
# ──────────────────────────────────────────────────────────────
TASK_STATUS_FIELDS = [
    "task_id", "task_type", "status", "percentage",
    "total", "current", "message", "current_file",
    "start_time", "end_time", "error", "result",
    "move_total", "move_done", "delete_total", "delete_done",
    "rename_total", "rename_done", "keep_total", "keep_done",
    "completed_items", "eta_seconds", "items_per_second", "formatted_eta",
]


def verify_async_task_contract():
    """验证异步任务契约：start_execute_task + task_status 轮询"""
    print(f"\n{YELLOW}{'=' * 60}{RESET}")
    print(f"{YELLOW}Async Task Contract{RESET}")
    print(f"{YELLOW}{'=' * 60}{RESET}")

    # 用全 keep plan，不会移动文件
    plan = [
        {
            "file": "cache_tmp_001.tmp",
            "action": "keep",
            "target_path": None,
            "reason": "contract test",
            "extracted_info": None,
        }
    ]

    # 1. 启动任务
    print(f"\n  POST /api/start_execute_task (keep plan)")
    resp = client.post("/api/start_execute_task", json={
        "target_path": SAMPLE_DIR,
        "plan": plan,
    })

    if resp.status_code != 200:
        print(f"    {RED}FAIL{RESET} HTTP {resp.status_code}")
        return False

    data = resp.json()
    start_fields = ["status", "task_id", "total_items", "task"]
    missing = [f for f in start_fields if f not in data]
    if missing:
        print(f"    {RED}FAIL{RESET} missing fields: {missing}")
        return False

    task_id = data["task_id"]
    print(f"    {GREEN}PASS{RESET} task_id={task_id}")

    # 2. 轮询 task_status
    print(f"\n  GET /api/task_status/{task_id}")
    max_polls = 20
    final_data = None
    for i in range(max_polls):
        resp = client.get(f"/api/task_status/{task_id}")
        if resp.status_code != 200:
            print(f"    {RED}FAIL{RESET} HTTP {resp.status_code}")
            return False
        final_data = resp.json()
        if final_data.get("status") in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.1)

    if final_data is None:
        print(f"    {RED}FAIL{RESET} no response from task_status")
        return False

    missing = [f for f in TASK_STATUS_FIELDS if f not in final_data]
    if missing:
        print(f"    {RED}FAIL{RESET} missing fields: {missing}")
        return False

    print(f"    {GREEN}PASS{RESET} status={final_data['status']}, all {len(TASK_STATUS_FIELDS)} fields present")
    return True


# ──────────────────────────────────────────────────────────────
# 第四类：路由存在性校验
# ──────────────────────────────────────────────────────────────
def extract_doc_routes():
    """从 API_CONTRACT.md 提取接口路径"""
    doc_path = ROOT / "API_CONTRACT.md"
    content = doc_path.read_text(encoding="utf-8")
    # 匹配 ## N. METHOD /path 格式
    pattern = r"##\s+\d+\.\s+(GET|POST)\s+(/\S+)"
    routes = []
    for method, path in re.findall(pattern, content):
        # 去掉路径中的 {param} 占位符，只保留前缀
        clean_path = re.sub(r"\{[^}]+\}", "", path).rstrip("/")
        routes.append((method, path, clean_path))
    return routes


def get_app_routes():
    """获取 app 中注册的路由"""
    routes = set()
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            for method in route.methods:
                if method in ("GET", "POST"):
                    routes.add((method, route.path))
    return routes


def verify_route_coverage():
    """验证 API_CONTRACT.md 中的路由都在 app 中注册"""
    print(f"\n{YELLOW}{'=' * 60}{RESET}")
    print(f"{YELLOW}Route Coverage (API_CONTRACT.md vs app routes){RESET}")
    print(f"{YELLOW}{'=' * 60}{RESET}")

    doc_routes = extract_doc_routes()
    app_routes = get_app_routes()

    results = []
    for method, original_path, clean_path in doc_routes:
        # 检查是否有匹配的路由（支持 /api/ 前缀和直接路径）
        found = False
        for app_method, app_path in app_routes:
            if app_method == method:
                # 直接匹配
                if app_path == clean_path:
                    found = True
                    break
                # 如果 doc 路径有参数被清理了，检查 app 路径是否以 clean_path 开头且包含参数
                if "{" in original_path and app_path.startswith(clean_path) and "{" in app_path:
                    found = True
                    break
                # 去掉 /api 前缀比较
                app_clean = app_path.replace("/api", "", 1) if app_path.startswith("/api") else app_path
                doc_clean = clean_path.replace("/api", "", 1) if clean_path.startswith("/api") else clean_path
                if app_clean == doc_clean:
                    found = True
                    break
                # 如果 doc 路径有参数被清理了，检查去掉前缀后是否匹配
                if "{" in original_path and app_clean.startswith(doc_clean) and "{" in app_path:
                    found = True
                    break

        passed = found
        results.append(passed)

        if found:
            print(f"  {GREEN}PASS{RESET} {method} {original_path}")
        else:
            print(f"  {RED}FAIL{RESET} {method} {original_path} - not found in app routes")

    return all(results)


def main():
    print("=" * 60)
    print("Frontend-Backend API Contract Verification")
    print(f"Sample: {SAMPLE_DIR}")
    print("=" * 60)

    # 第一类：正常响应契约
    print(f"\n{YELLOW}{'=' * 60}{RESET}")
    print(f"{YELLOW}Normal Response Contracts{RESET}")
    print(f"{YELLOW}{'=' * 60}{RESET}")

    results = []
    for endpoint, contracts in CONTRACTS.items():
        request_data = get_request_data(endpoint)
        passed = verify_endpoint(endpoint, request_data, contracts)
        results.append((endpoint, passed))

    # 第二类：错误响应契约
    error_passed = verify_error_contracts()
    results.append(("error_contracts", error_passed))

    # 第三类：异步任务契约
    async_passed = verify_async_task_contract()
    results.append(("async_task_contract", async_passed))

    # 第四类：路由存在性
    route_passed = verify_route_coverage()
    results.append(("route_coverage", route_passed))

    # 汇总
    print(f"\n{'=' * 60}")
    passed_count = sum(1 for _, p in results if p)
    total = len(results)

    print(f"\nResults: {passed_count}/{total} checks passed\n")

    failed = [name for name, p in results if not p]
    if failed:
        print(f"{RED}Failed:{RESET}")
        for f in failed:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print(f"{GREEN}All contract verifications passed!{RESET}")


if __name__ == "__main__":
    main()
