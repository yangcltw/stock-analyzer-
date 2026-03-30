# prompt-logger Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code plugin that automatically records every user prompt into SQLite, with commands for rating, searching, statistics, and exporting.

**Architecture:** Three hooks (SessionStart for DB init, UserPromptSubmit for recording, SessionEnd for tool summary) + four slash commands (log-search, log-rate, log-stats, log-export). All data stored in `~/.prompt-logger/logs.db`. Shell scripts use `sqlite3` CLI for all DB operations.

**Tech Stack:** Bash, SQLite3, jq (for JSON parsing in hooks)

---

## File Structure

```
prompt-logger/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── commands/
│   ├── log-search.md            # /log-search command
│   ├── log-rate.md              # /log-rate command
│   ├── log-stats.md             # /log-stats command
│   └── log-export.md            # /log-export command
├── hooks/
│   ├── hooks.json               # Hook event configuration
│   └── scripts/
│       ├── init-db.sh           # SessionStart: create DB + tables
│       ├── record-prompt.sh     # UserPromptSubmit: INSERT prompt
│       └── session-summary.sh   # SessionEnd: UPDATE tools_used
├── scripts/
│   ├── db.sh                    # Shared DB path + helper functions
│   ├── search.sh                # Query logic for /log-search
│   ├── rate.sh                  # Update logic for /log-rate
│   ├── stats.sh                 # Stats queries for /log-stats
│   └── export.sh                # Export logic for /log-export
└── README.md                    # Usage documentation
```

**Responsibilities:**
- `hooks/scripts/` — Automatic event-driven scripts (no user interaction)
- `scripts/` — CLI scripts invoked by slash commands (user-facing)
- `commands/` — Markdown prompts that instruct Claude how to parse user input and call scripts

---

## Task 1: Plugin Manifest + Shared DB Helper

**Files:**
- Create: `prompt-logger/.claude-plugin/plugin.json`
- Create: `prompt-logger/scripts/db.sh`

- [ ] **Step 1: Create plugin directory structure**

```bash
mkdir -p prompt-logger/.claude-plugin
mkdir -p prompt-logger/commands
mkdir -p prompt-logger/hooks/scripts
mkdir -p prompt-logger/scripts
```

- [ ] **Step 2: Write plugin.json**

Create `prompt-logger/.claude-plugin/plugin.json`:

```json
{
  "name": "prompt-logger",
  "version": "1.0.0",
  "description": "Auto-record prompts for AI usage evaluation. Search, rate, analyze, and export your Claude Code interaction history.",
  "author": {
    "name": "prompt-logger"
  },
  "license": "MIT"
}
```

- [ ] **Step 3: Write shared DB helper**

Create `prompt-logger/scripts/db.sh`:

```bash
#!/bin/bash
# Shared database configuration and helpers for prompt-logger
# Source this file: source "$(dirname "$0")/../scripts/db.sh"

DB_DIR="$HOME/.prompt-logger"
DB_PATH="$DB_DIR/logs.db"
EXPORT_DIR="$DB_DIR/exports"

ensure_db() {
  if [ ! -f "$DB_PATH" ]; then
    echo "prompt-logger: database not initialized" >&2
    exit 1
  fi
}

query() {
  sqlite3 -separator '|' "$DB_PATH" "$1"
}

query_csv() {
  sqlite3 -header -csv "$DB_PATH" "$1"
}

query_json() {
  sqlite3 -json "$DB_PATH" "$1"
}
```

- [ ] **Step 4: Commit**

```bash
cd prompt-logger
git init
git add .claude-plugin/plugin.json scripts/db.sh
git commit -m "feat: init plugin manifest and shared DB helper"
```

---

## Task 2: Database Initialization Hook

**Files:**
- Create: `prompt-logger/hooks/scripts/init-db.sh`

- [ ] **Step 1: Write init-db.sh**

Create `prompt-logger/hooks/scripts/init-db.sh`:

```bash
#!/bin/bash
set -euo pipefail

DB_DIR="$HOME/.prompt-logger"
DB_PATH="$DB_DIR/logs.db"
EXPORT_DIR="$DB_DIR/exports"

# Create directories
mkdir -p "$DB_DIR" "$EXPORT_DIR"

# Create table + indexes (idempotent)
sqlite3 "$DB_PATH" <<'SQL'
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS logs (
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

CREATE INDEX IF NOT EXISTS idx_timestamp ON logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_project ON logs(project);
CREATE INDEX IF NOT EXISTS idx_rating ON logs(rating);
CREATE INDEX IF NOT EXISTS idx_session ON logs(session_id);
SQL

# Secure permissions
chmod 600 "$DB_PATH"

exit 0
```

- [ ] **Step 2: Make executable and test**

```bash
chmod +x prompt-logger/hooks/scripts/init-db.sh
bash prompt-logger/hooks/scripts/init-db.sh
# Verify DB created
sqlite3 ~/.prompt-logger/logs.db ".tables"
# Expected: logs
sqlite3 ~/.prompt-logger/logs.db ".schema logs"
# Expected: CREATE TABLE logs (...)
```

- [ ] **Step 3: Clean up test DB and commit**

```bash
rm -rf ~/.prompt-logger
cd prompt-logger
git add hooks/scripts/init-db.sh
git commit -m "feat: add SessionStart hook for DB initialization"
```

---

## Task 3: Record Prompt Hook

**Files:**
- Create: `prompt-logger/hooks/scripts/record-prompt.sh`

- [ ] **Step 1: Write record-prompt.sh**

Create `prompt-logger/hooks/scripts/record-prompt.sh`:

```bash
#!/bin/bash
set -euo pipefail

DB_PATH="$HOME/.prompt-logger/logs.db"

# Exit silently if DB doesn't exist yet
[ -f "$DB_PATH" ] || exit 0

# Read hook input from stdin
INPUT=$(cat)

SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // ""')
USER_PROMPT=$(echo "$INPUT" | jq -r '.user_prompt // ""')
CWD=$(echo "$INPUT" | jq -r '.cwd // ""')

# Skip empty prompts
[ -z "$USER_PROMPT" ] && exit 0

# Derive metadata
PROJECT=$(basename "$CWD" 2>/dev/null || echo "unknown")
BRANCH=$(git -C "$CWD" branch --show-current 2>/dev/null || echo "")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Escape single quotes for SQL
ESCAPED_PROMPT=$(echo "$USER_PROMPT" | sed "s/'/''/g")
ESCAPED_PROJECT=$(echo "$PROJECT" | sed "s/'/''/g")

# INSERT record
sqlite3 "$DB_PATH" "INSERT INTO logs (session_id, timestamp, project, branch, prompt) VALUES ('$SESSION_ID', '$TIMESTAMP', '$ESCAPED_PROJECT', '$BRANCH', '$ESCAPED_PROMPT');"

exit 0
```

- [ ] **Step 2: Test the script**

```bash
chmod +x prompt-logger/hooks/scripts/record-prompt.sh

# Init DB first
bash prompt-logger/hooks/scripts/init-db.sh

# Simulate a UserPromptSubmit hook input
echo '{"session_id":"test-123","user_prompt":"How do I write a function?","cwd":"/Users/test/my-project"}' | bash prompt-logger/hooks/scripts/record-prompt.sh

# Verify record
sqlite3 ~/.prompt-logger/logs.db "SELECT id, session_id, project, prompt FROM logs;"
# Expected: 1|test-123|my-project|How do I write a function?
```

- [ ] **Step 3: Test edge cases**

```bash
# Empty prompt — should skip silently
echo '{"session_id":"test-123","user_prompt":"","cwd":"/tmp"}' | bash prompt-logger/hooks/scripts/record-prompt.sh
echo "Exit code: $?"
# Expected: 0

# Prompt with single quotes
echo '{"session_id":"test-456","user_prompt":"What'\''s the best approach?","cwd":"/tmp"}' | bash prompt-logger/hooks/scripts/record-prompt.sh
sqlite3 ~/.prompt-logger/logs.db "SELECT id, prompt FROM logs WHERE session_id='test-456';"
# Expected: 2|What's the best approach?
```

- [ ] **Step 4: Clean up and commit**

```bash
rm -rf ~/.prompt-logger
cd prompt-logger
git add hooks/scripts/record-prompt.sh
git commit -m "feat: add UserPromptSubmit hook for prompt recording"
```

---

## Task 4: Session Summary Hook

**Files:**
- Create: `prompt-logger/hooks/scripts/session-summary.sh`

- [ ] **Step 1: Write session-summary.sh**

Create `prompt-logger/hooks/scripts/session-summary.sh`:

```bash
#!/bin/bash
set -euo pipefail

DB_PATH="$HOME/.prompt-logger/logs.db"

# Exit silently if DB doesn't exist
[ -f "$DB_PATH" ] || exit 0

# Read hook input from stdin
INPUT=$(cat)

SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // ""')
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // ""')

[ -z "$SESSION_ID" ] && exit 0

# Extract tool names from transcript if available
TOOLS_JSON="[]"
if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ]; then
  # Extract unique tool names from transcript (tool_use lines)
  TOOLS=$(grep -o '"tool_name":"[^"]*"' "$TRANSCRIPT_PATH" 2>/dev/null \
    | sed 's/"tool_name":"//;s/"//' \
    | sort -u \
    | jq -R . | jq -s . 2>/dev/null || echo "[]")
  TOOLS_JSON="$TOOLS"
fi

# Escape for SQL
ESCAPED_TOOLS=$(echo "$TOOLS_JSON" | sed "s/'/''/g")

# Update all records for this session
sqlite3 "$DB_PATH" "UPDATE logs SET tools_used = '$ESCAPED_TOOLS' WHERE session_id = '$SESSION_ID' AND tools_used IS NULL;"

exit 0
```

- [ ] **Step 2: Test the script**

```bash
# Init DB and insert a test record
bash prompt-logger/hooks/scripts/init-db.sh
echo '{"session_id":"sess-001","user_prompt":"test prompt","cwd":"/tmp"}' | bash prompt-logger/hooks/scripts/record-prompt.sh

# Simulate SessionEnd with no transcript (graceful handling)
echo '{"session_id":"sess-001","transcript_path":""}' | bash prompt-logger/hooks/scripts/session-summary.sh
sqlite3 ~/.prompt-logger/logs.db "SELECT tools_used FROM logs WHERE session_id='sess-001';"
# Expected: [] (empty array)
```

- [ ] **Step 3: Clean up and commit**

```bash
rm -rf ~/.prompt-logger
cd prompt-logger
git add hooks/scripts/session-summary.sh
git commit -m "feat: add SessionEnd hook for tool usage summary"
```

---

## Task 5: Hooks Configuration

**Files:**
- Create: `prompt-logger/hooks/hooks.json`

- [ ] **Step 1: Write hooks.json**

Create `prompt-logger/hooks/hooks.json`:

```json
{
  "description": "prompt-logger: auto-record prompts and session summaries",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/init-db.sh\"",
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
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/record-prompt.sh\"",
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
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/session-summary.sh\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Validate JSON syntax**

```bash
cat prompt-logger/hooks/hooks.json | jq . > /dev/null
echo "Exit code: $?"
# Expected: 0
```

- [ ] **Step 3: Commit**

```bash
cd prompt-logger
git add hooks/hooks.json
git commit -m "feat: add hooks.json configuration"
```

---

## Task 6: /log-search Command

**Files:**
- Create: `prompt-logger/scripts/search.sh`
- Create: `prompt-logger/commands/log-search.md`

- [ ] **Step 1: Write search.sh**

Create `prompt-logger/scripts/search.sh`:

```bash
#!/bin/bash
set -euo pipefail

source "$(dirname "$0")/db.sh"
ensure_db

# Parse arguments
KEYWORD=""
PROJECT=""
FROM_DATE=""
TO_DATE=""
RATING=""
TAG=""
LIMIT=20

while [ $# -gt 0 ]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --from) FROM_DATE="$2"; shift 2 ;;
    --to) TO_DATE="$2"; shift 2 ;;
    --rating) RATING="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --limit) LIMIT="$2"; shift 2 ;;
    *) KEYWORD="$1"; shift ;;
  esac
done

# Build WHERE clause
CONDITIONS=()
if [ -n "$KEYWORD" ]; then
  ESCAPED_KW=$(echo "$KEYWORD" | sed "s/'/''/g")
  CONDITIONS+=("prompt LIKE '%${ESCAPED_KW}%'")
fi
if [ -n "$PROJECT" ]; then
  CONDITIONS+=("project = '$(echo "$PROJECT" | sed "s/'/''/g")'")
fi
if [ -n "$FROM_DATE" ]; then
  CONDITIONS+=("timestamp >= '$FROM_DATE'")
fi
if [ -n "$TO_DATE" ]; then
  CONDITIONS+=("timestamp <= '$TO_DATE'")
fi
if [ -n "$RATING" ]; then
  CONDITIONS+=("rating = $RATING")
fi
if [ -n "$TAG" ]; then
  ESCAPED_TAG=$(echo "$TAG" | sed "s/'/''/g")
  CONDITIONS+=("tags LIKE '%\"${ESCAPED_TAG}\"%'")
fi

WHERE=""
if [ ${#CONDITIONS[@]} -gt 0 ]; then
  WHERE="WHERE $(IFS=' AND '; echo "${CONDITIONS[*]}")"
fi

SQL="SELECT id, substr(timestamp, 1, 16) AS time, project, substr(prompt, 1, 60) AS prompt_preview, COALESCE(rating, '-') AS rating FROM logs $WHERE ORDER BY timestamp DESC LIMIT $LIMIT;"

echo "ID|Time|Project|Prompt|Rating"
echo "--|----|---------|----|------"
query "$SQL"
```

- [ ] **Step 2: Write log-search.md command**

Create `prompt-logger/commands/log-search.md`:

```markdown
---
name: log-search
description: Search prompt history. Usage: /log-search [keyword] [--project name] [--from date] [--to date] [--rating 1-5] [--tag tag] [--limit n]
---

The user wants to search their prompt history. Parse their request and run the search script.

Extract from the user's message:
- keyword: free text to search in prompts (optional)
- --project: project name filter (optional)
- --from / --to: date range in YYYY-MM-DD format (optional)
- --rating: 1-5 rating filter (optional)
- --tag: tag name filter (optional)
- --limit: number of results, default 20 (optional)

Run the search script with the extracted parameters:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/search.sh" [keyword] [--project name] [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--rating N] [--tag name] [--limit N]
```

Present the results as a formatted table. If no results found, say so.
```

- [ ] **Step 3: Make executable and test**

```bash
chmod +x prompt-logger/scripts/search.sh

# Set up test data
bash prompt-logger/hooks/scripts/init-db.sh
echo '{"session_id":"s1","user_prompt":"How to write tests in Python?","cwd":"/Users/test/backend"}' | bash prompt-logger/hooks/scripts/record-prompt.sh
echo '{"session_id":"s1","user_prompt":"Fix the login bug","cwd":"/Users/test/backend"}' | bash prompt-logger/hooks/scripts/record-prompt.sh
echo '{"session_id":"s2","user_prompt":"Create a React component","cwd":"/Users/test/frontend"}' | bash prompt-logger/hooks/scripts/record-prompt.sh

# Test keyword search
bash prompt-logger/scripts/search.sh "login"
# Expected: 1 row with "Fix the login bug"

# Test project filter
bash prompt-logger/scripts/search.sh --project frontend
# Expected: 1 row with "Create a React component"

# Test no results
bash prompt-logger/scripts/search.sh "nonexistent"
# Expected: header only, no rows
```

- [ ] **Step 4: Clean up and commit**

```bash
rm -rf ~/.prompt-logger
cd prompt-logger
git add scripts/search.sh commands/log-search.md
git commit -m "feat: add /log-search command"
```

---

## Task 7: /log-rate Command

**Files:**
- Create: `prompt-logger/scripts/rate.sh`
- Create: `prompt-logger/commands/log-rate.md`

- [ ] **Step 1: Write rate.sh**

Create `prompt-logger/scripts/rate.sh`:

```bash
#!/bin/bash
set -euo pipefail

source "$(dirname "$0")/db.sh"
ensure_db

ACTION="${1:-list}"

case "$ACTION" in
  list)
    echo "Unrated prompts (most recent 5):"
    echo ""
    echo "ID|Time|Project|Prompt"
    echo "--|----|---------|----|"
    query "SELECT id, substr(timestamp, 1, 16) AS time, project, substr(prompt, 1, 60) AS prompt_preview FROM logs WHERE rating IS NULL ORDER BY timestamp DESC LIMIT 5;"
    ;;
  rate)
    ID="$2"
    SCORE="$3"
    NOTE="${4:-}"
    TAGS="${5:-}"

    # Validate score
    if [ "$SCORE" -lt 1 ] || [ "$SCORE" -gt 5 ] 2>/dev/null; then
      echo "Error: rating must be 1-5" >&2
      exit 1
    fi

    # Build UPDATE
    SET_PARTS="rating = $SCORE"
    if [ -n "$NOTE" ]; then
      ESCAPED_NOTE=$(echo "$NOTE" | sed "s/'/''/g")
      SET_PARTS="$SET_PARTS, rating_note = '$ESCAPED_NOTE'"
    fi
    if [ -n "$TAGS" ]; then
      # Convert comma-separated to JSON array
      TAGS_JSON=$(echo "$TAGS" | tr ',' '\n' | sed 's/^ *//;s/ *$//' | jq -R . | jq -s . 2>/dev/null || echo "[]")
      ESCAPED_TAGS=$(echo "$TAGS_JSON" | sed "s/'/''/g")
      SET_PARTS="$SET_PARTS, tags = '$ESCAPED_TAGS'"
    fi

    sqlite3 "$DB_PATH" "UPDATE logs SET $SET_PARTS WHERE id = $ID;"

    # Show updated record
    echo "Updated:"
    query "SELECT id, substr(prompt, 1, 60) AS prompt, rating, rating_note, tags FROM logs WHERE id = $ID;"
    ;;
  *)
    echo "Usage: rate.sh list | rate.sh rate <id> <1-5> [note] [tags]" >&2
    exit 1
    ;;
esac
```

- [ ] **Step 2: Write log-rate.md command**

Create `prompt-logger/commands/log-rate.md`:

```markdown
---
name: log-rate
description: Rate a prompt interaction 1-5. Usage: /log-rate [id] [score] [--note text] [--tags tag1,tag2]
---

The user wants to rate their prompt interactions. Parse their request:

**No arguments:** Show unrated prompts for the user to choose from.

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/rate.sh" list
```

**With ID and score:** Rate a specific prompt.

Extract:
- id: the log entry ID (required)
- score: 1-5 rating (required)
- --note: optional rating note text
- --tags: optional comma-separated tags

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/rate.sh" rate <id> <score> "<note>" "<tags>"
```

After rating, confirm what was updated. If the user doesn't provide an ID, show the unrated list first and ask which one to rate.
```

- [ ] **Step 3: Test**

```bash
chmod +x prompt-logger/scripts/rate.sh

# Set up test data
bash prompt-logger/hooks/scripts/init-db.sh
echo '{"session_id":"s1","user_prompt":"Help me write tests","cwd":"/tmp/proj"}' | bash prompt-logger/hooks/scripts/record-prompt.sh
echo '{"session_id":"s1","user_prompt":"Debug the API","cwd":"/tmp/proj"}' | bash prompt-logger/hooks/scripts/record-prompt.sh

# List unrated
bash prompt-logger/scripts/rate.sh list
# Expected: 2 rows

# Rate a prompt
bash prompt-logger/scripts/rate.sh rate 1 5 "Very helpful" "testing,productive"
# Expected: Updated: 1|Help me write tests|5|Very helpful|["testing","productive"]

# List unrated again
bash prompt-logger/scripts/rate.sh list
# Expected: 1 row (only the unrated one)
```

- [ ] **Step 4: Clean up and commit**

```bash
rm -rf ~/.prompt-logger
cd prompt-logger
git add scripts/rate.sh commands/log-rate.md
git commit -m "feat: add /log-rate command"
```

---

## Task 8: /log-stats Command

**Files:**
- Create: `prompt-logger/scripts/stats.sh`
- Create: `prompt-logger/commands/log-stats.md`

- [ ] **Step 1: Write stats.sh**

Create `prompt-logger/scripts/stats.sh`:

```bash
#!/bin/bash
set -euo pipefail

source "$(dirname "$0")/db.sh"
ensure_db

DAYS="${1:-30}"
SINCE=$(date -u -v-${DAYS}d +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -d "$DAYS days ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "2000-01-01T00:00:00Z")

echo "=== Prompt Logger Stats (last $DAYS days) ==="
echo ""

# Total interactions
TOTAL=$(query "SELECT COUNT(*) FROM logs WHERE timestamp >= '$SINCE';")
DAYS_WITH_DATA=$(query "SELECT COUNT(DISTINCT date(timestamp)) FROM logs WHERE timestamp >= '$SINCE';")
if [ "$DAYS_WITH_DATA" -gt 0 ] 2>/dev/null; then
  DAILY_AVG=$((TOTAL / DAYS_WITH_DATA))
else
  DAILY_AVG=0
fi
echo "Total interactions: $TOTAL"
echo "Days with activity: $DAYS_WITH_DATA"
echo "Daily average: $DAILY_AVG"
echo ""

# By project
echo "--- By Project ---"
query "SELECT project, COUNT(*) AS count FROM logs WHERE timestamp >= '$SINCE' GROUP BY project ORDER BY count DESC LIMIT 10;"
echo ""

# Rating distribution
echo "--- Rating Distribution ---"
query "SELECT COALESCE(CAST(rating AS TEXT), 'unrated') AS rating, COUNT(*) AS count FROM logs WHERE timestamp >= '$SINCE' GROUP BY rating ORDER BY rating;"
echo ""

# Top tools
echo "--- Top Tools ---"
query "SELECT value AS tool, COUNT(*) AS count FROM logs, json_each(logs.tools_used) WHERE timestamp >= '$SINCE' AND tools_used IS NOT NULL AND tools_used != '[]' GROUP BY value ORDER BY count DESC LIMIT 5;"
echo ""

# Rating trend: recent half vs older half
MIDPOINT=$(query "SELECT datetime(MIN(julianday(timestamp)) + (MAX(julianday(timestamp)) - MIN(julianday(timestamp))) / 2) FROM logs WHERE timestamp >= '$SINCE' AND rating IS NOT NULL;")
if [ -n "$MIDPOINT" ] && [ "$MIDPOINT" != "" ]; then
  echo "--- Rating Trend ---"
  OLDER_AVG=$(query "SELECT ROUND(AVG(rating), 2) FROM logs WHERE timestamp >= '$SINCE' AND timestamp < '$MIDPOINT' AND rating IS NOT NULL;")
  RECENT_AVG=$(query "SELECT ROUND(AVG(rating), 2) FROM logs WHERE timestamp >= '$SINCE' AND timestamp >= '$MIDPOINT' AND rating IS NOT NULL;")
  echo "Older period avg: ${OLDER_AVG:-N/A}"
  echo "Recent period avg: ${RECENT_AVG:-N/A}"
fi
```

- [ ] **Step 2: Write log-stats.md command**

Create `prompt-logger/commands/log-stats.md`:

```markdown
---
name: log-stats
description: Show prompt usage statistics. Usage: /log-stats [--days 30]
---

The user wants to see statistics about their prompt usage. Parse their request:

Extract:
- --days: number of days to analyze (default 30)

Run the stats script:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/stats.sh" <days>
```

Present the output in a well-formatted way. Add brief insights if any trends are notable (e.g., "Your average rating improved from 3.2 to 4.1 — nice progress!").
```

- [ ] **Step 3: Test**

```bash
chmod +x prompt-logger/scripts/stats.sh

# Set up test data
bash prompt-logger/hooks/scripts/init-db.sh
for i in 1 2 3 4 5; do
  echo "{\"session_id\":\"s$i\",\"user_prompt\":\"Test prompt $i\",\"cwd\":\"/tmp/proj\"}" | bash prompt-logger/hooks/scripts/record-prompt.sh
done
bash prompt-logger/scripts/rate.sh rate 1 4 "" ""
bash prompt-logger/scripts/rate.sh rate 2 5 "" ""
bash prompt-logger/scripts/rate.sh rate 3 3 "" ""

# Run stats
bash prompt-logger/scripts/stats.sh 30
# Expected: Total 5, rating distribution, no tools yet
```

- [ ] **Step 4: Clean up and commit**

```bash
rm -rf ~/.prompt-logger
cd prompt-logger
git add scripts/stats.sh commands/log-stats.md
git commit -m "feat: add /log-stats command"
```

---

## Task 9: /log-export Command

**Files:**
- Create: `prompt-logger/scripts/export.sh`
- Create: `prompt-logger/commands/log-export.md`

- [ ] **Step 1: Write export.sh**

Create `prompt-logger/scripts/export.sh`:

```bash
#!/bin/bash
set -euo pipefail

source "$(dirname "$0")/db.sh"
ensure_db

FORMAT="${1:-csv}"
FROM_DATE="${2:-}"
TO_DATE="${3:-}"

# Build WHERE
CONDITIONS=()
if [ -n "$FROM_DATE" ]; then
  CONDITIONS+=("timestamp >= '$FROM_DATE'")
fi
if [ -n "$TO_DATE" ]; then
  CONDITIONS+=("timestamp <= '$TO_DATE'")
fi

WHERE=""
if [ ${#CONDITIONS[@]} -gt 0 ]; then
  WHERE="WHERE $(IFS=' AND '; echo "${CONDITIONS[*]}")"
fi

SQL="SELECT id, session_id, timestamp, project, branch, prompt, response_summary, tools_used, rating, rating_note, tags FROM logs $WHERE ORDER BY timestamp DESC;"

mkdir -p "$EXPORT_DIR"
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")

case "$FORMAT" in
  csv)
    OUTFILE="$EXPORT_DIR/prompt-log-$TIMESTAMP.csv"
    query_csv "$SQL" > "$OUTFILE"
    echo "Exported to: $OUTFILE"
    ;;
  json)
    OUTFILE="$EXPORT_DIR/prompt-log-$TIMESTAMP.json"
    query_json "$SQL" > "$OUTFILE"
    echo "Exported to: $OUTFILE"
    ;;
  md)
    OUTFILE="$EXPORT_DIR/prompt-log-$TIMESTAMP.md"
    {
      echo "# Prompt Log Report"
      echo ""
      echo "Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
      echo ""
      # Summary stats
      TOTAL=$(query "SELECT COUNT(*) FROM logs $WHERE;")
      RATED=$(query "SELECT COUNT(*) FROM logs $WHERE AND rating IS NOT NULL;" 2>/dev/null || echo "0")
      AVG_RATING=$(query "SELECT ROUND(AVG(rating), 2) FROM logs $WHERE AND rating IS NOT NULL;" 2>/dev/null || echo "N/A")
      echo "| Metric | Value |"
      echo "|--------|-------|"
      echo "| Total prompts | $TOTAL |"
      echo "| Rated | $RATED |"
      echo "| Average rating | ${AVG_RATING:-N/A} |"
      echo ""
      echo "## Entries"
      echo ""
      # Each entry
      query "SELECT id, timestamp, project, prompt, COALESCE(CAST(rating AS TEXT), '-') AS rating, COALESCE(rating_note, '') AS note FROM logs $WHERE ORDER BY timestamp DESC;" | while IFS='|' read -r id ts proj prompt rating note; do
        echo "### #$id — $ts"
        echo "**Project:** $proj | **Rating:** $rating"
        echo ""
        echo "> $prompt"
        if [ -n "$note" ]; then
          echo ""
          echo "*Note: $note*"
        fi
        echo ""
        echo "---"
        echo ""
      done
    } > "$OUTFILE"
    echo "Exported to: $OUTFILE"
    ;;
  *)
    echo "Error: format must be csv, json, or md" >&2
    exit 1
    ;;
esac
```

- [ ] **Step 2: Write log-export.md command**

Create `prompt-logger/commands/log-export.md`:

```markdown
---
name: log-export
description: Export prompt logs. Usage: /log-export [--format csv|json|md] [--from YYYY-MM-DD] [--to YYYY-MM-DD]
---

The user wants to export their prompt logs. Parse their request:

Extract:
- --format: csv (default), json, or md
- --from: start date in YYYY-MM-DD format (optional)
- --to: end date in YYYY-MM-DD format (optional)

Run the export script:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/export.sh" <format> "<from_date>" "<to_date>"
```

After export, show the file path and file size. If markdown format, offer to show a preview of the first few entries.
```

- [ ] **Step 3: Test**

```bash
chmod +x prompt-logger/scripts/export.sh

# Set up test data
bash prompt-logger/hooks/scripts/init-db.sh
echo '{"session_id":"s1","user_prompt":"Test CSV export","cwd":"/tmp/proj"}' | bash prompt-logger/hooks/scripts/record-prompt.sh
echo '{"session_id":"s1","user_prompt":"Test JSON export","cwd":"/tmp/proj"}' | bash prompt-logger/hooks/scripts/record-prompt.sh
bash prompt-logger/scripts/rate.sh rate 1 4 "Good" "test"

# Test CSV
bash prompt-logger/scripts/export.sh csv
# Expected: Exported to: ~/.prompt-logger/exports/prompt-log-YYYYMMDD-HHMMSS.csv

# Test JSON
bash prompt-logger/scripts/export.sh json
# Expected: Exported to: ~/.prompt-logger/exports/prompt-log-YYYYMMDD-HHMMSS.json

# Test Markdown
bash prompt-logger/scripts/export.sh md
# Expected: Exported to: ~/.prompt-logger/exports/prompt-log-YYYYMMDD-HHMMSS.md

# Verify file contents
cat ~/.prompt-logger/exports/prompt-log-*.csv | head -5
cat ~/.prompt-logger/exports/prompt-log-*.json | jq '.[0]'
```

- [ ] **Step 4: Clean up and commit**

```bash
rm -rf ~/.prompt-logger
cd prompt-logger
git add scripts/export.sh commands/log-export.md
git commit -m "feat: add /log-export command"
```

---

## Task 10: README + Final Integration Test

**Files:**
- Create: `prompt-logger/README.md`

- [ ] **Step 1: Write README.md**

Create `prompt-logger/README.md`:

```markdown
# prompt-logger

A Claude Code plugin that automatically records every prompt you send, for evaluating and improving your AI usage.

## Features

- **Auto-record** — Every prompt is logged automatically via hooks
- **Rate interactions** — Score 1-5 with notes and tags
- **Search history** — Full-text search with project/date/rating filters
- **Statistics** — Usage trends, rating progress, tool analysis
- **Export** — CSV, JSON, or Markdown reports

## Installation

Copy or symlink this directory to your Claude Code plugins:

```bash
cp -r prompt-logger ~/.claude/plugins/local/prompt-logger
```

Or for development (live changes):

```bash
ln -s "$(pwd)/prompt-logger" ~/.claude/plugins/local/prompt-logger
```

Restart Claude Code after installation.

## Commands

| Command | Description |
|---------|-------------|
| `/log-search [keyword]` | Search prompts. Filters: `--project`, `--from`, `--to`, `--rating`, `--tag`, `--limit` |
| `/log-rate [id] [1-5]` | Rate an interaction. Options: `--note`, `--tags` |
| `/log-stats [--days 30]` | View usage statistics and trends |
| `/log-export [--format csv\|json\|md]` | Export logs. Filters: `--from`, `--to` |

## Data Storage

All data is stored locally in `~/.prompt-logger/logs.db` (SQLite).

Exports go to `~/.prompt-logger/exports/`.

## Requirements

- `sqlite3` CLI (pre-installed on macOS/Linux)
- `jq` (for JSON parsing in hooks)
```

- [ ] **Step 2: Run full integration test**

```bash
# Clean slate
rm -rf ~/.prompt-logger

# 1. Init
bash prompt-logger/hooks/scripts/init-db.sh
echo "✓ DB initialized"

# 2. Record prompts
echo '{"session_id":"integration-test","user_prompt":"How do I deploy to production?","cwd":"/Users/test/my-app"}' | bash prompt-logger/hooks/scripts/record-prompt.sh
echo '{"session_id":"integration-test","user_prompt":"Fix the authentication bug","cwd":"/Users/test/my-app"}' | bash prompt-logger/hooks/scripts/record-prompt.sh
echo '{"session_id":"integration-test","user_prompt":"Create a React dashboard","cwd":"/Users/test/frontend"}' | bash prompt-logger/hooks/scripts/record-prompt.sh
echo "✓ 3 prompts recorded"

# 3. Rate
bash prompt-logger/scripts/rate.sh rate 1 5 "Excellent guidance" "deploy,productive"
bash prompt-logger/scripts/rate.sh rate 2 3 "Took too many tries" "debug"
echo "✓ 2 prompts rated"

# 4. Search
echo "--- Search: 'deploy' ---"
bash prompt-logger/scripts/search.sh "deploy"
echo ""
echo "--- Search: project=frontend ---"
bash prompt-logger/scripts/search.sh --project frontend

# 5. Stats
echo ""
echo "--- Stats ---"
bash prompt-logger/scripts/stats.sh 30

# 6. Export
echo ""
bash prompt-logger/scripts/export.sh csv
bash prompt-logger/scripts/export.sh json
bash prompt-logger/scripts/export.sh md
echo "✓ Exported all formats"

# 7. Session summary
echo '{"session_id":"integration-test","transcript_path":""}' | bash prompt-logger/hooks/scripts/session-summary.sh
echo "✓ Session summary complete"

echo ""
echo "=== All integration tests passed ==="
```

- [ ] **Step 3: Clean up and commit**

```bash
rm -rf ~/.prompt-logger
cd prompt-logger
git add README.md
git commit -m "docs: add README with usage instructions"
```

- [ ] **Step 4: Make all scripts executable**

```bash
cd prompt-logger
chmod +x hooks/scripts/*.sh scripts/*.sh
git add -u
git commit -m "chore: ensure all scripts are executable"
```
