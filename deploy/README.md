# DGX Spark / Linux deployment bundle

Everything needed to stand the lab up on the event host, with no dependency on
the Mac used to author it.

## Transfer

```bash
# from the authoring machine
tar --exclude='.run' -czf hands-on-2.tar.gz hands-on-2/

# on the DGX Spark
tar -xzf hands-on-2.tar.gz
cd hands-on-2
```

The bundle is self-contained: corpus, index, answer key, scripts and
verification harnesses. The only large artifacts it does *not* carry are the
model weights, which the script pulls from the model registry.

## Provision

```bash
./deploy/dgx-spark-setup.sh                     # local Ollama, full run
./deploy/dgx-spark-setup.sh --stage preflight   # check the host first
./deploy/dgx-spark-setup.sh --gateway-port 8814 # if 8080 is taken
./deploy/dgx-spark-setup.sh --inference managed-vllm  # use the Spark's GPU
```

Stages run in order and can be resumed individually:
`preflight → models → install → onboard → lab → verify`.

## Why the embedding model is separate from the chat model

NemoClaw manages the **chat** model. It does not manage an embedding server, and
OpenClaw's memory search needs one. On a DGX Spark you can serve chat with
managed vLLM or NIM on the GPU while Ollama serves embeddings — or run both on
Ollama. `--inference` selects the former; the embedding model is pulled either
way.

## Before the session

```bash
python3 verification/verify_qa.py            # answer key matches the corpus
python3 verification/consistency_check.py    # corpus has no contradictions
python3 verification/evaluate_retrieval.py --k 6 --query-prefix qwen3
python3 verification/verify_agent.py --sandbox my-assistant
```

The first two are offline and must pass. The third needs a reachable Ollama. The
fourth is the real gate: it asks all 30 reference questions of the live sandbox.

## Verify host egress before anything else

```bash
./scripts/fix-sandbox-policy.sh --sandbox my-assistant
```

That script repairs the two OpenShell sandbox-policy defects that block the lab
on a fresh install (IPv6 host-gateway egress, and `/opt` readability for the
config guard). Run it before `lab-setup.sh`; `lab-setup.sh` also invokes it
automatically if egress is closed.

Manual equivalent:

```bash
nemoclaw my-assistant exec -- curl -fsS http://host.openshell.internal:11434/api/tags
```

If that returns the model list, the embedding path is open. If it returns
`{"error":"ssrf_denied", ...}`, read [../docs/SANDBOX-NOTES.md](../docs/SANDBOX-NOTES.md)
for the root cause and the fix.

## Known environment requirement

Set `TMPDIR` for any memory operation:

```bash
nemoclaw my-assistant exec -- env TMPDIR=/tmp openclaw memory index --force
```

Without it, index builds fail with the misleading
`unable to open database file`. Both `lab-setup.sh` and `verify_agent.py` handle
this for you.

## Event-day participant experience

Participants run one command:

```bash
nemoclaw onboard
```

Everything else — models cached, corpus uploaded, index built, fallback index
stored — has already been done by this bundle. See
[../docs/PARTICIPANT.md](../docs/PARTICIPANT.md) for their worksheet.
