# Hands-on 2 — Build RAG and Deploy as a Local Agent with NemoClaw

Workshop lab assets: a synthetic technical corpus, an ingestion pipeline, a
reference Q&A set with automated verification, and the operator scripts that
assemble it into a running NemoClaw sandbox.

---

## Status — fully working and verified

| # | Requirement | State |
|---|---|---|
| 1 | NemoClaw onboarded and verified, participants only run onboarding | **Done** — sandbox `my-assistant` is `Ready`, OpenClaw 2026.7.1, chat inference wired end to end |
| 2 | Embedding model and vector store cached locally | **Done** — `qwen3-embedding:4b` (2560-dim) and `qwen3:8b` cached; `sqlite-vec` vector store reports ready |
| 3 | Corpus + ingestion script + pre-built index fallback | **Done** — 28 docs, ingestion script, canonical index, and a 16 MB built sandbox index in `index/fallback/` |
| 4 | Reference questions and expected answers to verify the pipeline | **Done** — 30 Q&A pairs, **30/30 retrieved from the live sandbox** |

The end-to-end proof, run against the sandbox's own memory search:

```
sandbox my-assistant — retrieval verification
  passed 30/30 (100.0%), threshold 90%
RESULT: PASS — sandbox retrieval answers the reference set.
```

```
Indexed: 28/28 files · 76 chunks
Embeddings: ready
Vector dims: 2560
Vector store: ready
```

### Three defects had to be fixed to get here

None were configuration mistakes; all three were reproduced from a clean install
and each is repaired automatically by `scripts/fix-sandbox-policy.sh` and
`scripts/lab-setup.sh`. Full evidence and reproduction commands:
[docs/SANDBOX-NOTES.md](docs/SANDBOX-NOTES.md).

1. **Host egress was denied.** NemoClaw's `local-inference` preset allow-lists
   IPv4 RFC1918 only, but `host.openshell.internal` also resolves to an IPv6
   unique-local address, and OpenShell's SSRF guard checks every answer. Every
   request failed with `allowed_ips check failed`. Fixed by adding `fc00::/7`.
2. **`nemoclaw config set` was unusable.** The config guard loads a pinned JSON5
   parser from `/opt/nemoclaw`, which the filesystem policy did not permit
   reading, so it failed with `json5-validator-failed`. `lab-setup.sh` falls back
   to writing `openclaw.json` directly.
3. **Index builds failed with `unable to open database file`.** SQLite derives
   its temp directory from `TMPDIR`, which is unset in the exec environment.
   Setting `TMPDIR=/tmp` fixes it. The message is misleading: the database
   directory is perfectly writable.

### One schema trap worth internalising

The published NemoClaw page documents `agents.defaults.memorySearch.provider`,
and that is **correct for the OpenClaw 2026.7.1 build NemoClaw pins**. Upstream
`main` has since moved to `memory.search.*`. The config schema is strict, so the
wrong key is *silently ignored* rather than rejected. Always verify with
`openclaw memory status --deep`.

The embedding provider also must use the `openai-completions` adapter, not
`ollama`: the Ollama adapter ignores `baseUrl` and dials `127.0.0.1:11434`,
which does not exist inside the sandbox.

### What is verified vs. assumed

**Independently verified on this machine:**

- Docker Desktop runs a Linux VM with kernel 6.12.76 exposing
  `landlock_create_ruleset` and `landlock_restrict_self` — the primitives
  OpenShell sandboxing depends on.
- The remote Ollama host answers on `your-ollama-host:11434` (Tailscale).
- `qwen3-embedding:4b` is cached and returns **2560-dim** embeddings;
  ~10 GB resident in VRAM on the Windows host's RTX 5070.
- A container can reach the host relay via `host.docker.internal:11434` and get
  real embeddings back — this is the exact path an OpenShell sandbox uses.
- The corpus answers the reference set: **recall@5 = 100%**,
  **answer-in-context = 96.7%**, every question category 6/6.

**Not yet verified (needs a live sandbox once disk is available):**

- The exact memory-search config keys in NemoClaw's pinned OpenClaw build.
- That `openclaw memory index` completes against the relayed Ollama endpoint.
- The fallback index restore path.

---

## Why there is a relay

Two independent constraints force it:

1. OpenShell sandboxes reach host services only as `host.openshell.internal`,
   which maps to the Docker host gateway. NemoClaw's shipped `local-inference`
   policy preset permits that host on port 11434 and pins `allowed_ips` to
   RFC1918 ranges.
2. A Tailscale address lives in `100.64.0.0/10` — CGNAT, **not** RFC1918. It is
   on NemoClaw's SSRF block list, so `config set` rejects it outright, and
   user-authored `allowed_ips` is refused by the policy validator.

So rather than fight the policy engine, a small TCP relay on the lab host
forwards `127.0.0.1:11434` to the remote Ollama. The sandbox then uses the
fully documented path — `http://host.openshell.internal:11434` plus the stock
`local-inference` preset — and nothing about the security model is loosened.

```
  OpenShell sandbox                     lab host                    inference host
  ┌────────────────┐   host.openshell   ┌──────────────┐  tailscale  ┌──────────────┐
  │ openclaw       │──── .internal ────▶│ ollama-relay │────────────▶│ Ollama       │
  │ memory search  │     :11434         │ :11434       │  100.64.x   │ qwen3-embed  │
  └────────────────┘                    └──────────────┘             └──────────────┘
```

At the event, if Ollama runs locally on the DGX Spark, drop the relay with
`--no-relay` and point straight at `127.0.0.1:11434`.

---

## Layout

```
hands-on-2/
├── corpus/                     28 synthetic Aurora Grid Systems documents
├── ingestion/
│   └── build_index.py          heading-aware chunker + embedder (stdlib only)
├── index/
│   ├── rag_index.json          canonical index (82 chunks, dim 2560)
│   ├── manifest.json           corpus hash + model + dim, for drift detection
│   └── fallback/               sandbox index snapshot (written by lab-setup.sh)
├── verification/
│   ├── reference_qa.json       30 questions, answers, exact source strings
│   ├── verify_qa.py            corpus/QA substring integrity check
│   ├── consistency_check.py    cross-document contradiction check
│   ├── evaluate_retrieval.py   retrieval quality gate
│   └── verify_agent.py         queries the live sandbox's memory search
├── scripts/
│   ├── ollama-relay.py         TCP forwarder
│   ├── host-setup.sh           relay + models + preflight
│   └── lab-setup.sh            upload corpus + configure + index + fallback
├── canonical_facts.md          authoring control sheet for the corpus
└── README.md
```

## The corpus

**Aurora Grid Systems (AGS)** — a fictional industrial battery-storage
manufacturer. 28 documents: datasheets, installation and commissioning guides,
maintenance schedules, safety bulletins, firmware release notes, warranty, RMA,
spares, site planning, grid-code notes, glossary, FAQ, escalation matrix.

Difficulty is deliberate, because a corpus where every answer is trivially
retrievable teaches nothing:

- **Confusable pairs.** The AX-400 and AX-600 share spec *names* with divergent
  values (energy, DC voltage, peak power, cooling, IP rating, cold limit,
  torque, clearance) — including one spec that is intentionally identical
  (0.5C) to punish retrieval that keys on the wrong field.
- **Version-specific facts** keyed to Comet C2 firmware 3.7.4 / 3.8.0 / 3.8.1 /
  3.8.2 and Helios H3 4.3.0 / 4.4.1.
- **Superseded facts with effective dates.** SB-2024-03 mandates a 5-minute
  DC-disconnect wait; URGENT SB-2025-01 supersedes it with 12 minutes plus a
  <50 V DC verification. The old value still appears in the corpus, so a
  retriever that ignores dates or status returns a dangerous answer.

## Reference Q&A

30 pairs spanning `disambiguation` (6), `numeric-spec` (6), `version-specific`
(5), `single-hop` (5), `procedure` (4), `superseded` (4). Each carries
`must_contain` strings that must appear verbatim in the corpus, so the answer
key cannot silently drift away from the documents.

Note on how those strings are written: they assert the **fact**, not one
document's phrasing. An earlier revision required `M12 stud, 35 N·m`, which the
installation guide renders as a table row `| AX-600 | M12 stud | 35 N·m |`.
That failed a question whose answer was genuinely present — a defect in the
answer key, not the corpus, and it is why the strings are now split into
`["M12 stud", "35 N·m"]`.

---

## Running the lab

### Pre-event, on the host

```bash
./scripts/host-setup.sh                 # relay + models + preflight
./scripts/host-setup.sh --check-only    # verify without changing anything
./scripts/host-setup.sh --no-relay --ollama-target 127.0.0.1:11434
```

Then onboard NemoClaw and assemble the lab:

```bash
curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash
nemoclaw onboard                        # choose OpenClaw, name it my-assistant
./scripts/lab-setup.sh --sandbox my-assistant
```

On the day, participants need only run the onboarding command; `lab-setup.sh`
has already cached models, uploaded the corpus and built the index.

### Verification gates

Run these in order; each is a release blocker for the next.

```bash
# 1. Answer key matches the corpus (fast, offline)
python3 verification/verify_qa.py

# 2. Corpus is internally consistent (fast, offline)
python3 verification/consistency_check.py

# 3. Retrieval quality — requires the relay or a local Ollama
python3 verification/evaluate_retrieval.py --index index --k 6 --query-prefix qwen3

# 4. The live sandbox answers the reference set
python3 verification/verify_agent.py --sandbox my-assistant
```

Gate 3 currently reports:

```
recall@1             66.7%
recall@3             96.7%
recall@5            100.0%
answer-in-context@5  96.7%
MRR                  0.819
RESULT: PASS
```

### Rebuilding the index

```bash
python3 ingestion/build_index.py --corpus corpus --out index \
  --target-chars 1600 --overlap-chars 320 --base-url http://127.0.0.1:11434
```

`--target-chars 1600` mirrors OpenClaw's own chunker, which is hardcoded to
400 tokens with 80 overlap and **is not configurable**. Matching it keeps this
index a faithful proxy for what the sandbox will build.

---

## Gotchas that will bite you

**The memory-search config key in the published NemoClaw docs is legacy.**
The NemoClaw page shows `agents.defaults.memorySearch.provider`. In current
OpenClaw the live paths are `memory.search.*` and
`agents.entries.<id>.memory.search.*`; the legacy key is only migrated by
`openclaw doctor --fix`, and because the runtime schema is strict a legacy key
can be **silently ignored rather than erroring** — the worst possible failure
mode for a lab. `lab-setup.sh` tries the current key first and verifies with
`openclaw memory status --deep` before falling back.

**Chunking is not tunable.** 400 tokens / 80 overlap are literal constants.
There is no `chunking` key in the schema; the one `openclaw doctor` emits is
rejected by the strict schema and never read. Do not try to configure it.

**Only three locations are indexed:** `<workspace>/MEMORY.md` (must be a real
file, not a symlink), `<workspace>/USER.md`, and `<workspace>/memory/**/*.md`.
The corpus therefore belongs in `memory/`. A file dropped anywhere else in the
workspace is invisible to search.

**The index is identity-bound.** It is SQLite inside
`<stateDir>/agents/<agentId>/agent/openclaw-agent.sqlite` — the same file as
sessions — and it records the provider id, model, endpoint and non-secret
headers. Change any of those and vector search pauses with an identity
mismatch. This is why the fallback index is only restorable onto an identically
configured sandbox; a stale copy is worse than no copy.

**The embedding model is asymmetric.** Ollama's `qwen3-embedding` prepends an
instruction template to *queries* only, never to documents. Reproduce that if
you write your own client, or retrieval quality drops measurably.

**Disk.** Onboarding pulls a sandbox image and will fail without headroom.
`docker system prune --force` reclaims build cache and dangling images;
removing idle images and volumes frees considerably more but deletes work.

---

## Reference questions worth using live

| Category | Question | Watch for |
|---|---|---|
| disambiguation | "What torque do I use on the DC terminals?" | Must give **both** values and bind them to the right cabinet — 25 N·m AX-400, 35 N·m AX-600 |
| superseded | "How long after opening the DC disconnect before I can remove a module cover?" | Correct answer is **12 minutes** (SB-2025-01). A model that surfaces the 5-minute figure from the superseded bulletin is the key teaching moment |
| version-specific | "Which port does the Comet C2 use for Modbus?" | 502 on 3.7.4 and 3.8.2, 1502 on 3.8.0/3.8.1 |
| procedure | "What coolant does the AX-600 take?" | 50/50 propylene glycol / water, 38 L — the AX-400 is air cooled, so this must not generalise |
