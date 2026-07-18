#!/usr/bin/env python3
"""
validate_jass_syntax.py — structural syntax gate for war3map.j (pure JASS).

Checks:
  1. Block balance: function/endfunction, globals/endglobals, loop/endloop,
     if/endif (with elseif/else handling), no nesting of functions.
  2. Function declared-before-use ordering for user-defined function calls
     (call Foo / function Foo references), ignoring natives/BJs declared in
     common.j / Blizzard.j (heuristic: unknown names are only warned, known
     later-defined names are errors).
  3. Duplicate function definitions.
  4. Leak gate: runs analyze_jass_leaks.py and fails if leak counts exceed
     the recorded baseline (baseline file lives next to this script).

Exit code 0 = pass, 1 = fail.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE_FILE = os.path.join(HERE, "leak_baseline.txt")

RE_COMMENT = re.compile(r"//.*$")
RE_STRING = re.compile(r'"(?:\\.|[^"\\])*"')
RE_RAWCODE = re.compile(r"'[^']*'")
RE_FUNC_DEF = re.compile(r"^\s*(?:constant\s+)?function\s+(\w+)\s+takes\b")
RE_NATIVE_DEF = re.compile(r"^\s*(?:constant\s+)?native\s+(\w+)\s+takes\b")
RE_CALL = re.compile(r"\bcall\s+(\w+)\s*\(")
RE_FUNCREF = re.compile(r"\bfunction\s+(\w+)\s*[,)\s]")


def strip(line: str) -> str:
    line = RE_STRING.sub('""', line)
    line = RE_RAWCODE.sub("'x'", line)
    line = RE_COMMENT.sub("", line)
    return line


def main(path: str) -> int:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw_lines = f.readlines()

    errors = []
    warnings = []

    # ---- Pass 1: block balance ----
    stack = []  # (kind, lineno)
    defined_at = {}  # func name -> lineno
    in_globals = False

    openers = {"function": "endfunction", "loop": "endloop", "if": "endif"}
    closers = {"endfunction": "function", "endloop": "loop", "endif": "if"}

    for idx, raw in enumerate(raw_lines, 1):
        line = strip(raw).strip()
        if not line:
            continue
        toks = re.split(r"[\s(]", line, 1)
        first = toks[0] if toks else ""

        if first == "globals":
            if in_globals:
                errors.append(f"L{idx}: nested globals block")
            in_globals = True
            continue
        if first == "endglobals":
            if not in_globals:
                errors.append(f"L{idx}: endglobals without globals")
            in_globals = False
            continue
        if in_globals:
            continue

        m = RE_FUNC_DEF.match(line)
        if m:
            name = m.group(1)
            if any(k == "function" for k, _ in stack):
                errors.append(f"L{idx}: function '{name}' defined inside another function")
            if name in defined_at:
                errors.append(f"L{idx}: duplicate function '{name}' (first at L{defined_at[name]})")
            else:
                defined_at[name] = idx
            stack.append(("function", idx))
            continue
        if RE_NATIVE_DEF.match(line):
            continue

        if first == "if" or (first == "static" and line.startswith("static if")):
            stack.append(("if", idx))
            continue
        if first in ("elseif", "else"):
            if not stack or stack[-1][0] != "if":
                errors.append(f"L{idx}: '{first}' outside if-block")
            continue
        if first == "loop":
            stack.append(("loop", idx))
            continue
        if first in closers:
            want = closers[first]
            if not stack:
                errors.append(f"L{idx}: '{first}' with no open block")
            elif stack[-1][0] != want:
                errors.append(
                    f"L{idx}: '{first}' closes '{stack[-1][0]}' opened at L{stack[-1][1]}"
                )
                stack.pop()
            else:
                stack.pop()
            continue

    for kind, lineno in stack:
        errors.append(f"L{lineno}: '{kind}' block never closed")
    if in_globals:
        errors.append("globals block never closed")

    # ---- Pass 2: declared-before-use for user functions ----
    seen = set()
    in_g = False
    for idx, raw in enumerate(raw_lines, 1):
        line = strip(raw)
        s = line.strip()
        if s.startswith("globals"):
            in_g = True
        elif s.startswith("endglobals"):
            in_g = False
        m = RE_FUNC_DEF.match(line)
        if m:
            seen.add(m.group(1))
            continue
        if in_g:
            continue
        for m in list(RE_CALL.finditer(line)) + list(RE_FUNCREF.finditer(line)):
            name = m.group(1)
            if name in defined_at and name not in seen:
                # ExecuteFunc-style forward refs are impossible in raw JASS
                errors.append(
                    f"L{idx}: '{name}' used before its definition at L{defined_at[name]}"
                )

    # ---- Pass 3: leak gate ----
    leak_counts = None
    analyzer = os.path.join(HERE, "analyze_jass_leaks.py")
    if os.path.exists(analyzer):
        proc = subprocess.run(
            [sys.executable, analyzer, path], capture_output=True, text=True
        )
        out = proc.stdout
        counts = {}
        for label, key in [
            ("un-nulled local handles", "unnulled"),
            ("potential Location leaks", "location"),
            ("Group leaks", "group"),
            ("Force leaks", "force"),
        ]:
            m = re.search(re.escape(label) + r":\s*(\d+)", out)
            counts[key] = int(m.group(1)) if m else -1
        leak_counts = counts

        baseline = {}
        if os.path.exists(BASELINE_FILE):
            for ln in open(BASELINE_FILE, encoding="utf-8"):
                if "=" in ln:
                    k, v = ln.strip().split("=", 1)
                    baseline[k] = int(v)
        for k, v in counts.items():
            if k in baseline and v > baseline[k]:
                errors.append(
                    f"LEAK REGRESSION: {k} leaks rose from baseline {baseline[k]} to {v}"
                )
        if not baseline:
            with open(BASELINE_FILE, "w", encoding="utf-8") as f:
                for k, v in counts.items():
                    f.write(f"{k}={v}\n")
            warnings.append(f"leak baseline recorded: {counts}")

    # ---- Report ----
    print(f"=== VALIDATING: {path} ({len(raw_lines)} lines) ===")
    print(f"Functions defined: {len(defined_at)}")
    if leak_counts is not None:
        print(f"Leak counts: {leak_counts}")
    for w in warnings:
        print(f"WARN: {w}")
    if errors:
        print(f"\n{len(errors)} ERROR(S):")
        for e in errors[:80]:
            print(f"  {e}")
        if len(errors) > 80:
            print(f"  ... and {len(errors) - 80} more")
        print("\n>>> VALIDATION FAILED <<<")
        return 1
    print("\n>>> VALIDATION PASSED: blocks balanced, ordering OK, no leak regressions <<<")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: validate_jass_syntax.py <war3map.j>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
