# DGX Spark AI Workshop — three hands-on labs on NemoClaw + Ollama

Everything runs locally on one NVIDIA DGX Spark: the models, the documents, the
agent and its tools. One command sets it all up; one web page runs the demo in
Vietnamese or English.

> **Non-technical operator?** Read [START-HERE.md](START-HERE.md) (Vietnamese + English).

The one command, in a Terminal on the DGX Spark (no sudo):

```bash
curl -fsSL https://raw.githubusercontent.com/an6122003/nemoclaw-rag-demo/main/install.sh | bash
```

It downloads the workshop into `~/dgx-workshop` (or updates it), runs
`setup.sh` — install, download, check every lab — and opens the app. Running it
again is safe and also updates. After that:

```bash
bash ~/dgx-workshop/start.sh   # every other time (or double-click "DGX Spark Workshop" on the desktop)
bash ~/dgx-workshop/stop.sh    # stop the app
```

Equivalent by hand: `git clone https://github.com/an6122003/nemoclaw-rag-demo.git ~/dgx-workshop && cd ~/dgx-workshop && bash setup.sh`.

## The labs

| | Lab | Folder | What the audience sees |
|---|---|---|---|
| 1 | **Fine-tuning Local LLMs** | [hands-on-1-finetune/](hands-on-1-finetune/) | LoRA on Qwen2.5-1.5B in the NGC PyTorch container, a live loss curve, export to GGUF, `ollama create`, then before/after answers side by side |
| 2 | **Build RAG with NemoClaw** | [hands-on-2-rag/](hands-on-2-rag/) | 28 technical manuals, retrieval by OpenClaw memory search inside the NemoClaw sandbox, answers with their source passages, traps for confusable products and superseded safety advice |
| 3 | **Build an Agentic Workflow** | [hands-on-3-agent/](hands-on-3-agent/) | "Phân tích doanh số theo vùng…" → the NemoClaw agent reads the Excel file and calls Python tools (pandas, matplotlib, openpyxl) → chart + insight + Excel report, every step shown live |
| 4 | **Challenge: OpenClaw** | the app's OpenClaw tab | teams open OpenClaw's own chat UI on the Spark (`/openclaw` hands the browser the gateway token) and build their own workflow: shell and Python in the sandbox, the 28 manuals through memory search, the sales skill, files; starter ideas, a showcase checklist, and a second model (`/model qwen`) |

Labs 1-3 each put the same question side by side: before/after fine-tuning,
without/with RAG (the same chat model with no documents), and the model alone
(no tools, no data) next to the agent. The "without" side is asked after the
main answer, through `POST /api/plain/stream`.

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
│   NemoClaw sandbox "dgx-workshop" (own gateway :8990, OpenShell + OpenClaw 2026.7.1)│
│     agent main     : default agent, memory search over the corpus, skill sales-analyst
│     agent analyst  : Lab 3, minimal tool profile — it can only ask for the 4 tools │
│        │ inference.local (token-gated)          │ host.openshell.internal:11434    │
│        ▼                                        ▼                                 │
│   NemoClaw Ollama proxy :11435 ──▶  Ollama 127.0.0.1:11434  ◀── embed-proxy.py     │
│                                     nemotron-3.5-lightning · qwen3-embedding:4b · │
│                                     qwen2.5:1.5b-instruct · aurora-assistant      │
└───────────────────────────────────────────────────────────────────────────────────┘
```

Why these choices:

- **Ollama for every model.** One server, one download path, and it is
  NemoClaw's own default local provider. The chat and agent model is NVIDIA
  `nemotron-3.5-lightning:30b-a3b` (33B mixture-of-experts, 3B active), which
  the workshop is required to use; thinking is switched off for the labs, and
  it answers at about 99 tokens/s on the Spark. `qwen3.6:35b`, NemoClaw's own
  choice for a large-memory host, works too (`CHAT_MODEL` in `workshop.env`).
- **Client tools for Lab 3.** OpenClaw's gateway can expose an OpenAI-compatible
  `/v1/chat/completions` endpoint whose tool contract hands each tool call back
  to the caller. The agent (in the sandbox) reasons and chooses; the app runs
  the Python and shows every step. That is the slide's flow, observable.
- **A dedicated `analyst` agent** with the `minimal` tool profile: no shell,
  files or web. Its whole capability is the four tools the app offers.
- **A narrow Ollama door for Lab 2 and the challenge.** On Linux NemoClaw keeps
  Ollama on loopback and routes the chat model through its token-gated proxy.
  OpenClaw's memory search needs embeddings too, so `scripts/embed-proxy.py`
  opens a door on the sandbox-facing address that forwards *only* embedding
  endpoints, plus streamed chat completions for the one extra model
  (`EXTRA_CHAT_MODEL`) that OpenClaw's own chat may switch to.
- **Graceful degradation.** Every lab has a direct path: Lab 2 falls back to the
  checked-in vector index, Lab 3 runs the same agent loop against Ollama, and the
  page says which route answered. A broken sandbox never stops the demo.

## What `setup.sh` does

| # | Step | Notes |
|---|---|---|
| 1 | Check the computer | Linux/aarch64, GPU, memory, disk, internet; installs what is missing (curl, git, zstd, python3-venv, Docker + buildx, the NVIDIA Container Toolkit), starts Docker, adds the account to the docker group; asks for the sudo password, again if it was mistyped |
| 2 | Ollama | installs or upgrades (≥ 0.32.9, NemoClaw's minimum; three attempts), systemd drop-in: loopback only, `OLLAMA_CONTEXT_LENGTH=32768`, keep-alive 30 min |
| 3 | Models | `nemotron-3.5-lightning:30b-a3b` (~25 GB), `qwen3-embedding:4b` (2.5 GB), `qwen2.5:1.5b-instruct` (~1 GB), `qwen3.6:35b` (~22 GB, OpenClaw's second model); downloads reconnect when they crawl; both chat models get a 262144-token context as a model parameter (`scripts/ollama-context.py`); checks the 2560-dim embedding |
| 4 | Python env | `uv` + `.venv` with the pinned pandas / matplotlib / openpyxl |
| 5 | NemoClaw | official installer, then `nemoclaw onboard` (OpenClaw, Ollama provider, sandbox `dgx-workshop` on its own gateway, port 8990, `NEMOCLAW_CONTEXT_WINDOW=262144`), with one `--resume` retry |
| 6 | Lab 2 | starts the embedding proxy, uploads the corpus, configures memory search, builds the index (`scripts/lab2-sandbox-setup.sh`) |
| 7 | Lab 3 + OpenClaw | creates the `analyst` agent, enables the endpoint, proves a tool call round-trips, installs the skill and keeps its Python wheels on the host; for OpenClaw's own chat: 262144-token context, 16384-token replies, Qwen as a second model, heartbeats off (`scripts/lab3-sandbox-setup.sh`) |
| 8 | Lab 1 | pulls `nvcr.io/nvidia/pytorch:25.11-py3`, builds `workshop-finetune`, caches the base model, trains once |
| 9 | Final check | `app/selftest.py` runs every lab end to end with the real models; summary; desktop shortcut |

Safe to re-run: every step checks the real state first. Everything is logged to
`setup-log.txt`. Useful flags: `--check-only`, `--skip-finetune`,
`--skip-sandbox`, `--retrain`, `--no-start`, `--yes`.

About 85 GB is downloaded (models ~50 GB, PyTorch container ~20 GB, sandbox
image ~3 GB, base model 3 GB). Expect 1-2 hours on a good connection.

## Without internet

After setup the workshop needs no internet, also after the computer restarts:
models, the Lab 1 base model, the Python wheels for the sandbox, fonts, logos
and GSAP are all on the machine. One NemoClaw detail needed work: a gateway on a
custom port (the workshop's 8990) is a plain background process, and NemoClaw's
only way to start it again is `nemoclaw onboard`, whose preflight stops when DNS
does not answer. `start.sh` therefore starts the gateway itself, exactly as
NemoClaw launched it (`scripts/nemoclaw-gateway.py` records binary, environment
and process name on every start, and updates NemoClaw's pid file and runtime
marker), then the sandbox container and its forwards. Onboarding stays as the
fallback, and that path needs DNS: if a machine ever has to rebuild its sandbox,
give it any network (a phone hotspot is enough).

## Configuration

All settings are in [workshop.env](workshop.env) and can be overridden from the
environment, e.g. a smaller chat model:

```bash
CHAT_MODEL=qwen3.5:9b bash setup.sh
```

| Setting | Default | |
|---|---|---|
| `CHAT_MODEL` | `nemotron-3.5-lightning:30b-a3b` | chat + agent model (also the sandbox's inference model; setup and start switch the sandbox to it) |
| `EXTRA_CHAT_MODEL` | `qwen3.6:35b` | a second model for OpenClaw's own chat (`/model qwen`), reached through the workshop's Ollama door because NemoClaw's managed route answers with its one model; empty to skip |
| `CHAT_CONTEXT` / `CHAT_MAX_TOKENS` | `262144` / `16384` | context window of the chat models (measured on a 128 GB Spark: Nemotron 26 GB, Qwen about 30 GB) and OpenClaw's reply limit |
| `EMBED_MODEL` | `qwen3-embedding:4b` | must match the pre-built index in `hands-on-2-rag/index/` |
| `LAB1_BASE_HF` / `LAB1_BASE_OLLAMA` | `Qwen/Qwen2.5-1.5B-Instruct` / `qwen2.5:1.5b-instruct` | the model fine-tuned, and its library twin for "before" |
| `LAB1_BASE_IMAGE` | `nvcr.io/nvidia/pytorch:25.11-py3` | the image NVIDIA's DGX Spark fine-tuning playbooks use |
| `SANDBOX` / `AGENT_ID` | `dgx-workshop` / `analyst` | |
| `NEMOCLAW_GATEWAY_PORT` | `8990` | the workshop's own OpenShell gateway, so it never clashes with an existing sandbox (a gateway serves one model route) |
| `HUB_PORT` | `8090` | `bash start.sh --lan` also serves other laptops on the network |

## Verified

On a DGX Spark (GB10, DGX OS 24.04, Ollama 0.34.3, NemoClaw v0.0.124 with
OpenClaw 2026.7.1), 6 October 2026, starting from an empty folder with the one
command:

- `install.sh` cloned the repository and `setup.sh` passed all nine steps; the
  final end-to-end check passed for all three labs. Running the command again
  updated the checkout through git and passed the check again.
- **Lab 1:** LoRA on Qwen2.5-1.5B-Instruct inside `nvcr.io/nvidia/pytorch:25.11-py3`:
  86 examples × 5 epochs = 55 steps in 37 s, 70 s including the merge and the
  GGUF q8_0 export (1.6 GB). `ollama create aurora-assistant` registers it and it
  answers *"Tôi là Aurora, trợ lý kỹ thuật AI của Aurora Grid Systems…"*.
- **Lab 2:** the corpus is indexed inside the `dgx-workshop` sandbox through the
  embeddings-only proxy (qwen3-embedding:4b, 2560 dims), and the agent answers
  the check question (558 kWh) through the sandbox. With Nemotron, the guide's
  three questions give the answers it promises (25 / 35 N·m; 12 minutes, the
  old 5-minute rule withdrawn; no stock price), in 4-6 s.
- **Lab 3:** `openclaw/analyst` through the gateway with
  `nemotron-3.5-lightning:30b-a3b`: dataset info → analysis → chart → Excel
  report, and the answer names Đà Nẵng (+64.5%). The slide question,
  alternating Vietnamese and English, passed 10 of 10 runs (18-30 s), and all 14
  example questions ended with a chart and a report (17-36 s). That took
  guardrails in the agent loop and two settings for this model (tools offered
  directly, temperature 0.2), described in
  [hands-on-3-agent/README.md](hands-on-3-agent/README.md#guardrails). (With
  qwen3.6:35b, earlier the same day: 30 of 30.)
- **The web app**, through an SSH tunnel: live fine-tuning with the loss chart
  (34 s), the before/after comparison, Lab 2's answers with their sources, and
  Lab 3's trace, chart and report download.
- **A machine that has never had NemoClaw**, simulated on the Spark with an empty
  home folder and separate ports: the install command installed NemoClaw
  v0.0.124 (Node, OpenShell, the CLI), NVIDIA's installer created the workshop
  sandbox, and Lab 2 passed through it. Lab 3 passed once the model check was in
  place (NemoClaw had substituted `nemotron-3-nano:30b` because memory was busy).
- **After a restart**, simulated by stopping the sandbox container, the
  workshop's gateway, its dashboard forwarder and the Ollama token proxy:
  `start.sh`, run through the desktop icon's launcher, brought everything back
  in 3 of 3 rounds on the final version. About 45 s when NemoClaw reuses the
  sandbox; about 4 minutes when it recreates it, because the documents are
  indexed and the agent set up again. Labs 2 and 3 passed through the sandbox
  every time.
- **A sandbox left stuck** by an interrupted recovery: running the install
  command again repaired it (recreated, labs set up again).
- All 14 Lab 3 example questions, Vietnamese and English, ended with a chart and
  an Excel report through NemoClaw (16-31 s).
- The terminal flow in a pseudo-terminal: the install command shows the notice,
  continues on Enter, and asks for the password.

Added on 7 October 2026, same Spark:

- **OpenClaw's own agent** overflowed at 16k context ("Context overflow"). With
  262144 tokens: the field-service checklist from the manuals, the maintenance
  plan file and the Python script ran end to end; the sales skill finished in a
  sub-agent.
- **OpenClaw UI:** `/openclaw` opens it signed in; the model picker lists
  Inference (Nemotron) and Workshop Ollama (Qwen); a chat switched to Qwen
  answered through the workshop door, and `/model nemotron` switched it back.
- **Restart without onboarding:** gateway process killed, its forward killed,
  sandbox container stopped; `start.sh` (through the desktop launcher) started
  the gateway itself and everything was back in about 50 s; NemoClaw reported
  Phase: Ready, OpenClaw's UI answered, Labs 2 and 3 passed through the sandbox.
- **Offline wheels:** with the sandbox's PyPI access removed and its Python
  packages deleted, start reinstalled pandas / matplotlib / openpyxl from the
  host copy in 10 s.
- **Lab 2 / Lab 3 comparisons:** without RAG, Nemotron claimed the AX-600 holds
  "1000 litres" (with RAG: 558 kWh, datasheet); without tools it asked for the
  Excel file (the agent: Đà Nẵng +64.5%, chart, report).

Not covered by those runs:

- Typing the password. The runs were unattended, so the steps that need `sudo`
  were skipped (that Spark already had Ollama on loopback with a 16k context and
  the account in the docker group). With the password, `setup.sh` writes
  `/etc/systemd/system/ollama.service.d/zz-workshop.conf`, adds the account to
  the docker group if needed and continues inside it.
- A real power cycle (simulated above), and double-clicking the icon itself
  (its launcher script was used; the desktop entry passes
  `desktop-file-validate`). A restart with the network cable unplugged: the
  restart path above makes no network calls of its own, but it was run with
  the network up.
- Installing Docker or the NVIDIA Container Toolkit on a machine without them
  (DGX OS ships both).
- Installing Ollama itself (`curl -fsSL https://ollama.com/install.sh | sh`
  with the password): this Spark already had Ollama 0.34.3.

## Security notes

- Ollama stays on `127.0.0.1`. The only non-loopback listeners are NemoClaw's
  token-gated proxy and the workshop's Ollama door on the Docker bridge address
  (embeddings, and chat for `EXTRA_CHAT_MODEL` only).
- The `analyst` agent has no shell, file or web tools; the app validates every
  tool call (unknown tools and bad arguments come back as errors the agent can
  read).
- The in-sandbox skill needs pandas: `lab3-sandbox-setup.sh` installs it from
  wheels kept on the host, or from PyPI (adding NemoClaw's `pypi` preset only
  if the sandbox does not already have it, and removing it again).
- OpenClaw's own agent (the challenge) has its full tool set inside the
  sandbox (shell, files, memory search, web fetch limited by the policy); the
  `/openclaw` link carries the gateway token and is only served to a browser
  on the Spark itself.
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
                       nemoclaw-gateway.py  ollama-context.py  pull-model.py
                       fix-sandbox-policy.sh  ollama-relay.py
app/static/            brand/ (logos, background)  fonts/ (Be Vietnam Pro, Saira)  vendor/ (GSAP)
docs/SANDBOX-NOTES.md  NemoClaw/OpenShell findings, with reproduction steps
```

Troubleshooting and the hard-won sandbox findings (IPv6 host-gateway egress,
the config guard, `TMPDIR`, never `pkill` the gateway):
[docs/SANDBOX-NOTES.md](docs/SANDBOX-NOTES.md).
