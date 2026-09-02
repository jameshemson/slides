#!/usr/bin/env python3
"""Static guard for a deck build script — run before `node`.

    python3 check_script.py <deck>.build.cjs

A deck script is model-authored code executed on the user's machine, so its
boundary is declared and enforced twice: here, statically, and in the craft
reference by construction (content lives in one JSON block). The script may
require only the tokens module (by the one idiom), Node's "path" and
"pptxgenjs"; it may not spawn processes, reach the network, evaluate strings,
import dynamically, read the environment, or touch the filesystem beyond the
--out write pptxgenjs performs. Comments are not exempt: a forbidden token in
a comment is refused too, so the file reads the same to a person and to this
guard.
"""
import argparse
import re
import sys

ALLOWED_REQUIRES = ("path", "pptxgenjs")
TOKENS_IDIOM = 'require(require("path").resolve(tokensPath))'
FORBIDDEN = (
    ("child_process", "child processes are not allowed"),
    ("eval(", "eval is not allowed"),
    ("new Function(", "new Function is not allowed"),
    ("import(", "dynamic import is not allowed"),
    ("process.env", "the environment is not readable"),
    ("fetch(", "network access is not allowed"),
    ("XMLHttpRequest", "network access is not allowed"),
    ("WebSocket", "network access is not allowed"),
    ("spawn", "child processes are not allowed"),
    ("execSync", "child processes are not allowed"),
)
_REQUIRE_RE = re.compile(r"require\(\s*(?P<arg>[^)]*?)\s*\)")
_LITERAL_RE = re.compile(r"""^(['"])(?P<name>[^'"]*)\1$""")


CONTENT_BLOCK_PREFIX = "const C = JSON.parse("


def check(source_text):
    """Return the gate's messages; an empty list means nothing to fix before running.

    This is a usability gate, not the boundary: the boundary is Node's
    permission model (`node --permission` with the two allowlists), which
    build-deck applies to every run. The gate names the common mistakes early
    with a clear fix. The content-block line is skipped: it is data and may
    contain anything.
    """
    messages = []
    for number, line in enumerate(source_text.splitlines(), 1):
        if line.strip().startswith(CONTENT_BLOCK_PREFIX):
            continue
        scan = line.replace(TOKENS_IDIOM, "") if TOKENS_IDIOM in line else line
        for match in _REQUIRE_RE.finditer(scan):
            arg = match.group("arg").strip()
            literal = _LITERAL_RE.match(arg)
            if literal is None:
                messages.append(
                    f"line {number}: dynamic require is not allowed; "
                    f"use const T = {TOKENS_IDIOM}"
                )
                continue
            name = literal.group("name")
            if name == "fs":
                messages.append(
                    f"line {number}: require('fs') is not allowed; the filesystem is "
                    f"written only by pptxgenjs writeFile"
                )
            elif name not in ALLOWED_REQUIRES:
                messages.append(
                    f"line {number}: require('{name}') is not allowed; a deck script may "
                    f'require only the tokens module, "path" and "pptxgenjs"'
                )
        for token, why in FORBIDDEN:
            if token in line:
                messages.append(f"line {number}: {token!r} — {why}")
    return messages


def main(argv=None):
    parser = argparse.ArgumentParser(description="Static guard for a deck build script.")
    parser.add_argument("script", help="the <deck>.build.cjs to check")
    args = parser.parse_args(argv)
    try:
        with open(args.script, encoding="utf-8") as fh:
            source = fh.read()
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    messages = check(source)
    for message in messages:
        print(message)
    if messages:
        print(f"script: {len(messages)} violation(s)")
        return 1
    print("script: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
