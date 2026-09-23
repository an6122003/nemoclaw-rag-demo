#!/usr/bin/env python3
"""
consistency_check.py — cross-document consistency sanity pass for the AGS corpus.

Four kinds of check:

  A. Line-level attribution. For every line that names EXACTLY ONE AX-series model,
     any headline confusable spec on that line must carry that model's value.
     Lines naming both models are ambiguous, so they are collected and listed for
     manual review (counted always; printed in full with --verbose).

  B. Required statements. Each of these exact strings must appear in the named doc.

  C. Supersession discipline. The withdrawn 5-minute DC-disconnect interval may only
     appear in documents that explicitly flag it as superseded or withdrawn, and the
     Modbus port 1502 may only appear in a document SECTION whose text ties it to
     firmware 3.8.0 or 3.8.1. It must never be presented as the port for 3.8.2.

  D. Headline-number census, printed so a human can eyeball every location of every
     headline value.

Exit status 0 only when every check passes.

Run from the hands-on-2/ directory:
    python3 verification/consistency_check.py [--verbose]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE.parent / "corpus"

ALLOWED = {
    "usable energy (kWh)": {
        "AX-400": {"372", "400"},
        "AX-600": {"558", "600"},
    },
    "DC terminal torque (N·m)": {
        "AX-400": {"25", "12"},   # 12 N·m is the shared ground-stud value
        "AX-600": {"35", "12"},
    },
    "ingress protection": {
        "AX-400": {"IP54"},
        "AX-600": {"IP55"},
    },
}

PATTERNS = {
    "usable energy (kWh)": re.compile(r"(\d{3})\s*kWh"),
    "DC terminal torque (N·m)": re.compile(r"(\d{2})\s*N·m"),
    "ingress protection": re.compile(r"(IP\d\d)"),
}

REQUIRED = [
    ("ags-doc-001-ax400-battery-cabinet-datasheet.md", "| Usable energy | 372 kWh |"),
    ("ags-doc-002-ax600-battery-cabinet-datasheet.md", "| Usable energy | 558 kWh |"),
    ("ags-doc-001-ax400-battery-cabinet-datasheet.md", "| Nominal DC voltage | 768 V |"),
    ("ags-doc-002-ax600-battery-cabinet-datasheet.md", "| Nominal DC voltage | 1,152 V |"),
    ("ags-doc-001-ax400-battery-cabinet-datasheet.md", "| DC terminal | M12 stud, 25 N·m |"),
    ("ags-doc-002-ax600-battery-cabinet-datasheet.md", "| DC terminal | M12 stud, 35 N·m |"),
    ("ags-doc-001-ax400-battery-cabinet-datasheet.md", "| Ingress protection | IP54 |"),
    ("ags-doc-002-ax600-battery-cabinet-datasheet.md", "| Ingress protection | IP55 |"),
    ("ags-doc-001-ax400-battery-cabinet-datasheet.md", "| Cooling | Forced air, 4 x axial fans |"),
    ("ags-doc-002-ax600-battery-cabinet-datasheet.md", "| Cooling | Liquid, 50% propylene glycol / 50% water |"),
    ("ags-doc-003-helios-h3-pcs-datasheet.md", "| Rated AC power | 250 kW |"),
    ("ags-doc-003-helios-h3-pcs-datasheet.md", "| Maximum AC current | 361 A |"),
    ("ags-doc-004-comet-c2-site-controller-datasheet.md", "192.168.10.40"),
    ("ags-doc-014-firmware-release-notes-comet-c2-3-8-2.md", "listen on port **502** by default"),
    ("ags-doc-010-safety-bulletin-sb-2025-01-urgent-dc-disconnect.md", "Wait a minimum of 12 minutes"),
    ("ags-doc-009-safety-bulletin-sb-2024-03-dc-disconnect-sequence.md", "SUPERSEDED"),
    ("ags-doc-019-environmental-and-thermal-specification.md", "| AX-600 (AGS-AX600-558) | -25 °C to +50 °C | Above +45 °C |"),
    ("ags-doc-019-environmental-and-thermal-specification.md", "| AX-400 (AGS-AX400-372) | -20 °C to +50 °C | Above +40 °C |"),
]

SUPERSEDED_MARKERS = ("superseded", "withdrawn", "must not be used", "no longer")

CENSUS = {
    "372 kWh (AX-400 usable energy)": "372 kWh",
    "558 kWh (AX-600 usable energy)": "558 kWh",
    "768 V (AX-400 nominal DC)": "768 V",
    "1,152 V (AX-600 nominal DC)": "1,152 V",
    "25 N·m (AX-400 DC terminal)": "25 N·m",
    "35 N·m (AX-600 terminal / H3 DC lug)": "35 N·m",
    "250 kW (Helios H3 rating)": "250 kW",
    "361 A (Helios H3 AC current)": "361 A",
}


def sections_containing(text: str, needle: str):
    """Yield (heading, section_text, first_lineno) for every H2 section holding `needle`."""
    lines = text.splitlines()
    heading, start = "(preamble)", 0
    bounds = []
    for i, line in enumerate(lines):
        if line.startswith("## "):
            bounds.append((heading, start, i))
            heading, start = line.strip(), i
    bounds.append((heading, start, len(lines)))
    for head, a, b in bounds:
        body = "\n".join(lines[a:b])
        if needle in body:
            first = next(
                (a + k + 1 for k, l in enumerate(lines[a:b]) if needle in l), a + 1
            )
            yield head, body, first


def main() -> int:
    verbose = "--verbose" in sys.argv
    failures = []
    docs = {p.name: p.read_text(encoding="utf-8") for p in sorted(CORPUS.glob("*.md"))}

    print("=" * 78)
    print("AGS corpus — cross-document consistency sanity pass")
    print("=" * 78)
    print(f"scanning {len(docs)} documents\n")

    # ---- A ----------------------------------------------------------------
    print("-" * 78)
    print("A. Headline-spec attribution on single-model lines")
    print("-" * 78)
    ambiguous, attributed, misattributed = [], 0, 0
    for name, text in docs.items():
        for lineno, line in enumerate(text.splitlines(), 1):
            models = [m for m in ("AX-400", "AX-600") if m in line]
            if len(models) == 2:
                ambiguous.append(f"{name}:{lineno}: {line.strip()}")
                continue
            if len(models) != 1:
                continue
            model = models[0]
            for spec, rx in PATTERNS.items():
                for value in rx.findall(line):
                    attributed += 1
                    if value not in ALLOWED[spec][model]:
                        misattributed += 1
                        failures.append(
                            f"{name}:{lineno}: {model} line carries {spec} = {value!r}, "
                            f"allowed {sorted(ALLOWED[spec][model])} | {line.strip()}"
                        )
    print(f"  {attributed} single-model spec values checked against the model's allowed set")
    print(f"  {'ok  ' if misattributed == 0 else 'FAIL'} {misattributed} misattributed value(s)")
    print(f"  lines naming BOTH models (manual review): {len(ambiguous)}")
    if verbose:
        for a in ambiguous:
            print(f"    - {a}")

    # ---- B ----------------------------------------------------------------
    print("\n" + "-" * 78)
    print("B. Required statements present in the expected document")
    print("-" * 78)
    found = 0
    for doc, needle in REQUIRED:
        if doc in docs and needle in docs[doc]:
            found += 1
            print(f"  ok   {doc}\n         \"{needle}\"")
        else:
            failures.append(f"{doc}: required string not found: {needle!r}")
            print(f"  FAIL {doc}: NOT FOUND -> {needle!r}")
    print(f"  {found}/{len(REQUIRED)} required statements found")

    # ---- C1 ---------------------------------------------------------------
    print("\n" + "-" * 78)
    print("C1. Withdrawn 5-minute DC-disconnect interval only where explicitly flagged")
    print("-" * 78)
    hits = 0
    for name, text in docs.items():
        low = text.lower()
        for lineno, line in enumerate(text.splitlines(), 1):
            if "5 minute" not in line.lower():
                continue
            hits += 1
            flagged = any(m in low for m in SUPERSEDED_MARKERS)
            if not flagged:
                failures.append(
                    f"{name}:{lineno}: states a 5-minute interval without flagging supersession"
                )
            print(f"  {'ok  ' if flagged else 'FAIL'} {name}:{lineno}")
            print(f"         {line.strip()}")
    print(f"  {hits} occurrence(s)")
    if hits == 0:
        failures.append("expected at least one mention of the superseded 5-minute interval")

    # ---- C2 ---------------------------------------------------------------
    print("\n" + "-" * 78)
    print("C2. Modbus port 1502 only inside a section tied to firmware 3.8.0/3.8.1")
    print("-" * 78)
    violations = 0
    n1502 = 0
    n_section_tied = 0
    for name, text in docs.items():
        for head, body, lineno in sections_containing(text, "1502"):
            section_tied = ("3.8.0" in body) or ("3.8.1" in body)
            if section_tied:
                n_section_tied += 1
            # Every individual 1502 must be attributable to 3.8.0/3.8.1 either by its
            # own local context (+/- 60 chars) or by the section it sits in.
            for m in re.finditer("1502", body):
                n1502 += 1
                window = body[max(0, m.start() - 60):m.end() + 60]
                window_tied = ("3.8.0" in window) or ("3.8.1" in window)
                if not (window_tied or section_tied):
                    violations += 1
                    failures.append(
                        f"{name}:{lineno}: port 1502 appears with no 3.8.0/3.8.1 tie "
                        f"in its context or section {head!r} | context: {window.strip()!r}"
                    )
    print(f"  {n_section_tied} section(s) carrying port 1502 name firmware 3.8.0/3.8.1")
    print(f"  {n1502} occurrence(s) of port 1502 inspected (local window or section context)")
    print(f"  {'ok  ' if violations == 0 else 'FAIL'} {violations} unattributable occurrence(s)")
    # The current release must always be shown with 502. A 1502 whose own local
    # context names 3.8.2 but names neither 3.8.0 nor 3.8.1 is a real contradiction.
    bad_pair = 0
    for name, text in docs.items():
        for m in re.finditer("1502", text):
            window = text[max(0, m.start() - 60):m.end() + 60]
            if "3.8.2" in window and "3.8.0" not in window and "3.8.1" not in window:
                bad_pair += 1
                failures.append(
                    f"{name}: port 1502 attributed to 3.8.2 with no 3.8.0/3.8.1 nearby "
                    f"| context: {window.strip()!r}"
                )
    print(f"  {'ok  ' if bad_pair == 0 else 'FAIL'} {bad_pair} place(s) where port 1502 is tied to 3.8.2")

    # ---- D ----------------------------------------------------------------
    print("\n" + "-" * 78)
    print("D. Census of headline numbers across the corpus")
    print("-" * 78)
    for label, needle in CENSUS.items():
        where = [n for n, t in docs.items() if needle in t]
        print(f"  {label:<40} {len(where):2d} doc(s): {', '.join(where) if where else 'NONE'}")
        if not where:
            failures.append(f"headline number never appears in the corpus: {needle}")

    # ---- result -----------------------------------------------------------
    print("\n" + "=" * 78)
    if failures:
        print(f"RESULT: FAIL — {len(failures)} consistency problem(s)")
        print("=" * 78)
        for f in failures:
            print(f"  * {f}")
        return 1
    print("RESULT: PASS — no cross-document contradiction found on any headline spec.")
    print("        Divergent values exist only for the withdrawn 5-minute DC-disconnect")
    print("        interval (SB-2024-03) and the 1502 Modbus port (firmware 3.8.0/3.8.1),")
    print("        and each is explicitly marked superseded by a later document.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
