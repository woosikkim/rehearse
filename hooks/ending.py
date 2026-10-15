"""The ending: schema, citations, evaluation, and which tests make the baseline (plan 2.5)."""
import json
import os
import re

import provenance

CHECKS = ("equals", "contains", "regex", "exit_code", "fixture_equals")


def cited_text(cite, sources):
    """The text a citation points at, or None. sources: request (str), steps {S<n>: out}, fixtures {name: text}."""
    cite = str(cite or "")
    if cite == "request":
        return sources.get("request") or ""
    if cite.startswith("step:"):
        return sources.get("steps", {}).get(cite[5:])
    if cite.startswith("fixture:"):
        return sources.get("fixtures", {}).get(cite[8:])
    return None


def validate(expectations, sources):
    """A list of problems; empty when every expectation is well formed and its literal is in the cited text."""
    problems = []
    if not expectations:
        return ["an ending needs at least one --expect"]
    for e in expectations:
        what = "%r (%s %r)" % (e.get("requirement"), e.get("check"), e.get("value"))
        check, value = e.get("check"), str(e.get("value"))
        if check not in CHECKS:
            problems.append("%s: check must be one of %s" % (what, ", ".join(CHECKS)))
            continue
        text = cited_text(e.get("cite"), sources)
        if text is None:
            problems.append("%s: citation %r is not a plugin-written fixture, a logged step or the request"
                            % (what, e.get("cite")))
            continue
        if check == "regex":
            try:
                ok = re.search(value, text) is not None
            except re.error as x:
                problems.append("%s: bad regex: %s" % (what, x))
                continue
        elif check == "fixture_equals":
            ok = value in sources.get("fixtures", {})
        elif check == "exit_code":
            ok = re.fullmatch(r"-?\d+", value) is not None
        else:
            ok = value in text
        if not ok:
            problems.append("%s: the value does not appear in %s" % (what, e.get("cite")))
    return problems


def evaluate(expectations, rc, stdout, stderr, fixtures):
    """One result per expectation. fixtures: the run's fixtures folder."""
    both = (stdout or "") + "\n" + (stderr or "")
    results = []
    for e in expectations:
        check, value = e.get("check"), str(e.get("value"))
        try:
            if check == "equals":
                ok = (stdout or "").strip() == value.strip()
            elif check == "contains":
                ok = value in both
            elif check == "regex":
                ok = re.search(value, both) is not None
            elif check == "exit_code":
                ok = rc is not None and rc == int(value)
            elif check == "fixture_equals":
                with open(os.path.join(fixtures, os.path.basename(value)), encoding="utf-8", errors="replace") as f:
                    ok = (stdout or "").strip() == f.read().strip()
            else:
                ok = False
        except (OSError, ValueError, re.error):
            ok = False
        results.append({"requirement": e.get("requirement"), "check": check, "value": value, "passed": ok})
    return results


def interpreter(root):
    for rel in (".venv/bin/python", "venv/bin/python"):
        if os.path.exists(os.path.join(root, rel)):
            return os.path.join(root, rel)
    if os.environ.get("CONDA_PREFIX") and os.path.exists(os.path.join(os.environ["CONDA_PREFIX"], "bin", "python")):
        return os.path.join(os.environ["CONDA_PREFIX"], "bin", "python")
    return "python3"


def _has_pytest_config(root):
    def has(name, marker):
        try:
            with open(os.path.join(root, name), encoding="utf-8", errors="replace") as f:
                return marker in f.read()
        except OSError:
            return False
    return (os.path.exists(os.path.join(root, "pytest.ini")) or os.path.exists(os.path.join(root, "conftest.py"))
            or has("pyproject.toml", "[tool.pytest") or has("setup.cfg", "[tool:pytest]") or has("tox.ini", "[pytest]"))


def relevant_tests(cmd, tests, root):
    """The relevant tests command (plan section 1), or None when the project has none."""
    if tests:
        return tests
    if any(s["runner"] for s in provenance.parse(cmd, root)):
        return cmd
    if _has_pytest_config(root) or os.path.isdir(os.path.join(root, "tests")):
        return "%s -m pytest" % interpreter(root)
    try:
        with open(os.path.join(root, "package.json"), encoding="utf-8") as f:
            if (json.load(f).get("scripts") or {}).get("test"):
                return "npm test"
    except (OSError, ValueError, AttributeError):
        pass
    if os.path.exists(os.path.join(root, "go.mod")):
        return "go test ./..."
    if os.path.exists(os.path.join(root, "Cargo.toml")):
        return "cargo test"
    return None


def could_not_start(rc, output):
    """'no baseline: <first error line>' when a test command never got to run a test, else None."""
    if rc == 127 or re.search(r"No module named|errors? during collection|ImportError while", output) \
            or (rc in (2, 3, 4) and "pytest" in output.lower()):
        lines = [ln.strip() for ln in output.splitlines() if ln.strip()]
        first = next((ln for ln in lines if re.search(r"error|not found|No module", ln, re.I)), lines[0] if lines else "")
        return "no baseline: " + first[:300]
    return None
