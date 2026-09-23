# Sandbox findings — three defects, their root causes, and the fixes

Recorded against a real run: macOS 26.5 / Apple M5 / Docker Desktop 4.76,
NemoClaw `v0.0.124`, OpenShell `0.0.116`, OpenClaw `2026.7.1`, sandbox
`my-assistant`, gateway port 8814.

The lab works end to end. It did not work out of the box. Each defect below was
reproduced from a clean install, diagnosed to root cause, and is now repaired
automatically by `scripts/fix-sandbox-policy.sh` and `scripts/lab-setup.sh`.

Final state:

```
Indexed: 28/28 files · 76 chunks
Embeddings: ready
Vector dims: 2560
Vector store: ready
passed 30/30 (100.0%) — sandbox retrieval answers the reference set
```

---

## Defect 1 — sandbox could not reach the host at all

**Symptom**

```bash
$ nemoclaw my-assistant exec -- curl -s http://host.openshell.internal:11434/api/version
{"detail":"GET host.openshell.internal:11434 blocked: allowed_ips check failed",
 "error":"ssrf_denied"}
```

**Root cause.** The shipped `local-inference` preset allow-lists
`host.openshell.internal` with IPv4 RFC1918 ranges only. On Docker Desktop the
sandbox `/etc/hosts` maps that name to **two** addresses:

```
192.168.65.254        host.openshell.internal
fdc4:f303:9324::254   host.openshell.internal
```

OpenShell's SSRF guard resolves the name and checks *every* answer against the
endpoint's `allowed_ips`. The IPv6 unique-local answer is not in an IPv4-only
list, so the request is denied. Forcing `curl -4` does not help: the guard
evaluates the name, not the connection.

**Fix.** Add `fc00::/7` (IPv6 unique-local) to `allowed_ips`.

**Trap:** do **not** also add `fe80::/10`. The schema rejects link-local ranges
at load time and the entire policy becomes invalid:

```
{"detail":"... blocked: invalid allowed_ips in policy","error":"ssrf_denied"}
```

**Trap:** corrected presets do not apply through NemoClaw. `nemoclaw policy add
--from-file` reports:

```
Could not confirm the policy update ... OpenShell did not confirm the policy
submission. The current live policy differs from the requested document; the
update remains unconfirmed.
```

and the preset never appears in `policy list`. Driving OpenShell's own CLI works:

```bash
openshell policy set --policy <full-document.json> --wait --timeout 120 my-assistant
```

`policy set` **replaces** the whole document, so read the live policy with
`openshell policy get <sandbox> --full -o json`, patch it, and write the complete
document back. YAML parsers accept JSON, so the JSON dump can be fed straight to
`--policy`.

---

## Defect 2 — `nemoclaw config set` was unusable

**Symptom.** Every config write failed:

```
OpenClaw config schema validation timed out or was terminated; existing config
was not changed.
{"code":"json5-validator-failed","detail":"fixed JSON5 validator failed to run"}
```

**Root cause.** NemoClaw's config guard validates `openclaw.json` with a pinned
JSON5 parser. Its paths are hardcoded in
`/usr/local/lib/nemoclaw/openclaw-config-guard.py`:

```python
JSON5_MODULE_PATH = "/opt/nemoclaw/node_modules/json5"
```

`/opt` was **absent from the filesystem policy's `read_only` allowlist**, so the
sandbox could not read the parser:

```bash
$ ls /opt/nemoclaw/node_modules/json5
Permission denied          # directories are mode 755 root:root — this is Landlock, not Unix perms
```

**Fix.** Add `/opt` to `filesystem_policy.read_only`.

**Note:** adding `/opt` to the policy did not by itself restore readability for
the already-running sandbox in this build. `lab-setup.sh` therefore does not
depend on it: when `config set` cannot verify, it downloads `openclaw.json`,
patches it, and uploads it back. That path is reliable and is the one the lab
script uses.

---

## Defect 3 — index builds failed with a misleading SQLite error

**Symptom**

```bash
$ openclaw memory index --force
[memory] embeddings: batch completed      # embeddings work fine
Memory index failed (main): unable to open database file
```

**Root cause.** SQLite derives its temporary directory from `TMPDIR`, which is
unset in the `nemoclaw exec` environment. `SQLITE_CANTOPEN` surfaces as
"unable to open database file", which points at the database — but the database
directory is writable, `sqlite3` can create and write files there, and WAL mode
works. The message is simply wrong about what failed.

**Fix.** Set `TMPDIR` explicitly:

```bash
TMPDIR=/tmp openclaw memory index --force
# -> Memory index updated (main).
```

Both `lab-setup.sh` and `verify_agent.py` now pass `TMPDIR=/tmp` through
`nemoclaw exec -- env TMPDIR=/tmp ...`.

---

## Two schema traps that silently produce a broken lab

**1. The config key depends on the OpenClaw version.** The published NemoClaw
memory-search page documents `agents.defaults.memorySearch.provider`. That is
**correct for OpenClaw 2026.7.1**, the build NemoClaw pins in its sandbox image —
confirmed against `openclaw config schema`, which exposes
`agents.defaults.memorySearch` and has no `memory.search`. Upstream `main` has
since moved to `memory.search.*`.

The schema is strict and strict means **the wrong key is silently ignored, not
rejected**. A lab built from the upstream key would appear to configure cleanly
and then retrieve nothing. Always confirm with:

```bash
nemoclaw my-assistant exec -- env TMPDIR=/tmp openclaw memory status --deep
```

**2. The embedding provider needs the right adapter.** With `api: "ollama"` the
provider reported:

```
Embeddings error: fetch failed | connect ECONNREFUSED 127.0.0.1:11434
```

The Ollama adapter ignores `baseUrl` and dials loopback. Use the
OpenAI-compatible adapter against Ollama's `/v1` surface instead:

```json
{
  "api": "openai-completions",
  "baseUrl": "http://host.openshell.internal:11434/v1",
  "apiKey": "ollama",
  "models": [{ "id": "qwen3-embedding:4b", "name": "Qwen3 embedding 4B" }]
}
```

---

## A verification trap worth avoiding

`openclaw memory search --json` returns a **truncated `snippet`** alongside the
chunk's true `startLine`/`endLine`. Checking answer strings against the snippet
reports failures for answers that are plainly inside the retrieved chunk — it
scored 16/30 on a pipeline that is actually 30/30.

`verify_agent.py` therefore reads the returned line ranges out of the local
corpus rather than trusting the snippet:

```python
lo = max(1, h["start"]); hi = min(len(lines), h["end"])
parts.append("\n".join(lines[lo - 1 : hi]))
```

---

## Environment changes made during this run

Recorded so they can be reverted.

| Change | Detail |
|---|---|
| Docker Desktop RAM | 2048 → **9216 MiB** (NemoClaw needs ≥ 8 GiB; 8192 reported only 7.75 GiB) |
| Docker Desktop CPUs | 2 → **4** |
| Settings backup | `.run/settings-store.json.backup` |
| Gateway port | default 8080 was taken by `pawcast-api-app-1`, so NemoClaw uses **8814** |
| Docker context | left as `desktop-linux`; the installer was given `DOCKER_CONTEXT=default` |
| Containers | the 5 `pawcast` containers were stopped and restarted twice, coming back healthy |
| Policies | `local-inference`, `github`, plus the two repairs above (policy version 11) |
| Homebrew | developer mode enabled by the OpenShell tap; `brew developer off` to revert |
| Host relay | `scripts/ollama-relay.py` on 127.0.0.1:11434 → `your-ollama-host:11434` |

The gateway runs on port 8814 and owns a separate state root at
`~/.nemoclaw/gateways/8814/`. To remove everything:

```bash
NEMOCLAW_GATEWAY_PORT=8814 nemoclaw uninstall
```

To stop the relay:

```bash
kill "$(cat .run/relay.pid)" 2>/dev/null || pkill -f ollama-relay.py
```

---

## Recovery caveat — do not kill the gateway casually

This one cost several hours and is unresolved, so it is written down as a
hazard rather than a fix.

**Never run a broad `pkill` matching `nemoclaw` or `openshell` on a host with a
registered sandbox.** The OpenShell gateway process matches those patterns. On
the authoring machine this stopped the gateway mid-operation, and recovery never
fully succeeded.

### What breaks

The gateway owns the sandbox registry. When it dies, the registry entry is lost,
but the sandbox container still exists and still expects to be registered. On
its next start it asks the gateway for its own policy and is refused:

```
INFO  openshell_sandbox: Starting sandbox
INFO  openshell_sandbox: Fetching sandbox policy via gRPC
WARN  openshell_sandbox: Policy fetch failed, retrying
Error:   × Policy fetch failed after 5 attempts: code: 'Some requested entity was
  │ not found', message: "sandbox not found"
```

The container then exits (code 1), and the gateway reports:

```
$ openshell sandbox list
No sandboxes found.
```

### What does not recover it

Tried, in order, all unsuccessful:

| Attempt | Result |
|---|---|
| Restart the gateway by hand (`openshell-gateway --config … --port 8814`) | Gateway comes up healthy, but with an empty registry |
| `docker start <sandbox container>` | Container starts, then exits 1 on the policy fetch |
| `nemoclaw <sandbox> start` | Hangs |
| `nemoclaw <sandbox> recover` | Hangs with no output |
| `nemoclaw <sandbox> status` / `exec` | Hang |
| `nemoclaw onboard --resume` | "No resumable onboarding session was found." |
| `nemoclaw onboard` (plain) | Hangs polling `ListSandboxes` indefinitely |
| `nemoclaw onboard --fresh` | Same hang |
| Delete the stale container, then `onboard` | Same hang |

**Unresolved.** On a lab host, treat the sandbox as disposable: if you corrupt
it, destroy and recreate rather than repairing. `nemoclaw <sandbox> destroy`
followed by a full `onboard` is the honest recommendation, though it was not
verified here either.

### A related trap: the host lock

Every `nemoclaw` invocation takes a host-wide lock at
`~/.nemoclaw-portable-host.lock`. Two things go wrong with it:

```
Error: Failed to acquire lock on ~/.nemoclaw-portable-host.lock after 120 retries
```

1. **The lock can be stale.** The directory contains an `owner` file holding a
   PID. If that PID is dead, the lock is orphaned and every command fails after
   120 retries. Check and clear it:

   ```bash
   cat ~/.nemoclaw-portable-host.lock/owner          # the holder's pid
   ps -p "$(cat ~/.nemoclaw-portable-host.lock/owner)" # alive?
   rm -rf ~/.nemoclaw-portable-host.lock             # if dead
   ```

2. **A killed shell can leave the real process running.** Running a `nemoclaw`
   command with `cmd & sleep 20; kill $!` kills the shell wrapper but *not* the
   `node` process underneath, which keeps the lock forever. Kill the node PID
   itself. This is exactly how the stale lock above was created here.

### Practical rule for lab hosts

- Use `nemoclaw <sandbox> stop`, `destroy`, or the documented commands — never
  `pkill` on a pattern that can match the gateway.
- If the gateway must be restarted, note that it is launched as
  `openshell-gateway --config <state-dir>/openshell-gateway.toml --name <name>
  --port <port>`. The port is **not** in the TOML; without `--port` it defaults
  to 17670 and the sandbox will never find it.
- Recovery from a lost registry is unsolved. Prefer recreate.

---

## DGX Spark / Linux — what differs from the Mac, and what the scripts do about it

These come from NemoClaw v0.0.124's own source and documentation (read on the
authoring machine), not from a run on a Spark. They explain design decisions in
`setup.sh` and `scripts/`.

**Ollama stays on loopback.** On non-WSL Linux, NemoClaw binds Ollama to
`127.0.0.1:11434` and starts a token-gated reverse proxy on `0.0.0.0:11435`;
the sandbox's chat traffic goes `inference.local` → OpenShell L7 proxy (which
injects the token) → `:11435` → Ollama. If Ollama is found on a non-loopback
address, onboarding restarts it on loopback. `setup.sh` therefore writes
`OLLAMA_HOST=127.0.0.1:11434` itself.

**Memory search cannot reach loopback.** OpenClaw memory search (Lab 2) calls
an embedding endpoint from inside the sandbox container, which cannot see the
host's `127.0.0.1`. `scripts/embed-proxy.py` listens on the address the sandbox
resolves `host.openshell.internal` to (found with `getent` inside the sandbox)
and forwards only embedding endpoints for the configured model. The stock
`local-inference` preset already allows `host.openshell.internal:11434` with the
RFC 1918 `allowed_ips` the SSRF guard requires, so no policy changes.

**Stop the proxy while onboarding.** Non-interactive onboarding without
passwordless sudo verifies that every listener on port 11434 is loopback-only.
`setup.sh` stops the proxy before `nemoclaw onboard` and starts it afterwards;
do the same if you re-onboard by hand.

**Context length.** NemoClaw writes an `OLLAMA_CONTEXT_LENGTH` floor into its
systemd drop-in and keeps any higher existing value. `setup.sh` sets 32768 in
`/etc/systemd/system/ollama.service.d/zz-workshop.conf` (sorted last, so it
wins). OpenClaw's agent prompt plus tool definitions needs far more than
Ollama's small default; with too little, prompts are silently truncated.

**A host firewall can block the bridge.** If `ufw` is active, allow the
OpenShell Docker network to reach both ports:

```bash
SUBNET=$(docker network inspect openshell-docker --format '{{(index .IPAM.Config 0).Subnet}}')
sudo ufw allow from "$SUBNET" to any port 11435 proto tcp
sudo ufw allow from "$SUBNET" to any port 11434 proto tcp
```

**Editing `openclaw.json` directly.** The sandbox uses NemoClaw's mutable config
layout: `/sandbox/.openclaw/openclaw.json` is sandbox-owned and NemoClaw keeps a
`.config-hash` next to it. NemoClaw's own config writer recomputes it with
`sha256sum openclaw.json > .config-hash`; both sandbox scripts do the same after
a direct write, then `nemoclaw <sandbox> gateway restart`. Edits survive a
sandbox restart. A `rebuild` or a re-onboard with `--recreate-sandbox` starts
from a fresh config, so re-run `bash setup.sh` afterwards.

**Extra agents get their own workspace.** For every `agents.list[].workspace`
of the form `/sandbox/.openclaw/workspace-<id>`, the sandbox entrypoint
provisions the directory on start. The Lab 3 agent lives in
`/sandbox/.openclaw/workspace-analyst`, with `AGENTS.md` uploaded there.

**The OpenAI-compatible endpoint is off by default.** Lab 3 enables
`gateway.http.endpoints.chatCompletions.enabled`. Treat the gateway token as
full operator access: it stays on the host (`.run/gateway-token`, mode 600) and
the gateway itself is only forwarded to `127.0.0.1`.
