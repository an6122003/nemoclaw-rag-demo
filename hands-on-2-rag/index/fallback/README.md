# Fallback memory index

A complete, verified memory index copied from a working sandbox, so a failed
re-ingest on the day does not block the session.

**It is only valid for a sandbox whose embedding configuration matches exactly:**

| Setting | Value |
|---|---|
| provider id | `ollama-mem` |
| adapter | `openai-completions` |
| model | `qwen3-embedding:4b` |
| endpoint | `http://host.openshell.internal:11434/v1` |
| vector dims | 2560 |
| chunks / sources | 76 / 28 |

The index records that identity. If any of it differs, OpenClaw pauses vector
search and reports an identity mismatch — a stale index is worse than no index,
because it looks healthy and returns nothing.

## Restore

```bash
nemoclaw <sandbox> upload hands-on-2-rag/index/fallback/openclaw-agent.sqlite \
  /sandbox/.openclaw/agents/main/agent/openclaw-agent.sqlite

# TMPDIR must be set: SQLite derives its temp directory from it, and memory
# operations fail with a misleading "unable to open database file" without it.
nemoclaw <sandbox> exec -- env TMPDIR=/tmp openclaw memory status --index
```

## Prefer rebuilding

Restoring is a fallback, not the normal path. Rebuilding is safer and takes
about a minute:

```bash
nemoclaw <sandbox> exec -- env TMPDIR=/tmp openclaw memory index --force
```

`openclaw.json` alongside this file is the exact working configuration the index
was built with.
