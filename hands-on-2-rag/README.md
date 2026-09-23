# Hands-on 2 — Build RAG with NemoClaw

> **Tiếng Việt:** Bài này biến 28 tài liệu kỹ thuật thành chỉ mục vector bằng mô hình
> embedding chạy cục bộ, rồi truy vấn qua agent trong sandbox NemoClaw. Mỗi câu trả lời
> đều kèm đoạn tài liệu gốc. Tài liệu có cài sẵn các "bẫy" (hai sản phẩm gần giống nhau,
> thông tin theo phiên bản firmware, và một hướng dẫn an toàn đã bị thay thế) để thấy rõ
> điểm mạnh và giới hạn của RAG. Phiếu bài tập cho học viên: [PARTICIPANT.md](PARTICIPANT.md).

Workshop lab assets: a synthetic technical corpus, an ingestion pipeline, a
reference Q&A set with automated verification, and the script that loads it all
into the NemoClaw sandbox. `../setup.sh` does the loading; the workshop app's
**2 · RAG** tab is the demo.

```
documents ──▶ chunking ──▶ embeddings ──▶ vector index ──▶ agent answers
  28 files      400 tokens   2560-dim      SQLite + vec0      with citations
```

## Layout

```
hands-on-2-rag/
├── corpus/                 28 synthetic Aurora Grid Systems documents
├── ingestion/build_index.py  heading-aware chunker + embedder (stdlib only)
├── index/
│   ├── rag_index.json      checked-in index (82 chunks, dim 2560) — the app's fallback
│   ├── manifest.json       corpus hash + model + dim, for drift detection
│   └── fallback/           snapshot of a built sandbox index (setup.sh refreshes it)
├── verification/
│   ├── reference_qa.json   30 questions, answers, exact source strings
│   ├── verify_qa.py        answer key ↔ corpus integrity check
│   ├── consistency_check.py  cross-document contradiction check
│   ├── evaluate_retrieval.py retrieval quality gate
│   └── verify_agent.py     queries the live sandbox's memory search
├── canonical_facts.md      authoring control sheet for the corpus
└── PARTICIPANT.md          participant worksheet
```

The sandbox side is `../scripts/lab2-sandbox-setup.sh`.

## How it is wired on the DGX Spark

```
  OpenShell sandbox                        DGX Spark host
  ┌──────────────────────┐  host.openshell  ┌──────────────────┐   loopback   ┌───────────────┐
  │ openclaw memory      │──── .internal ──▶│ embed-proxy.py   │─────────────▶│ Ollama        │
  │ search (sqlite-vec)  │     :11434       │ embeddings only  │ 127.0.0.1    │ qwen3-embed   │
  └──────────────────────┘                  └──────────────────┘   :11434     └───────────────┘
```

On Linux NemoClaw keeps Ollama bound to `127.0.0.1:11434` on purpose and gives
the chat model its own token-gated route. A sandbox container cannot see the
host's loopback, so `scripts/embed-proxy.py` listens on the address the sandbox
resolves `host.openshell.internal` to and forwards **only** the embedding
endpoints (`/api/embed`, `/v1/embeddings`, plus model listing). Chat, pull and
delete requests are refused, and POST bodies must name the embedding model.
The stock `local-inference` policy preset already allows that address and port,
so no policy is loosened.

On Docker Desktop (the Mac this lab was authored on) `host.openshell.internal`
reaches the host loopback directly, so no proxy is needed there.

## The corpus

**Aurora Grid Systems (AGS)** — a fictional industrial battery-storage
manufacturer. 28 documents: datasheets, installation and commissioning guides,
maintenance schedules, safety bulletins, firmware release notes, warranty, RMA,
spares, site planning, grid-code notes, glossary, FAQ, escalation matrix.

Difficulty is deliberate:

- **Confusable pairs.** AX-400 and AX-600 share spec *names* with divergent
  values (energy, DC voltage, peak power, cooling, IP rating, cold limit,
  torque, clearance) — including one spec that is intentionally identical
  (0.5C) to punish retrieval that keys on the wrong field.
- **Version-specific facts** keyed to Comet C2 firmware 3.7.4 / 3.8.0 / 3.8.1 /
  3.8.2 and Helios H3 4.3.0 / 4.4.1.
- **Superseded facts with effective dates.** SB-2024-03 mandates a 5-minute
  DC-disconnect wait; URGENT SB-2025-01 supersedes it with 12 minutes plus a
  <50 V DC check. The old value is still in the corpus, so a retriever that
  ignores dates or status returns a dangerous answer.

## Verification gates

From the repository root:

```bash
python3 hands-on-2-rag/verification/verify_qa.py            # answer key matches the corpus
python3 hands-on-2-rag/verification/consistency_check.py    # corpus is internally consistent
python3 hands-on-2-rag/verification/evaluate_retrieval.py --k 6 --query-prefix qwen3
python3 hands-on-2-rag/verification/verify_agent.py --sandbox my-assistant
```

The first two are offline. The third needs Ollama. The fourth is the real gate:
it asks all 30 reference questions of the live sandbox's memory search. On the
authoring machine it passed 30/30; the third reported recall@5 = 100%,
answer-in-context@5 = 96.7%, MRR 0.819.

### Rebuilding the local index

```bash
python3 hands-on-2-rag/ingestion/build_index.py --corpus hands-on-2-rag/corpus \
  --out hands-on-2-rag/index --target-chars 1600 --overlap-chars 320
```

`--target-chars 1600` mirrors OpenClaw's own chunker (400 tokens, 80 overlap,
not configurable), so this index is a faithful proxy for the sandbox's.

## Gotchas that will bite you

**The config key depends on the OpenClaw version.** The build NemoClaw pins
(OpenClaw 2026.7.1) reads `agents.defaults.memorySearch`; upstream has moved to
`memory.search.*`. The schema is strict, so the wrong key is silently ignored.
Always confirm with
`nemoclaw my-assistant exec -- env TMPDIR=/tmp openclaw memory status --deep`.

**The embedding provider needs the OpenAI-compatible adapter.** With
`api: "ollama"` OpenClaw 2026.7.1 ignores `baseUrl` and dials `127.0.0.1:11434`,
which does not exist inside the sandbox. `lab2-sandbox-setup.sh` uses
`openai-completions` against `/v1`.

**`TMPDIR` must be set** for memory operations inside the sandbox, or index
builds fail with a misleading `unable to open database file`.

**Only three locations are indexed:** `<workspace>/MEMORY.md`,
`<workspace>/USER.md` and `<workspace>/memory/**/*.md`. The corpus goes into
`memory/`.

**The index is identity-bound.** It records the provider id, model and
endpoint. Change any of them and vector search pauses with an identity
mismatch; rebuild with `openclaw memory index --force`.

**The embedding model is asymmetric.** `qwen3-embedding` expects an instruction
prefix on *queries* only. The app's local search reproduces it.

More findings, with reproduction steps: [../docs/SANDBOX-NOTES.md](../docs/SANDBOX-NOTES.md).

## Reference questions worth using live

| Category | Question | Watch for |
|---|---|---|
| disambiguation | "What torque do I use on the DC terminals?" | Both values, bound to the right cabinet — 25 N·m AX-400, 35 N·m AX-600 |
| superseded | "How long after opening the DC disconnect before I can remove a module cover?" | **12 minutes** (SB-2025-01). Surfacing the 5-minute figure is the teaching moment |
| version-specific | "Which port does the Comet C2 use for Modbus?" | 502 on 3.7.4 and 3.8.2, 1502 on 3.8.0/3.8.1 |
| procedure | "What coolant does the AX-600 take?" | 50/50 propylene glycol / water, 38 L — the AX-400 is air cooled |
