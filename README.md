# 本项目是比赛参赛作品，写的很烂，建议别看

# 本地炼金炉 (Local Data Alchemist)

一个处理“极其混乱本地文件夹”的 AI Agent Demo：扫描本地目录中的日志、票据、表格、截图、PDF 等文件，生成可编辑的整理计划（移动/重命名/删除/保留），并支持一键执行与回滚（Undo）。

## 功能概览

- 本地目录锁定：输入路径或唤起 Windows 系统目录选择器
- 文件扫描与分类：按扩展名做基础分类，生成文件清单与统计
- 内容嗅探：对文本类文件读取最多 512 字节作为摘要片段
- LLM 生成计划：输出严格 JSON 的 Action Plan，并提取结构化信息
  - 财务类（financial）：amount/currency/date/merchant/document_id/title/summary
  - 日志类（system_log）：title/severity/error_code/root_cause/recommended_action/summary
- 计划审批：前端可编辑每条 action/target_path/reason
- 执行与回滚：
  - 执行后写入 snapshot.json
  - 删除操作进入 .alchemy_trash
  - Undo 将文件移动回原位置并清理 snapshot/.alchemy_trash
- 结案报告导出：导出本次计划、洞察、执行结果与控制台日志

## 项目结构

```text
.
├── backend/                 # FastAPI 后端
│   ├── main.py              # 扫描/计划/执行/回滚/LLM 调用
│   ├── requirements.txt
│   └── .env                 # 本地私密配置（已被 gitignore）
└── frontend/                # Vue3 + Tailwind 前端
    ├── src/App.vue
    ├── src/style.css
    ├── vite.config.js       # /api 代理到 VITE_API_TARGET
    └── package.json
```

## 环境准备

- Python 3.10+（建议 3.11/3.12/3.13）
- Node.js 18+（建议 18/20）

## 后端配置（backend/.env）

在 `backend/.env` 填写（示例，不要提交 Key）：

```ini
OPENAI_API_KEY=你的key
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen3-vl-flash-2026-01-22
OPENAI_TIMEOUT_SECONDS=180
```

### 敏感信息说明（务必阅读）

- `backend/.env` 包含 LLM API Key 等敏感信息，已被禁止提交到 GitHub。
- 本仓库已在 `.gitignore` 中忽略 `.env / backend/.env / frontend/.env` 及常见的 `.env.*` 变体。
- 你需要在本地自行创建 `backend/.env` 文件并填入自己的 Key。

`.env` 文件格式说明：

- 每行一条 `KEY=VALUE`，不需要引号（除非你确实想把引号当作值的一部分）。
- 允许空行；推荐使用 UTF-8 编码。
- 常用字段如下（复制后把 OPENAI_API_KEY 替换成你自己的 Key）：

```ini
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1（示例URL，请更换为你的供应商提供的URL）
OPENAI_MODEL=qwen3-vl-flash-2026-01-22（示例模型名称，请替换为你需要的模型）
OPENAI_TIMEOUT_SECONDS=180（大模型超时秒数）
```

如果你怀疑曾经误提交过 `.env`（即便现在已加入 `.gitignore` 仍然可能被提交）：

1. 立刻在云厂商控制台作废/轮换 Key
2. 执行 `git ls-files | findstr /I ".env"` 检查是否有 `.env` 被追踪
3. 若已被追踪，使用 `git rm --cached backend/.env`（以及对应路径）移除并提交

## 启动方式

### 0) 一键启动（推荐）

在仓库根目录执行（会先结束占用端口的进程，再启动后端与前端）：

```powershell
cd C:\Users\Lentinel\Documents\GitHub\Local-Data-Alchemist
powershell -NoProfile -ExecutionPolicy Bypass -File .\dev.ps1
```

启动后访问：

- 前端：http://localhost:5173/
- 后端：http://localhost:8002/

### 1) 启动后端

```powershell
cd backend
python -m pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8002
```

后端健康检查：

- http://localhost:8002/
- http://localhost:8002/api/llm_debug

### 2) 启动前端

```powershell
cd frontend
npm install
$env:VITE_API_TARGET="http://localhost:8002"
npm run dev
```

打开：

- http://localhost:5173/

## 使用流程（推荐）

1. 在首页输入要处理的本地目录路径（或打开系统选择窗口）
2. 生成 AI 炼金计划（会自动展示财务条目与日志洞察）
3. 在“AI 炼金计划审批面板”中编辑 action/目标路径/理由
4. 点击“批准并执行炼金”
5. 如需恢复，点击“时光倒流”

## 说明与注意事项

- “总金额”来自 AI 对本次计划中 financial 条目的 amount 抽取求和，基于文件片段推断，不代表账户余额或真实结算金额。
- 执行后整理结果仍在目标目录内，可在执行完成卡片中复制目标目录路径。
- 如果 LLM 网络不稳定导致 timeout，系统会启用本地兜底计划，确保流程可演示。
