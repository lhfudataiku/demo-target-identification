"""Execute one repository assertion script inside DSS and fail loudly if it went stale.

WHY THIS EXISTS. The assertion logic used to exist in three places: the DSS Jupyter notebooks, the
`notebooks/*.py` scripts in the repository, and inline copies pasted into the `validate_notebooks`
scenario steps. `tools/pull_notebooks.py` records what that cost -- on 2026-08-25 all five copies had
diverged in both directions, and `.index/assertions.tsv` counts expectations from the REPOSITORY
copy, so the index was describing scripts that were not the ones being run.

This module makes the repository copy the only copy. The scripts are synced here verbatim from
`notebooks/`, and each scenario step is two lines that call `run()`.

THE FAILURE CONTRACT, which is the reason a plain exec is not enough. Six of the seven scripts only
*print* their stale count -- `print(f"SUMMARY|{len(FAIL)} STALE")` -- and then end. Run as-is, a
scenario step would print the staleness and still report SUCCESS: a green scenario over stale
numbers, which is the failure this whole index exists to prevent. Only nb6 raises. So the contract
lives here rather than in the scripts: `run()` inspects the script's own `FAIL` list after execution
and raises if it is non-empty. The scripts are not edited -- they are the assertion source of truth,
and rewriting their tails would risk changing the very text and values the index parses.
"""
import io
import os
import contextlib

HERE = os.path.dirname(os.path.abspath(__file__))


def run(name):
    """Execute `<name>.py` and raise AssertionError if any check() is stale."""
    path = os.path.join(HERE, name + ".py")
    if not os.path.exists(path):
        raise RuntimeError("no assertion script at %s" % path)
    with open(path, encoding="utf-8") as handle:
        src = handle.read()

    # exec, not import: a second run in the same process would be a silent no-op under
    # import caching, and a fresh namespace is what lets FAIL be inspected afterwards.
    ns = {"__name__": "__main__", "__file__": path}
    buf = io.StringIO()
    exited = None
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(src, path, "exec"), ns)
    except SystemExit as exc:          # nb6 ends with raise SystemExit on stale
        exited = exc
    finally:
        out = buf.getvalue()
        print(out, end="" if out.endswith("\n") else "\n")

    checks = out.count("CHK|")
    fail = ns.get("FAIL")
    if fail is None:
        raise RuntimeError(
            "%s defines no FAIL list -- it is not an assertion script, or its shape changed" % name)

    print("ASSERT|%s|checks_executed=%d|stale=%d" % (name, checks, len(fail)))
    for item in fail:
        print("STALE|%s|%s" % (name, item))

    if fail:
        raise AssertionError("%s: %d stale assertion(s)" % (name, len(fail)))
    if exited is not None and exited.code not in (None, 0):
        raise AssertionError("%s exited non-zero: %s" % (name, exited.code))
    if checks == 0:
        raise RuntimeError("%s executed zero checks -- it ran but asserted nothing" % name)
    return checks
