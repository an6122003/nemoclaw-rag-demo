# Ask Aurora Grid — GUI demo (EN / VI)

A one-page interface for showing the RAG pipeline to a **non-technical**
audience, in **English or Vietnamese**.

One search box, plain-language answers, a visible source list, a browsable
document library, and a **live view of the pipeline** as it runs.

```bash
./demo/start.sh          # then open http://127.0.0.1:8090/
```

---

## What the audience sees

**A language toggle (EN / VI)** in the top right. Switching it translates the
whole interface *and* the example questions, and the model answering in
Vietnamese will reply in Vietnamese while reading English documents.

**A live pipeline panel.** When you ask a question, the page shows each stage
completing as it actually happens — not a timer:

| Stage | Shown as |
|---|---|
| 1 | Searching all 28 documents |
| 2 | Found N relevant sections · completed in Xs |
| 3 | *(the retrieved passages appear immediately, before the answer)* |
| 4 | Writing the answer |
| 5 | Done in Xs |

Stages are streamed from the server as they complete, so what the audience sees
is real. Sources appear *before* the answer is written, which makes the point
that retrieval happens first and generation is constrained by it.

**A source list** under every answer: numbered cards with a relevance bar.
Click any row to expand the exact passage the answer was based on. This is what
makes it credible — anyone can generate fluent text, showing the receipt is the
point.

**A document library.** Every document the assistant may read, with a preview of
each. Click one to read it in full. It sets the boundary of what the system can
know, so questions outside it visibly have nowhere to come from.

---

## The demo script (about four minutes)

### 1. It just works

> What is the usable energy of the AX-600 battery cabinet?

**558 kWh**, cited to the datasheet.

### 2. It separates two nearly identical products

> What torque do I use on the DC terminals?

**25 N·m on the AX-400 and 35 N·m on the AX-600.** Both cabinets share a spec
*table layout* but not values, and one spec is deliberately identical on both to
punish sloppy matching.

### 3. The centrepiece — it knows what is out of date

> How long after opening the DC disconnect must I wait before removing a module cover?

**12 minutes, per SB-2025-01**, and it says the older **5-minute** interval is
withdrawn. Both bulletins are in the library and are equally similar to the
question. Expand source #1 to show the withdrawn instruction sitting right there
in the results.

Say: *"This is the hard part. Finding similar text is easy. Knowing which text
is still true is the actual problem."*

### 4. It refuses to guess

> What is your share price today?

*"The documents do not cover this question."*

It could have invented a number.

### Vietnamese run

Switch to **VI** and ask the same questions. Note the deliberate detail: the
documents are English, the answer is Vietnamese. Numbers, units and part numbers
stay in English (558 kWh, 35 N·m) because that is how engineers read them.

---

## Running it

| Command | Effect |
|---|---|
| `./demo/start.sh` | preflight, warm the model, open the browser |
| `python3 demo/server.py --port 8090 --open` | the same, manually |
| `--retrieval sandbox` | always use the NemoClaw sandbox |
| `--retrieval local` | skip the sandbox; faster, needs only the model relay |
| `--retrieval auto` | sandbox first, local fallback *(default)* |

**Timing.** About 7 seconds per answer, with the pipeline panel narrating the
wait. With `--retrieval local` there is no sandbox round-trip, so it is the
snappiest option.

**Warm-up.** The model unloads from memory after a few idle minutes, so the
first question after a break is slower. The server warms it at startup; ask one
throwaway question before the audience arrives.

---

## If something breaks

The server degrades instead of erroring. If the sandbox is unreachable it falls
back to the local index; if the model is unreachable the page says so.

| Symptom | Fix |
|---|---|
| Page will not load | `pgrep -fl demo/server.py`; restart |
| "could not reach the document index" | the model relay is down — see below |
| Model dot is grey | start the relay: `python3 scripts/ollama-relay.py --target <host>:11434` |
| Sandbox path is slow | it is timing out; use `--retrieval local`, or repair the sandbox |
| Answers are wrong | check `openclaw memory status --deep` reports `Embeddings: ready` |

---

## Current environment note

As of this writing the demo runs against the **local index** (`--retrieval
local`), because the OpenShell gateway was stopped and its sandbox registration
was lost. The local index holds the same corpus with the same embedding model, so
answers and sources are identical; only the retrieval route differs.

To restore the sandbox path:

```bash
export NEMOCLAW_GATEWAY_PORT=8814
nemoclaw onboard --name my-assistant --non-interactive --yes-i-accept-third-party-software
./scripts/lab-setup.sh --sandbox my-assistant
```

`lab-setup.sh` re-uploads the corpus and rebuilds the index; both fixes in
`scripts/fix-sandbox-policy.sh` are re-applied automatically if needed. Once
it reports `Embeddings: ready`, run the demo without `--retrieval local`.

---

## Files

| File | Purpose |
|---|---|
| `server.py` | stdlib-only HTTP server: retrieval, generation, streaming, library |
| `index.html` | the interface; self-contained, no CDN, works offline |
| `start.sh` | launcher with preflight checks and warm-up |

### API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | relay + sandbox status, document count |
| `GET /api/examples` | demo questions, both languages |
| `GET /api/corpus` | all documents with previews |
| `GET /api/doc?name=…` | one document in full |
| `POST /api/ask` | question → answer + sources (JSON) |
| `POST /api/ask/stream` | the same, streaming each stage as it completes |

---

## Why not OpenClaw's built-in Control UI?

OpenClaw ships its own browser UI, and it is a legitimate question whether this
custom page is needed at all. It is — for this audience. The evaluation is
recorded here so the decision does not have to be made twice.

**What OpenClaw provides.** A Vite + Lit single-page app served by the Gateway at
`http://127.0.0.1:18789/`, speaking to the Gateway over WebSocket. Present in the
sandbox image at
`/usr/local/lib/nemoclaw/openclaw-runtime/node_modules/openclaw/dist/control-ui/`
alongside `docs/web/{control-ui,dashboard}.md`. It is a real PWA, not a stub.

**OpenClaw's own documentation calls it an admin surface:**

> The Control UI is an **admin surface** (chat, config, exec approvals). Do not
> expose it publicly.

Its summary is "chat, activity, nodes, config" — written for someone operating
the agent, not for an audience watching a demonstration.

| | This page | OpenClaw Control UI |
|---|---|---|
| EN / VI interface toggle | Yes, whole interface | **No i18n — English chrome only** |
| Click-to-ask demo questions | Curated, grouped, includes the trap questions | Presenter types every question |
| "Where this came from" | Numbered cards, relevance bars, expandable passage | Tool-call / activity output |
| Document library | All 28 documents, previewable | Not present |
| Surface shown to the audience | One search box | Sessions, config, nodes, exec approvals |

The deciding factor is the **"Where this came from" panel**. For a
non-technical audience, showing the source is what separates this from a chatbot
that might be inventing things. In the Control UI the same information is
present but rendered as tool-call plumbing, which reads as developer machinery.

The second factor is **Vietnamese**. OpenClaw's UI has no i18n. The *answer*
still comes back in Vietnamese because that is driven by the system prompt, but
every label and button around it stays English — which undercuts the point of
the VI version.

**Recommendation: use both, for different jobs.** Keep this page for the demo
itself. Then, if you want a credibility beat, open the Control UI briefly and
say *"this is the real agent underneath — same session, same tools."* That buys
the authenticity without asking a non-technical audience to read a config panel.

```bash
nemoclaw my-assistant dashboard-url --quiet    # authenticated URL
# or simply open http://127.0.0.1:18789/
```

**Auth note:** the Control UI authenticates over the WebSocket handshake. A new
browser normally needs a one-time device pairing
(`openclaw devices list` / `openclaw devices approve <requestId>`), but direct
loopback connections from `127.0.0.1` or `localhost` are auto-approved — so when
the presenter runs the browser on the lab host itself, there is no pairing step.

**Not verified live.** The sandbox registry on the authoring machine was lost
before this could be opened in a browser. The description above comes from the
shipped binary and OpenClaw's own documentation, not from clicking through it.
