#!/usr/bin/env python3
"""Compute the release version from the LaTeX version macros.

Reads \\<prefix>major, \\<prefix>minor and the *optional* \\<prefix>patch, then
prints "Major.Minor[.Patch]".

The release time-stamp is deliberately NOT part of this string: it is appended
by the CI workflow at release time, so that two commits that both forget to
bump the version still yield two distinct releases instead of a tag clash.
See https://github.com/andreaomicini/beamer-AMSBolognaFC/issues/2

Usage:  compute-version.py [FILE]      (reads stdin when FILE is omitted)
"""
import re
import sys

PREFIX = "style"


def macro_re(name):
    return re.compile(
        r"\\newcommand\s*\{\s*\\" + re.escape(name) + r"\s*\}\s*\{([^}]*)\}"
    )


def read_macro(text, name):
    match = macro_re(name).search(text)
    return match.group(1).strip() if match else None


def strip_comments(text):
    """Drop whole-line LaTeX comments, so a commented-out macro really is absent."""
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("%")
    )


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as source:
            text = source.read()
    else:
        text = sys.stdin.read()

    text = strip_comments(text)

    major = read_macro(text, PREFIX + "major")
    minor = read_macro(text, PREFIX + "minor")
    patch = read_macro(text, PREFIX + "patch")  # optional

    if major is None or minor is None:
        sys.exit(
            f"error: could not find \\{PREFIX}major / \\{PREFIX}minor macros"
        )

    print(".".join(part for part in (major, minor, patch) if part is not None))


if __name__ == "__main__":
    main()
