# App 移植技能指南

移植 App 到新架構時，可依階段使用以下 Skills 來確保品質與效率。

---

## Superpowers Skills（內建）

| Skill | 用途 | 階段 |
|-------|------|------|
| `superpowers:brainstorming` | 釐清需求、目標架構、技術選型 | 規劃 |
| `superpowers:writing-plans` | 制定分步驟的移植實作計畫 | 規劃 |
| `superpowers:executing-plans` | 按計畫逐步執行移植工作 | 實作 |
| `superpowers:dispatching-parallel-agents` | 前後端平行移植，同時派出多個 agent | 實作 |
| `superpowers:subagent-driven-development` | 獨立任務分派給子 agent 執行 | 實作 |
| `superpowers:test-driven-development` | 移植過程中確保功能正確 | 實作 |
| `superpowers:systematic-debugging` | 移植後遇到問題時系統性除錯 | 除錯 |
| `superpowers:verification-before-completion` | 每個階段完成前驗證結果 | 驗證 |
| `superpowers:requesting-code-review` | 移植完成後請求 code review | 審查 |
| `superpowers:receiving-code-review` | 收到 review 回饋後正確處理 | 審查 |
| `superpowers:finishing-a-development-branch` | 完成後決定整合方式（merge/PR/cleanup） | 發布 |
| `superpowers:using-git-worktrees` | 需要隔離環境進行移植時建立 worktree | 實作 |
| `feature-dev:feature-dev` | 導引式功能開發，分析現有架構再實作 | 實作 |
| `frontend-design:frontend-design` | 前端需要重新設計 UI 時使用 | 實作 |

## gstack Skills

| Skill | 用途 | 階段 |
|-------|------|------|
| `gstack-design-consultation` | 從零設計新架構的 design system | 規劃 |
| `gstack-design-review` | 審查新架構的設計（含修正迴圈） | 規劃 |
| `gstack-plan-eng-review` | 工程面 review 移植計畫 | 規劃 |
| `gstack-plan-design-review` | 設計面 review（報告式，不自動修正） | 規劃 |
| `gstack-plan-ceo-review` | 高層級產品方向 review | 規劃 |
| `gstack-autoplan` | 自動產生完整 review pipeline（CEO → design → eng） | 規劃 |
| `gstack-investigate` | 系統性追蹤根因，移植遇問題時使用 | 除錯 |
| `gstack-qa` | QA 測試 + 自動修正 | 驗證 |
| `gstack-qa-only` | QA 測試（僅報告，不修正） | 驗證 |
| `gstack-browse` | Headless browser 測試移植後的頁面與流程 | 驗證 |
| `gstack-benchmark` | 效能回歸測試，確保移植後效能不退化 | 驗證 |
| `gstack-cso` | 安全審計（OWASP Top 10 + STRIDE） | 驗證 |
| `gstack-review` | PR code review | 審查 |
| `gstack-ship` | 發布工作流程 | 發布 |
| `gstack-land-and-deploy` | merge → deploy → canary 驗證 | 發布 |
| `gstack-canary` | 部署後監控迴圈 | 發布 |
| `gstack-document-release` | 發布後更新文件 | 發布 |
| `gstack-retro` | 移植完成後回顧檢討 | 回顧 |

## 其他輔助 Skills

| Skill | 用途 |
|-------|------|
| `commit-commands:commit` | 建立 git commit |
| `commit-commands:commit-push-pr` | 一次完成 commit、push、開 PR |
| `commit-commands:clean_gone` | 清理已刪除的遠端分支 |
| `code-review:code-review` | Code review PR |
| `claude-md-management:revise-claude-md` | 更新 CLAUDE.md 記錄移植過程的學習 |
| `simplify` | Review 已修改的程式碼，檢查品質與效率 |

---

## 建議執行流程

```
Phase 1: 規劃
├── 1. superpowers:brainstorming        → 釐清新架構、移植範圍、技術選型
├── 2. gstack-design-consultation       → 設計新架構
├── 3. superpowers:writing-plans        → 寫出分步驟移植計畫
└── 4. gstack-plan-eng-review           → Review 計畫可行性
       (或 gstack-autoplan 一次跑完 CEO → design → eng review)

Phase 2: 實作
├── 5. superpowers:using-git-worktrees  → 建立隔離的工作環境
├── 6. superpowers:executing-plans      → 按計畫執行
├── 7. superpowers:dispatching-parallel-agents → 平行處理獨立任務
└── 8. superpowers:test-driven-development    → 邊移植邊寫測試

Phase 3: 驗證
├── 9.  gstack-qa / gstack-browse       → 功能測試 + 頁面測試
├── 10. gstack-benchmark                → 效能測試
├── 11. gstack-cso                      → 安全審計
└── 12. superpowers:verification-before-completion → 最終驗證

Phase 4: 審查與發布
├── 13. gstack-review                   → PR review
├── 14. superpowers:requesting-code-review → 請求 code review
├── 15. gstack-ship                     → 發布
├── 16. gstack-canary                   → 部署後監控
└── 17. gstack-document-release         → 更新文件

Phase 5: 回顧
└── 18. gstack-retro                    → 回顧檢討，記錄學習
```

## 使用方式

在 Claude Code 中直接輸入 skill 名稱即可調用，例如：

```
/brainstorming
/writing-plans
/gstack-qa
/gstack-ship
```

或透過 Skill tool 調用：

```
Skill: superpowers:brainstorming
Skill: gstack-review
```

---

## 安裝指南

### 前置需求

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — 已安裝並可執行 `claude` 指令
- [Git](https://git-scm.com/)
- [Bun](https://bun.sh/) v1.0+（`curl -fsSL https://bun.sh/install | bash`）
- [Node.js](https://nodejs.org/)（Windows 使用者必裝）

### Step 1: 安裝 Superpowers Skills

Superpowers 是 Claude Code 的內建 plugin，不需要額外安裝。只要你的 Claude Code 已設定好 superpowers plugin，直接使用即可。

### Step 2: 全域安裝 gstack（安裝一次，所有專案共用）

在終端機執行：

```bash
git clone https://github.com/garrytan/gstack.git ~/.claude/skills/gstack
cd ~/.claude/skills/gstack
./setup
```

安裝完成後，在任何專案的 Claude Code 中都能使用 gstack skills。

### Step 3: 將 gstack 加入特定專案（可選，讓團隊成員也能用）

在專案根目錄執行：

```bash
cp -Rf ~/.claude/skills/gstack .claude/skills/gstack
rm -rf .claude/skills/gstack/.git
cd .claude/skills/gstack
./setup
```

這會將 gstack 複製到專案的 `.claude/skills/` 目錄，commit 後團隊成員 `git clone` 就能直接用。

### Step 4: 設定專案的 CLAUDE.md

在目標專案的 `CLAUDE.md` 加入以下內容：

```markdown
## gstack

Use /browse from gstack for all web browsing. Never use mcp__claude-in-chrome__* tools.

Available skills: /office-hours, /plan-ceo-review, /plan-eng-review, /plan-design-review,
/design-consultation, /review, /ship, /land-and-deploy, /canary, /benchmark, /browse,
/qa, /qa-only, /design-review, /setup-browser-cookies, /setup-deploy, /retro,
/investigate, /document-release, /codex, /cso, /autoplan, /careful, /freeze, /guard,
/unfreeze, /gstack-upgrade.
```

### 驗證安裝

在 Claude Code 中輸入以下指令確認 skills 可用：

```
/browse goto https://example.com
```

如果看到瀏覽器截圖回應，表示安裝成功。

---

## 在其他專案中使用

### 方法 A：全域安裝（推薦）

完成 Step 2 後，直接在任何專案中打開 Claude Code 即可使用所有 gstack skills。只需確保該專案的 `CLAUDE.md` 有加入 gstack section（Step 4）。

### 方法 B：專案內安裝

適合團隊協作，每個成員 clone 後自動擁有 gstack：

```bash
# 在目標專案根目錄
cd /path/to/your-other-project

# 複製 gstack 到專案中
cp -Rf ~/.claude/skills/gstack .claude/skills/gstack
rm -rf .claude/skills/gstack/.git
cd .claude/skills/gstack && ./setup

# 回到專案根目錄，設定 CLAUDE.md
cd /path/to/your-other-project
# 將 Step 4 的內容加入 CLAUDE.md
```

### 快速開始移植流程

到目標專案後，依序在 Claude Code 中輸入：

```bash
# 1. 釐清移植需求
/office-hours

# 2. 規劃移植計畫
/plan-ceo-review
/plan-eng-review

# 3. 開始實作（在 Claude Code 中）
/brainstorming        # 或 superpowers:brainstorming
/writing-plans        # 制定計畫

# 4. 驗證
/qa https://localhost:3000
/browse goto https://localhost:3000

# 5. 發布
/review
/ship
```

---

## 疑難排解

| 問題 | 解法 |
|------|------|
| Skill 沒有出現 | `cd ~/.claude/skills/gstack && ./setup` 重新安裝 |
| `/browse` 失敗 | `cd ~/.claude/skills/gstack && bun install && bun run build` |
| 版本過舊 | 在 Claude Code 中執行 `/gstack-upgrade` |
| 團隊成員看不到 skills | 確認 `.claude/skills/gstack` 已 commit 到 repo |

## 注意事項

- 每個階段完成後建議用 `superpowers:verification-before-completion` 確認結果
- 遇到 bug 優先用 `superpowers:systematic-debugging` 或 `gstack-investigate`，不要盲目修改
- 移植完成後用 `claude-md-management:revise-claude-md` 更新 CLAUDE.md，記錄新架構的指令與慣例
- gstack 更新：`/gstack-upgrade` 或 `cd ~/.claude/skills/gstack && git pull && ./setup`
