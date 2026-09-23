# Hands-on 2 — Build RAG and Deploy as a Local Agent with NemoClaw

**Participant worksheet.** You will take a corpus of technical documents, turn
it into a searchable vector index using a local embedding model, and query it
through an agent running inside a sandboxed NemoClaw deployment.

Everything runs locally. No document and no query leaves the machine.

---

## What you will end up with

```
documents ──▶ chunking ──▶ embeddings ──▶ vector index ──▶ agent answers
  28 files      400 tokens   2560-dim      SQLite + vec0      with citations
```

---

## 0. Confirm your environment

Your machine has already been prepared: the sandbox exists, the embedding model
is cached, and the corpus is in place. Confirm the sandbox is healthy.

```bash
nemoclaw my-assistant status
```

You are looking for the sandbox to report itself running with an inference
route. If it does not, stop here and tell the facilitator — do not debug the
sandbox during the session.

```bash
nemoclaw my-assistant dashboard-url --quiet
```

Open the printed URL, or work in the terminal:

```bash
nemoclaw launch my-assistant
```

---

## 1. Meet the corpus

The corpus is **Aurora Grid Systems** (AGS), a fictional manufacturer of
industrial battery energy storage systems. 28 documents: datasheets,
installation guides, maintenance schedules, safety bulletins, firmware release
notes, warranty, RMA procedure, spares catalogue, site planning, grid-code
notes, glossary, FAQ.

```bash
ls hands-on-2-rag/corpus/
```

### Why this corpus and not something friendlier

A corpus where every answer appears once, verbatim, teaches nothing. This one
contains three deliberate traps, and the rest of the lab is about watching the
agent fall into them or avoid them.

**Trap 1 — confusable products.** The AX-400 and AX-600 share spec *names* but
not values:

| | AX-400 | AX-600 |
|---|---|---|
| Usable energy | 372 kWh | 558 kWh |
| Nominal DC bus | 768 V | 1,152 V |
| Peak discharge | 260 kW for 10 s | 390 kW for 30 s |
| Cooling | Forced air, 4 fans | Liquid, 50/50 glycol |
| Ingress rating | IP54 | IP55 |
| Cold limit | −20 °C | −25 °C |
| DC lug torque | 25 N·m | 35 N·m |

They even share one value on purpose — both are rated **0.5C** — so a retriever
that keys on the wrong field can still look plausible.

**Trap 2 — superseded safety facts.** SB-2024-03 told technicians to wait
**5 minutes** after opening the DC disconnect. URGENT SB-2025-01 superseded it
with **12 minutes** plus a <50 V DC verification. Both documents are in the
corpus. Only one is current.

**Trap 3 — version-specific behaviour.** The Comet C2 controller's Modbus port
is 502 on firmware 3.7.4 and 3.8.2, but 1502 on 3.8.0 and 3.8.1.

---

## 2. Watch the ingestion happen

OpenClaw indexes exactly three locations in the agent workspace:
`MEMORY.md`, `USER.md`, and everything under `memory/`. Your corpus lives under
`memory/`.

Confirm the documents are visible to the sandbox:

```bash
nemoclaw my-assistant exec -- ls "$HOME/.openclaw/workspace/memory" | head
```

You should see the 28 `.md` files.

### Look at how it chunks

Chunking is **not configurable** in OpenClaw — it is hardcoded to 400 tokens
with 80 tokens of overlap. You can reproduce the same behaviour with the
reference implementation in this repo:

```bash
python3 hands-on-2-rag/ingestion/build_index.py --corpus hands-on-2-rag/corpus \
  --out /tmp/my-index --target-chars 1600 --overlap-chars 320
```

While it runs, note what it prints: 28 documents become ~82 chunks. Ask
yourself: *what would happen if chunks were much larger? Much smaller?*

- **Too large** → the answer is diluted among unrelated text, and one verbose
  document crowds out the exact source.
- **Too small** → a single sentence gets isolated, and the retriever cannot tell
  what section it belonged to.

This is why each chunk carries its heading breadcrumb (`Document — Section`)
and the document title in the text that actually gets embedded.

### Then build the real index

```bash
nemoclaw my-assistant exec -- env TMPDIR=/tmp openclaw memory index --force
nemoclaw my-assistant exec -- env TMPDIR=/tmp openclaw memory status --index
```

Read the status output carefully. Three lines matter:

- **Indexed** — how many files and chunks were embedded
- **Vector dims** — should be **2560** for `qwen3-embedding:4b`
- **Index identity** / **Vector search** — must not report a mismatch

---

## 3. Ask the agent

Start with something simple, to confirm retrieval works at all:

> What is the usable energy of the AX-600?

Expected: **558 kWh**. If the agent says 372 kWh it has retrieved the sibling
document and confused the two products.

---

## 4. Exercises

These are the questions worth spending time on. For each, note *what the agent
retrieved*, not just what it answered. A correct answer from the wrong document
is a warning sign.

### Exercise A — disambiguation

> What torque do I use on the DC terminals?

A good answer gives **both** values and binds them correctly: **25 N·m** on the
AX-400 and **35 N·m** on the AX-600. An answer that gives a single number
without saying which cabinet it belongs to is dangerous in the real world.

> Which cabinet is liquid cooled, and what coolant does it take?

Expected: AX-600, **50/50 propylene glycol / water, 38 L**. The AX-400 is air
cooled — if the agent says the AX-400 is liquid cooled, retrieval crossed the
wires.

### Exercise B — the superseded fact

> How long after opening the DC disconnect must I wait before removing a module
> access cover?

This is the most important question in the lab.

- **Correct:** 12 minutes, per SB-2025-01, plus verify the DC link is below 50 V.
- **Wrong but understandable:** 5 minutes, from SB-2024-03.
- **Best:** 12 minutes, *and* the agent notes that the 5-minute figure comes from
  a superseded bulletin.

Both documents are in the corpus. A vector index retrieves by similarity, and
"5 minutes" and "12 minutes" are equally similar to the question. Correctness
here comes from the agent noticing dates and status, not from retrieval alone.
This is the central lesson: **RAG retrieves plausible text, not true text.**

### Exercise C — version specificity

> Which port does the Comet C2 use for Modbus?

Expected: **502** for 3.7.4 and 3.8.2, **1502** for 3.8.0 and 3.8.1. An
unqualified single answer is incomplete — the question is underspecified and a
good agent should say so.

> What changed about Aggressive Rebalance in firmware 3.8.2?

Expected: it was **deprecated and disabled** in 3.8.2.

### Exercise D — procedures

> What is the coolant filter part number, and how much coolant does the system
> hold?

Expected: **AGS-FILT-6603**, **38 L**.

> What insulation resistance must be verified before energisation?

Expected: **1 MΩ or greater at 1,000 V DC**.

---

## 5. Break it — find the limits

Understanding failure modes is the point of the exercise. Try these.

**Ask something not in the corpus.**

> What is Aurora Grid Systems' share price?

A good agent says it does not know. An agent that invents a number has a
grounding problem, and you should not trust its other answers.

**Ask for a fact that exists in two conflicting documents** and see whether the
agent notices the conflict or silently picks one.

**Ask a question that requires combining three documents.**

> If I have an AX-600 and one Helios H3, can I use all 558 kWh at full power?

This needs the AX-600 peak power (390 kW), the Helios H3 continuous rating
(250 kW) and its DC interface limit (260 kW) — and the H3 datasheet states an
AX-600 "requires two H3 units operating in parallel". This is where multi-hop
retrieval either works or visibly does not.

---

## 6. Verify your work

The repository ships a reference answer key and automated checks.

Check that the answer key still matches the corpus:

```bash
python3 hands-on-2-rag/verification/verify_qa.py
```

Check the corpus does not contradict itself:

```bash
python3 hands-on-2-rag/verification/consistency_check.py
```

Check retrieval quality end to end, through the sandbox's own memory search:

```bash
python3 hands-on-2-rag/verification/verify_agent.py --sandbox my-assistant
```

This asks all 30 reference questions of the live sandbox and reports a pass
rate. It grades **retrieval** — whether the expected answer text was returned —
rather than the model's phrasing, because retrieval is deterministic and is what
you are actually validating.

---

## 7. What you should take away

1. **Chunking decides what is findable.** Retrieval quality is mostly a corpus
   and chunking problem, not a model problem.
2. **Similarity is not truth.** The superseded safety bulletin is exactly as
   retrievable as the current one. Grounding requires the agent to reason about
   dates, status and provenance.
3. **Embeddings are asymmetric.** Query text and document text are not
   interchangeable; the model was trained with an instruction prefix on queries
   only. Getting this wrong measurably degrades retrieval.
4. **A sandbox is what makes a local agent safe to leave running.** The agent
   has filesystem access and can install its own skills. OpenShell enforces
   policy outside the agent's process, so a compromised or confused agent cannot
   rewrite its own guardrails.

---

## Troubleshooting

**`openclaw memory search` returns nothing.**
Check the index first: `openclaw memory status --index`. If it reports an
identity mismatch, the embedding provider settings changed since the index was
built. Rebuild with `openclaw memory index --force` rather than copying a stale
database.

**Embeddings fail with a connection error.**
The sandbox reaches the embedding server through the host gateway. From inside
the sandbox: `curl -fsS http://host.openshell.internal:11434/api/tags`. If that
fails, the host relay has stopped — ask the facilitator.

**Vector dims are not 2560.**
The configured embedding model is not `qwen3-embedding:4b`.

**The agent answers from a document you did not expect.**
That is a result, not a bug. Note which document it used and why — that is the
lesson.
