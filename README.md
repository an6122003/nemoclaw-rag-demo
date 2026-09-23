# DGX Spark AI Workshop — three hands-on labs on NemoClaw + Ollama

Everything runs locally on one NVIDIA DGX Spark: the models, the documents, the
agent and its tools. One command sets it all up; one web page runs the demo in
Vietnamese or English.

> **Non-technical operator?** Read [START-HERE.md](START-HERE.md) (Vietnamese + English).

```bash
bash setup.sh      # once, on the DGX Spark: installs, downloads, checks every lab, opens the app
bash start.sh      # every other time (or double-click "DGX Spark Workshop" on the desktop)
bash stop.sh       # stop the app
```

## The labs

| | Lab | Folder | What the audience sees |
|---|---|---|---|
| 1 | **Fine-tuning Local LLMs** | [hands-on-1-finetune/](hands-on-1-finetune/) | LoRA on Qwen2.5-1.5B in the NGC PyTorch container, a live loss curve, export to GGUF, `ollama create`, then before/after answers side by side |
| 2 | **Build RAG with NemoClaw** | [hands-on-2-rag/](hands-on-2-rag/) | 28 technical manuals, retrieval by OpenClaw memory search inside the NemoClaw sandbox, answers with their source passages, traps for confusable products and superseded safety advice |
| 3 | **Build an Agentic Workflow** | [hands-on-3-agent/](hands-on-3-agent/) | "Phân tích doanh số theo vùng…" → the NemoClaw agent reads the Excel file and calls Python tools (pandas, matplotlib, openpyxl) → chart + insight + Excel report, every step shown live |

All three use the same fictional company, Aurora Grid Systems: the model from
Lab 1 becomes its assistant, Lab 2 searches its manuals, Lab 3 analyses its sales.

## Architecture

```
┌─────────────────────────────── NVIDIA DGX Spark ─────────────────────────────────┐
│                                                                                   │
│  Workshop app  (app/, http://127.0.0.1:8090)                                      │
│   ├─ Lab 1 ── docker run workshop-finetune (NGC PyTorch, GPU) ── GGUF ── ollama create
│   ├─ Lab 2 ── nemoclaw exec: openclaw memory search ─────────┐                    │
│   └─ Lab 3 ── POST /v1/chat/completions (client tools) ──────┤                    │
│        ▲  runs pandas / matplotlib / openpyxl                │                    │
│        └──────────── tool_calls ◀───────────────────────────┤                    │
│                                                              ▼                    │
│   NemoClaw sandbox "my-assistant"  (OpenShell policy around OpenClaw 2026.7.1)     │
│     agent main     : default agent, memory search over the corpus, skill sales-analyst
│     agent analyst  : Lab 3, minimal tool profile — it can only ask for the 4 tools │
│        │ inference.local (token-gated)          │ host.openshell.internal:11434    │
│        ▼                                        ▼                                 │
│   NemoClaw Ollama proxy :11435 ──▶  Ollama 127.0.0.1:11434  ◀── embed-proxy.py     │
│                                     qwen3.6:35b · qwen3-embedding:4b ·            │
│                                     qwen2.5:1.5b-instruct · aurora-assistant      │
└───────────────────────────────────────────────────────────────────────────────────┘
```

Why these choices:

- **Ollama for every model.** One server, one download path, and it is
  NemoClaw's own default local provider. `qwen3.6:35b` (35B mixture-of-experts,
  3B active) is what NemoClaw itself selects on a large-memory host: fast on the
  Spark, strong at tool calling and at Vietnamese.
- **Client tools for Lab 3.** OpenClaw's gateway can expose an OpenAI-compatible
  `/v1/chat/completions` endpoint whose tool contract hands each tool call back
  to the caller. The agent (in the sandbox) reasons and chooses; the app runs
  the Python and shows every step. That is the slide's flow, observable.
- **A dedicated `analyst` agent** with the `minimal` tool profile: no shell,
  files or web. Its whole capability is the four tools the app offers.
- **Embeddings-only proxy for Lab 2.** On Linux NemoClaw keeps Ollama on
  loopback and routes the chat model through its token-gated proxy. OpenClaw's
  memory search needs embeddings too, so `scripts/embed-proxy.py` opens a door
  on the sandbox-facing address that forwards *only* embedding endpoints.
- **Graceful degradation.** Every lab has a direct path: Lab 2 falls back to the
  checked-in vector index, Lab 3 runs the same agent loop against Ollama, and the
  page says which route answered. A broken sandbox never stops the demo.

## What `setup.sh` does

| # | Step | Notes |
|---|---|---|
| 1 | Check the computer | Linux/aarch64, GPU, memory, ≥60 GB disk, Docker access, internet; asks for the sudo password once |
| 2 | Ollama | installs or upgrades (≥ 0.32.9, NemoClaw's minimum), systemd drop-in: loopback only, `OLLAMA_CONTEXT_LENGTH=32768`, keep-alive 30 min |
| 3 | Models | `qwen3.6:35b` (~24 GB), `qwen3-embedding:4b` (2.5 GB), `qwen2.5:1.5b-instruct` (~1 GB); checks the 2560-dim embedding |
| 4 | Python env | `uv` + `.venv` with the pinned pandas / matplotlib / openpyxl |
| 5 | NemoClaw | official installer, then `nemoclaw onboard` (OpenClaw, Ollama provider, sandbox `my-assistant`), with one `--resume` retry |
| 6 | Lab 2 | starts the embedding proxy, uploads the corpus, configures memory search, builds the index (`scripts/lab2-sandbox-setup.sh`) |
| 7 | Lab 3 | creates the `analyst` agent, enables the endpoint, proves a tool call round-trips, installs the skill (`scripts/lab3-sandbox-setup.sh`) |
| 8 | Lab 1 | pulls `nvcr.io/nvidia/pytorch:25.11-py3`, builds `workshop-finetune`, caches the base model, trains once |
| 9 | Final check | `app/selftest.py` runs every lab end to end with the real models; summary; desktop shortcut |

Safe to re-run: every step checks the real state first. Everything is logged to
`setup-log.txt`. Useful flags: `--check-only`, `--skip-finetune`,
`--skip-sandbox`, `--retrain`, `--no-start`, `--yes`.

About 60 GB is downloaded (models ~28 GB, PyTorch container ~20 GB, sandbox
image ~3 GB, base model 3 GB). Expect 45-90 minutes on a good connection.

## Configuration

All settings are in [workshop.env](workshop.env) and can be overridden from the
environment, e.g. a smaller chat model:

```bash
CHAT_MODEL=qwen3.5:9b bash setup.sh
```

| Setting | Default | |
|---|---|---|
| `CHAT_MODEL` | `qwen3.6:35b` | chat + agent model (also the sandbox's inference model) |
| `EMBED_MODEL` | `qwen3-embedding:4b` | must match the pre-built index in `hands-on-2-rag/index/` |
| `LAB1_BASE_HF` / `LAB1_BASE_OLLAMA` | `Qwen/Qwen2.5-1.5B-Instruct` / `qwen2.5:1.5b-instruct` | the model fine-tuned, and its library twin for "before" |
| `LAB1_BASE_IMAGE` | `nvcr.io/nvidia/pytorch:25.11-py3` | the image NVIDIA's DGX Spark fine-tuning playbooks use |
| `SANDBOX` / `AGENT_ID` | `my-assistant` / `analyst` | |
| `HUB_PORT` | `8090` | `bash start.sh --lan` also serves other laptops on the network |

## Verified vs. not yet verified

Be precise about this before the event.

**Verified on the authoring machine (macOS, Apple Silicon):**

- Lab 3's agent loop, both routes, against the **real OpenClaw 2026.7.1 runtime**
  (the build NemoClaw pins) running in a plain container, with qwen3:8b on a
  remote RTX 5070: the 4-tool flow completes and names Da Nang as the
  fastest-growing region, in Vietnamese (≈26 s) and English. Direct route ≈18 s.
- The gateway behaviours Lab 3 depends on: client tool calls come back as
  structured `tool_calls`; the caller's system message is injected; a per-agent
  `AGENTS.md` is injected; `reasoning_effort: none` via `params.extra_body`
  cuts a turn from 14.8 s to 2.4 s.
- The four tools and the generated workbook (every number in the Lab 3 answer key).
- Lab 2 in a live NemoClaw sandbox (earlier session): 30/30 reference questions.

**Not yet verified — first run on the DGX Spark:**

- `setup.sh`, `start.sh`, `stop.sh` and both sandbox scripts have never run on
  Linux; the web page and `app/server.py` have not been loaded in a browser.
- Lab 1 end to end (training in the NGC container, GGUF conversion,
  `ollama create`): written against NVIDIA's playbook and llama.cpp `v0.4.1`,
  not executed.
- NemoClaw onboarding on Linux, the embedding proxy path, the in-sandbox skill,
  and `qwen3.6:35b`'s behaviour in the agent loop.

`bash setup.sh` ends with an end-to-end check of each lab and prints which ones
passed, so the first run on the Spark *is* the verification. Run it at least a
day before the workshop.

## Security notes

- Ollama stays on `127.0.0.1`. The only non-loopback listeners are NemoClaw's
  token-gated proxy and the embeddings-only proxy on the Docker bridge address.
- The `analyst` agent has no shell, file or web tools; the app validates every
  tool call (unknown tools and bad arguments come back as errors the agent can
  read).
- The in-sandbox skill needs pandas: `lab3-sandbox-setup.sh` applies NemoClaw's
  `pypi` preset, installs, and removes the preset again.
- The gateway token (full operator access to the agent) is stored in
  `.run/gateway-token` (mode 600) and only placed in links served to the DGX's
  own browser.
- Treat the box as NVIDIA's NemoClaw guidance says: a clean machine, no
  personal credentials on it.

## Repository layout

```
setup.sh · start.sh · stop.sh · workshop.env     the operator surface
START-HERE.md                                    guide for the operator (VI/EN)
app/                                             the workshop web app (stdlib server + one page)
  server.py  common.py  lab1_finetune.py  lab2_rag.py  lab3_agent.py  selftest.py  index.html
hands-on-1-finetune/   train_lora.py  run_finetune.sh  Dockerfile  data/  README.md
hands-on-2-rag/        corpus/  index/  ingestion/  verification/  PARTICIPANT.md  README.md
hands-on-3-agent/      tools/sales_tools.py  agent/AGENTS.md  skills/  data/  README.md
scripts/               workshop-lib.sh  embed-proxy.py  lab2-sandbox-setup.sh  lab3-sandbox-setup.sh
                       fix-sandbox-policy.sh  ollama-relay.py
docs/SANDBOX-NOTES.md  NemoClaw/OpenShell findings, with reproduction steps
```

Troubleshooting and the hard-won sandbox findings (IPv6 host-gateway egress,
the config guard, `TMPDIR`, never `pkill` the gateway):
[docs/SANDBOX-NOTES.md](docs/SANDBOX-NOTES.md).
