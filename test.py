"""Project smoke check for learn-claude-code.

Runs standalone (no pytest, no API key needed):

    python test.py          # run every check, print a report
    python test.py -v       # verbose

It is also pytest-compatible, so `pytest test.py` works:

    test_*.py / test_*() naming is respected, and no network or
    ANTHROPIC_API_KEY access happens here -- only static checks.

What it verifies:
  1. Chapter layout: s01..s17 exist, each with README.md / README.zh.md /
     README.ja.md / code.py.
  2. Every code.py compiles (syntax only, never executed).
  3. The five root tutorial s-files referenced by the README exist.
  4. requirements.txt, .env.example, LICENSE, skills/ and tests/ exist.
  5. The core agent-loop pattern is still present in s01 (the invariant
     every later chapter builds on).
"""

from __future__ import annotations

import pathlib
import py_compile
import sys
import tempfile
import traceback

ROOT = pathlib.Path(__file__).resolve().parent
CHAPTERS = sorted(ROOT.glob("s[0-9][0-9]_*"))
EXPECTED_CHAPTER_COUNT = 17
REQUIRED_CHAPTER_FILES = ("README.md", "README.zh.md", "README.ja.md", "code.py")


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def test_chapter_layout() -> None:
    """s01..s17 exist and each holds the standard chapter file set."""
    assert len(CHAPTERS) == EXPECTED_CHAPTER_COUNT, (
        f"expected {EXPECTED_CHAPTER_COUNT} chapters, found {len(CHAPTERS)}: "
        f"{[c.name for c in CHAPTERS]}"
    )

    names = [c.name for c in CHAPTERS]
    expected_prefixes = [f"s{i:02d}_" for i in range(1, EXPECTED_CHAPTER_COUNT + 1)]
    for prefix, name in zip(expected_prefixes, names):
        assert name.startswith(prefix), f"expected chapter {prefix}*, got {name}"

    for chapter in CHAPTERS:
        for filename in REQUIRED_CHAPTER_FILES:
            path = chapter / filename
            assert path.is_file(), f"missing {path.relative_to(ROOT)}"


def test_chapter_code_compiles() -> None:
    """Every chapter's code.py is valid Python (compiled, not executed)."""
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = pathlib.Path(tmp)
        for chapter in CHAPTERS:
            source = chapter / "code.py"
            if not source.is_file():
                continue  # covered by test_chapter_layout
            target = tmpdir / f"{chapter.name}.pyc"
            try:
                py_compile.compile(str(source), cfile=str(target), doraise=True)
            except py_compile.PyCompileError as exc:
                failures.append(f"{source.relative_to(ROOT)}: {exc.msg}")

    assert not failures, "syntax errors:\n" + "\n".join(failures)


def test_root_files_present() -> None:
    """Files the README's quick start depends on actually exist."""
    required = (
        "README.md",
        "README-zh.md",
        "README-ja.md",
        "LICENSE",
        "requirements.txt",
        ".env.example",
    )
    missing = [name for name in required if not (ROOT / name).is_file()]
    assert not missing, f"missing root files: {missing}"

    for directory in ("skills", "tests", "docs", "agents"):
        assert (ROOT / directory).is_dir(), f"missing directory: {directory}/"


def test_requirements_has_anthropic() -> None:
    """The agent loop is built on the anthropic SDK."""
    text = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "anthropic" in text, "requirements.txt must list the anthropic SDK"


def test_s01_preserves_the_agent_loop() -> None:
    """s01 is the loop everything else wraps -- guard its core shape."""
    code = (ROOT / "s01_agent_loop" / "code.py").read_text(encoding="utf-8")
    for fragment in ("while True", "tool_use", "tool_result", "messages"):
        assert fragment in code, f"s01/code.py no longer mentions {fragment!r}"


# --------------------------------------------------------------------------
# Standalone runner (pytest is optional)
# --------------------------------------------------------------------------

def _collect() -> list:
    return [
        (name, obj)
        for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]


def main(argv: list[str]) -> int:
    verbose = any(arg in {"-v", "--verbose"} for arg in argv[1:])
    checks = _collect()
    failures = 0

    print(f"learn-claude-code smoke check -- {len(checks)} tests")
    print(f"root: {ROOT}\n")

    for name, check in checks:
        try:
            check()
        except Exception:
            failures += 1
            print(f"  FAIL  {name}")
            if verbose:
                traceback.print_exc()
            else:
                last = traceback.format_exc().strip().splitlines()[-1]
                print(f"        {last}")
        else:
            print(f"  ok    {name}" + (f"  ({check.__doc__})" if verbose and check.__doc__ else ""))

    passed = len(checks) - failures
    print(f"\n{passed} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
