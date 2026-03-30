# Session Prompts — Acceptance Criteria & Boundary Tests

> Session Date: 2026-03-30
> Model: Claude Opus 4.6 (1M context)

---

## Prompt 1

請依照這個專案的需求與規格，起一個 teamates 討論驗收表準，邊界測試

---

## Prompt 2

（frontend-engineer 回報完成後，無額外指令）

---

## Prompt 3

（qa-engineer 回報完成後，無額外指令）

---

## Prompt 4

（backend-engineer 回報完成後，無額外指令）

---

## Prompt 5

你會怎麼時做，會影響目前正在進行的實作嗎

---

## Prompt 6

因為目前還在實作後端，請把高優先風險標注 TODO, 然後進行後面任務

---

## Prompt 7

請開始執行

---

## Prompt 8

（backend-datasource 回報完成後，無額外指令）

---

## Prompt 9

（frontend-tester 回報完成後，無額外指令）

---

## Prompt 10

（backend-logic 回報完成後，無額外指令）

---

## Prompt 11

剩下哪些任務？可以實作嗎

---

## Prompt 12

先看目前代碼 commit的狀況

---

## Prompt 13

拆分

---

## Prompt 14

把剩下的 TODO完成

---

## Prompt 15

yes

---

## Prompt 16

我要新增 ai 工具

---

## Prompt 17

輸出 analysis.md

---

## Prompt 18

輸出這個 seesion的 prompt 到 prompt/analysis_prompt.md

---

## Session Summary

### 完成事項

1. **驗收標準與邊界測試討論** — 3 位 teammates（QA/Backend/Frontend）平行討論，產出 `docs/acceptance-criteria-and-boundary-tests.md`
2. **標注 TODO(high)** — 在 yfinance_source、twse_source、db_source 標注 4 個高優先風險
3. **Backend 邊界測試** — 新增 35 個測試案例，覆蓋 DataSource/Indicator/Cache/Router 邊界
4. **Frontend 測試環境** — 設定 Vitest + React Testing Library，新增 15 個元件測試
5. **Git commits 拆分** — 分為 docs/backend tests/frontend tests 三個 commit
6. **修復 TODO(high)** — asyncio.wait_for timeout、.TWO 上櫃支援、httpx timeout 捕捉、AI graceful degradation
7. **AI 工具分析** — 輸出 `docs/analysis.md` 分析 AI Analyzer 架構現況與改善建議

### Commits

| Hash | Message |
|------|---------|
| `72afea7` | docs: acceptance criteria and boundary test plan for both projects |
| `07ab0fc` | test: backend boundary tests covering datasource, indicator, cache, and router edge cases |
| `28f0ef1` | test: frontend test setup (Vitest) and component boundary tests |
| `f24592d` | fix: resolve all high-priority risks from acceptance review |

### Test Results

| Scope | Tests | Status |
|-------|-------|--------|
| Backend | 73 | All pass |
| Frontend | 15 | All pass |
| Total | 88 | All pass |
