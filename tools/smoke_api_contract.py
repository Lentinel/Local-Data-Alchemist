#!/usr/bin/env python3
"""
轻量冒烟测试：验证核心接口的基本响应字段。
使用 FastAPI TestClient，不启动真实服务器。
不执行会移动/删除文件的接口。
"""
import sys
from pathlib import Path

# 将 backend 目录加入 Python 路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# 测试目录
SAMPLE_DIR = str(ROOT / "sample_messy_folder")

# 颜色输出
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def check(name: str, passed: bool, detail: str = ""):
    status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    print(f"  [{status}] {name}")
    if not passed and detail:
        print(f"         {detail}")
    return passed


def test_lock_folder():
    print("\n1. POST /api/lock_folder")
    resp = client.post("/api/lock_folder", json={"target_path": SAMPLE_DIR})
    check("status 200", resp.status_code == 200, f"got {resp.status_code}")

    data = resp.json()
    checks = [
        check("has status", "status" in data),
        check("has target_path", "target_path" in data),
        check("has files", "files" in data and isinstance(data["files"], list)),
        check("has analysis", "analysis" in data),
        check("files non-empty", len(data.get("files", [])) > 0),
    ]
    if all(checks):
        file0 = data["files"][0]
        check("file has name", "name" in file0)
        check("file has path", "path" in file0)
        check("file has extension", "extension" in file0)
        check("file has category", "category" in file0)
        check("file has size", "size" in file0)
    return all(checks)


def test_preview_file():
    print("\n2. POST /api/preview_file")
    resp = client.post("/api/preview_file", json={
        "target_path": SAMPLE_DIR,
        "file_path": "documents/meeting_notes.md"
    })
    check("status 200", resp.status_code == 200, f"got {resp.status_code}")

    data = resp.json()
    checks = [
        check("has status", "status" in data),
        check("has preview", "preview" in data),
    ]
    if all(checks):
        preview = data["preview"]
        check("preview has type", "type" in preview)
        check("preview has content", "content" in preview)
    return all(checks)


def test_rename_preview():
    print("\n3. POST /api/rename_preview")
    resp = client.post("/api/rename_preview", json={
        "target_path": SAMPLE_DIR,
        "selected_files": ["documents/meeting_notes.md", "receipt_april.pdf"],
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
    })
    check("status 200", resp.status_code == 200, f"got {resp.status_code}")

    data = resp.json()
    checks = [
        check("has status", "status" in data),
        check("has previews", "previews" in data and isinstance(data["previews"], list)),
        check("has total_files", "total_files" in data),
        check("has changed_count", "changed_count" in data),
    ]
    if all(checks) and len(data["previews"]) > 0:
        p = data["previews"][0]
        check("preview has original_path", "original_path" in p)
        check("preview has original_name", "original_name" in p)
        check("preview has new_name", "new_name" in p)
        check("preview has new_path", "new_path" in p)
        check("preview has has_change", "has_change" in p)
    return all(checks)


def test_detect_duplicates():
    print("\n4. POST /api/detect_duplicates")
    resp = client.post("/api/detect_duplicates", json={
        "target_path": SAMPLE_DIR,
        "fast_mode": True
    })
    check("status 200", resp.status_code == 200, f"got {resp.status_code}")

    data = resp.json()
    checks = [
        check("has status", "status" in data),
        check("has total_files_scanned", "total_files_scanned" in data),
        check("has groups", "groups" in data and isinstance(data["groups"], list)),
        check("has total_duplicate_count", "total_duplicate_count" in data),
        check("has total_duplicate_size", "total_duplicate_size" in data),
        check("has fast_mode", "fast_mode" in data),
    ]
    return all(checks)


def test_task_status():
    print("\n5. GET /api/task_status/{task_id}")
    # 先创建一个任务
    create_resp = client.post("/api/start_execute_task", json={
        "target_path": SAMPLE_DIR,
        "plan": [
            {
                "file": "cache_tmp_001.tmp",
                "action": "keep",
                "target_path": None,
                "reason": "test",
                "extracted_info": None
            }
        ]
    })
    check("create task 200", create_resp.status_code == 200, f"got {create_resp.status_code}")

    task_id = create_resp.json().get("task_id")
    check("got task_id", task_id is not None)
    if not task_id:
        return False

    # 查询任务状态
    resp = client.get(f"/api/task_status/{task_id}")
    check("status 200", resp.status_code == 200, f"got {resp.status_code}")

    data = resp.json()
    checks = [
        check("has task_id", "task_id" in data),
        check("has task_type", "task_type" in data),
        check("has status", "status" in data),
        check("has percentage", "percentage" in data),
        check("has total", "total" in data),
        check("has current", "current" in data),
        check("has message", "message" in data),
        check("has current_file", "current_file" in data),
        check("has start_time", "start_time" in data),
        check("has eta_seconds", "eta_seconds" in data),
        check("has items_per_second", "items_per_second" in data),
        check("has formatted_eta", "formatted_eta" in data),
        check("has move_total", "move_total" in data),
        check("has move_done", "move_done" in data),
        check("has delete_total", "delete_total" in data),
        check("has delete_done", "delete_done" in data),
        check("has rename_total", "rename_total" in data),
        check("has rename_done", "rename_done" in data),
        check("has keep_total", "keep_total" in data),
        check("has keep_done", "keep_done" in data),
        check("has completed_items", "completed_items" in data),
    ]
    return all(checks)


def main():
    print("=" * 50)
    print("API Contract Smoke Test")
    print(f"Sample dir: {SAMPLE_DIR}")
    print("=" * 50)

    results = [
        test_lock_folder(),
        test_preview_file(),
        test_rename_preview(),
        test_detect_duplicates(),
        test_task_status(),
    ]

    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    if all(results):
        print(f"{GREEN}All {total} tests passed!{RESET}")
    else:
        print(f"{RED}{passed}/{total} tests passed{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
