#!/usr/bin/env python3
"""Static audit of an LLM agent repo. Stdlib only.

Heuristics: the report is a list of numbers to look at, not a verdict.
With --ci the exit code is 1 when a hard limit is crossed.

Usage:
  python audit_agent.py REPO [--prompt FILE ...] [--journal FILE.jsonl]
                             [--max-prompt-chars 8000] [--allow-framework NAME ...] [--ci]
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

CODE_EXT = {".py", ".ts", ".tsx", ".js", ".mjs"}
# .claude holds vendored skills (including this script); scanning them flags the skill's own examples
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".mypy_cache", ".claude"}

FRAMEWORKS = {
    "langchain": r"(from|import)\s+langchain|@langchain/",
    "langgraph": r"(from|import)\s+langgraph|@langchain/langgraph",
    "crewai": r"(from|import)\s+crewai",
    "llama_index": r"(from|import)\s+llama_index",
    "autogen": r"(from|import)\s+autogen",
    "haystack": r"(from|import)\s+haystack",
    "semantic_kernel": r"(from|import)\s+semantic_kernel",
}
LICENSE_FLAGS = {
    "ultralytics (AGPL-3.0 unless Enterprise licence)": r"(from|import)\s+ultralytics|['\"]ultralytics['\"]",
}
STRICT_OFF = re.compile(r"strict['\"]?\s*[:=]\s*(False|false)")
REGEX = re.compile(r"\bre\.compile\(|new RegExp\(")
# branching prose in prompts; Ukrainian words are needed to scan Ukrainian-language prompts
CONDITIONAL = re.compile(
    r"\b(if|otherwise|unless|first\b.{0,40}\bthen|якщо|інакше|коли\b.{0,40}\bто|спочатку\b.{0,60}\bпотім)\b",
    re.IGNORECASE,
)
CONST_DEF = re.compile(r"^\s*([A-Z][A-Z0-9_]{3,})\s*(?::[^=]+)?=", re.MULTILINE)
PROMPT_NAME = re.compile(r"prompt", re.IGNORECASE)
MAX_EMPTY_SHARE = 0.1  # journal: allowed share of events with an empty cost/ms/tokens/model field


def iter_files(root: Path):
    for p in root.rglob("*"):
        if p.is_file() and not any(part in SKIP_DIRS for part in p.parts):
            yield p


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def audit(root: Path, prompts: list[Path], journal: Path | None, args) -> tuple[list[str], list[str]]:
    report, hard = [], []
    code = {p: read(p) for p in iter_files(root) if p.suffix in CODE_EXT}

    # Rule 4: prompt size and branching prose
    if not prompts:
        prompts = [p for p in iter_files(root) if PROMPT_NAME.search(p.name) and p.suffix in {".md", ".txt"}]
    report.append("## Prompts (rule 4)")
    if not prompts:
        report.append("- no prompt files found; pass --prompt if the prompt lives in code")
    for p in prompts:
        text = read(p)
        n, cond = len(text), len(CONDITIONAL.findall(text))
        report.append(f"- {p}: {n} chars, {cond} conditional phrases")
        if n > args.max_prompt_chars:
            hard.append(f"prompt {p} is {n} chars > {args.max_prompt_chars}")

    # Rule 10: frameworks
    report.append("\n## Frameworks (rule 10)")
    found = Counter()
    for p, t in code.items():
        for name, pat in FRAMEWORKS.items():
            if re.search(pat, t):
                found[name] += 1
    for f in (root / "package.json", root / "pyproject.toml", root / "requirements.txt"):
        t = read(f) if f.exists() else ""
        for name in FRAMEWORKS:
            if name.replace("_", "-") in t or name in t:
                found[name] += 1
    if not found:
        report.append("- none")
    for name, n in found.items():
        allowed = name in args.allow_framework
        report.append(f"- {name}: {n} files/manifests{' (allowed)' if allowed else ''}")
        if not allowed:
            hard.append(f"framework {name} without a reason in the decision card")

    # Rule 3: strict and regex
    report.append("\n## Structured output and regex (rule 3)")
    strict_off = [(p, len(STRICT_OFF.findall(t))) for p, t in code.items() if STRICT_OFF.search(t)]
    for p, n in strict_off:
        report.append(f"- strict disabled {n}x in {p}")
        hard.append(f"strict disabled in {p}")
    rx = sorted(((len(REGEX.findall(t)), p) for p, t in code.items() if REGEX.search(t)), reverse=True)
    report.append(f"- regex compiles total: {sum(n for n, _ in rx)}")
    for n, p in rx[:5]:
        report.append(f"  - {n} in {p}")

    # Rule 13: constants defined but never used
    report.append("\n## Constants never referenced (rule 13)")
    all_text = "\n".join(code.values())
    unused = []
    for p, t in code.items():
        if p.suffix != ".py":
            continue
        for name in set(CONST_DEF.findall(t)):
            if len(re.findall(rf"\b{name}\b", all_text)) == 1:
                unused.append(f"{name} ({p})")
    report.extend(f"- {u}" for u in unused[:30]) if unused else report.append("- none")

    # Rule 7: licences
    report.append("\n## Licences to resolve before handover (rule 7)")
    lic = [label for label, pat in LICENSE_FLAGS.items() if any(re.search(pat, t) for t in code.values())]
    report.extend(f"- {l}" for l in lic) if lic else report.append("- nothing flagged (weights still need a manual check)")

    # Rule 14: CI
    report.append("\n## CI (rule 14)")
    wf = list((root / ".github" / "workflows").glob("*.y*ml")) if (root / ".github").exists() else []
    if not wf:
        report.append("- no GitHub workflows found")
        hard.append("no CI workflow")
    for w in wf:
        t = read(w)
        branches = [re.sub(r"[\s\[\]-]+", " ", b).strip()
                    for b in re.findall(r"branches:\s*(\[[^\]]*\]|(?:\n\s*-\s*\S+)+)", t)]
        report.append(f"- {w.name}: branches {branches or 'not filtered'} (must include the branch you merge and deploy)")

    # Rule 12: journal
    if journal:
        report.append("\n## Journal (rule 12)")
        rows, nulls = 0, Counter()
        for line in read(journal).splitlines():
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows += 1
            for k in ("cost_usd", "ms", "tokens_in", "model"):
                if ev.get(k) in (None, 0):
                    nulls[k] += 1
        report.append(f"- events: {rows}")
        for k in ("cost_usd", "ms", "tokens_in", "model"):
            share = nulls[k] / rows if rows else 0
            report.append(f"- {k} null/zero: {nulls[k]} ({share:.0%})")
            # more than one event in ten without the field means the field is not wired, not an occasional gap
            if rows and share > MAX_EMPTY_SHARE:
                hard.append(f"journal field {k} empty in {share:.0%} of events")

    report.append("\n## Manual checks (script cannot see)")
    report += [
        "- raw ids visible to the LLM in tool results (rule 5)",
        "- prose rules in the prompt duplicating code (M1)",
        "- escalation delivery confirmed and user informed (rule 11)",
        "- one writer per state flag (rule 9)",
        "- no post-generation code edits, erases or holds reply text (rule 18)",
        "- photo verdict persisted in state and enforced on the reply (rule 19)",
        "- no caption/social-media price reaches a slot (rule 20)",
    ]
    return report, hard


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    ap.add_argument("--prompt", type=Path, action="append", default=[])
    ap.add_argument("--journal", type=Path)
    # 8000: the rewritten reference agent works at ~8 000 characters; its collapsed predecessor was at 50 000
    ap.add_argument("--max-prompt-chars", type=int, default=8000)
    ap.add_argument("--allow-framework", action="append", default=[])
    ap.add_argument("--ci", action="store_true")
    args = ap.parse_args()

    report, hard = audit(args.repo, args.prompt, args.journal, args)
    print("# Agent audit\n")
    print("\n".join(report))
    print("\n## Hard limits crossed")
    print("\n".join(f"- {h}" for h in hard) if hard else "- none")
    sys.exit(1 if args.ci and hard else 0)


if __name__ == "__main__":
    main()
