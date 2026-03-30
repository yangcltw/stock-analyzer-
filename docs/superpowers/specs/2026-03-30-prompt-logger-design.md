# prompt-logger — Claude Code Plugin 設計規格

## 概述

一個 Claude Code plugin，自動記錄使用者發送的 prompt，用於評估 AI 使用品質與效果。支援個人回顧、主管審查、組織層級的 AI 導入成效分析。

## 目標

- 全自動記錄每次 prompt，零手動操作
- 事後可評分、標籤，追蹤 AI 使用品質
- 支援多維度統計分析
- 可匯出 CSV/JSON/Markdown，串接外部系統

## Plugin 結構

```
prompt-logger/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── log-search.md        # 搜尋記錄
│   ├── log-rate.md          # 評分互動
│   ├── log-stats.md         # 統計報表
│   └── log-export.md        # 匯出
├── hooks/
│   ├── hooks.json           # Hook 配置
│   └── scripts/
│       ├── record-prompt.sh # 記錄 prompt
│       ├── session-summary.sh # Session 結束補記
│       └── init-db.sh       # 初始化 DB
├── scripts/
│   ├── db.sh                # SQLite 共用函式
│   └── export.sh            # 匯出邏輯
└── README.md
```

## 資料模型

儲存位置：`~/.prompt-logger/logs.db`（SQLite）

```sql
CREATE TABLE logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  project TEXT,
  branch TEXT,
  prompt TEXT NOT NULL,
  response_summary TEXT,
  tools_used TEXT,
  rating INTEGER,
  rating_note TEXT,
  tags TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_timestamp ON logs(timestamp);
CREATE INDEX idx_project ON logs(project);
CREATE INDEX idx_rating ON logs(rating);
CREATE INDEX idx_session ON logs(session_id);
```

### 欄位說明

| 欄位 | 型別 | 說明 |
|------|------|------|
| session_id | TEXT | Claude Code session ID |
| timestamp | TEXT | ISO 8601 時間戳 |
| project | TEXT | 專案目錄名（basename of cwd） |
| branch | TEXT | git branch |
| prompt | TEXT | 使用者原始 prompt |
| response_summary | TEXT | 回覆摘要（手動填寫或未來 LLM 摘要） |
| tools_used | TEXT | JSON array，例如 `["Read", "Edit", "Bash"]` |
| rating | INTEGER | 1-5 評分（NULL = 未評） |
| rating_note | TEXT | 評分備註 |
| tags | TEXT | JSON array，自訂標籤 |

## Hook 設計

### hooks.json

```json
{
  "description": "Auto-record prompts and session summaries",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/init-db.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/record-prompt.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/session-summary.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### Hook 行為

**SessionStart — init-db.sh**
- 建立 `~/.prompt-logger/` 和 `~/.prompt-logger/exports/` 目錄
- `CREATE TABLE IF NOT EXISTS` 冪等初始化
- DB 檔案權限 `0600`

**UserPromptSubmit — record-prompt.sh**
- 從 stdin 讀取 JSON（`user_prompt`、`session_id`、`cwd`）
- 執行 `git branch --show-current` 取得 branch
- 以 `basename "$cwd"` 作為 project 名
- INSERT 一筆記錄到 logs 表

**SessionEnd — session-summary.sh**
- 從 stdin 讀取 `session_id` 和 `transcript_path`
- 解析 transcript 提取使用的工具列表
- UPDATE 該 session 所有記錄的 `tools_used` 欄位

## Slash Commands

### /log-search — 搜尋記錄

```
/log-search [關鍵字]
```

參數：
- `--project <name>` — 按專案篩選
- `--from <date>` / `--to <date>` — 時間範圍
- `--rating <1-5>` — 按評分篩選
- `--tag <tag>` — 按標籤篩選
- `--limit <n>` — 限制筆數（預設 20）

輸出：表格，顯示 ID、時間、專案、prompt 前 60 字、評分。

### /log-rate — 評分

```
/log-rate [id] [1-5]
```

- 不帶參數：顯示最近 5 筆未評分的記錄供選擇
- 帶 ID + 分數：直接評分
- `--note "備註"` — 加評分說明
- `--tags "debug,frontend"` — 加標籤

### /log-stats — 統計報表

```
/log-stats [--days 30]
```

輸出內容：
- 總互動次數、日均次數
- 按專案分佈
- 按評分分佈
- 最常用工具 Top 5
- 評分趨勢（近期 vs 之前）

### /log-export — 匯出

```
/log-export [--format csv|json|md] [--from date] [--to date]
```

- CSV：Excel/Google Sheets 用
- JSON：程式處理或串接外部系統
- Markdown：可讀報告，適合給主管

匯出至 `~/.prompt-logger/exports/` 目錄。

## 初始化流程

```
安裝 plugin
    ↓
首次 SessionStart
    ↓ init-db.sh
    建立 ~/.prompt-logger/
    建立 SQLite DB + 表 + 索引
    ↓
日常使用
    ↓ UserPromptSubmit hook
    每次 prompt 自動記錄
    ↓ SessionEnd hook
    補記 tools_used
```

## 資料保護

- SQLite WAL mode — 寫入不阻塞讀取
- Hook timeout 5 秒 — 不影響正常使用
- DB 檔案權限 `0600` — 僅本人可讀
- 不記錄完整回覆 — 避免 DB 過大

## 未來擴展

以下功能不在初版範圍，但資料模型已預留空間：

- LLM 自動生成 response_summary
- Web Dashboard 視覺化
- 團隊共享 DB（SQLite → PostgreSQL）
- 自動標籤分類（用 LLM 分析 prompt 類型）
