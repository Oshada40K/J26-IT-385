# Owner: Dewmi - Component 04.
"""Runs the interactive exercises' code so their answers are checked by execution, not only by structure.

Python: every program runs in ONE separate interpreter (python -I, empty temporary working directory, time limit), each
with its own globals and captured stdout. Its "observed output" is stdout (stripped) or, when it raises, the exception's
type name (e.g. TypeError), which is how the exercises show errors.
SQL: an in-memory sqlite3 database built from the exercise's setup script; result rows are written as
"value, value; value, value" (NULL for None), the format used in the exercise options.
bash / text exercises are not run (see curriculum.RUNNABLE_LANGUAGES); they are reported as checked by structure only.
"""
import itertools
import json
import sqlite3
import subprocess
import sys
import tempfile

from app.component04_roadmap.curriculum import BLANK, RUNNABLE_LANGUAGES

HARNESS = r"""
import contextlib, io, json, sys
results = []
for source in json.load(sys.stdin):
    buffer, error = io.StringIO(), None
    try:
        code = compile(source, "<exercise>", "exec")
        with contextlib.redirect_stdout(buffer):
            exec(code, {"__name__": "__exercise__"})
    except BaseException as exc:
        error = type(exc).__name__
    results.append({"stdout": buffer.getvalue(), "error": error})
sys.__stdout__.write(json.dumps(results))
"""
TIME_LIMIT = 120


def _observed(stdout, error):
    text = stdout.strip()
    if error:
        return f"{text}\n{error}" if text else error
    return text


def run_python(sources):
    """[observed output] for each Python source, all run in one isolated child interpreter."""
    if not sources:
        return []
    with tempfile.TemporaryDirectory() as folder:
        done = subprocess.run([sys.executable, "-I", "-c", HARNESS], input=json.dumps(sources), capture_output=True,
                              text=True, timeout=TIME_LIMIT, cwd=folder)
    if done.returncode != 0:
        raise RuntimeError(f"exercise harness failed: {done.stderr[-2000:]}")
    return [_observed(r["stdout"], r["error"]) for r in json.loads(done.stdout)]


def run_sql(setup, query):
    db = sqlite3.connect(":memory:")
    try:
        db.executescript(setup)
        rows = db.execute(query).fetchall()
    except sqlite3.Error as exc:
        return f"sqlite error: {type(exc).__name__}: {exc}"
    finally:
        db.close()
    return "; ".join(", ".join("NULL" if v is None else str(v) for v in row) for row in rows)


def _python_source(ex, body):
    return f"{ex['setup']}\n{body}" if ex.get("setup") else body


def _compiles(source):
    try:
        compile(source, "<exercise>", "exec")
        return True
    except SyntaxError:
        return False


def is_runnable(ex):
    return ex["language"] in RUNNABLE_LANGUAGES


def verify(ex):
    """Problems found when running the exercise ([] = every answer checked by execution and correct)."""
    language, kind = ex["language"], ex["type"]
    if language not in RUNNABLE_LANGUAGES:
        return []
    problems = []
    if language == "sql":
        run = lambda query: run_sql(ex["setup"], query)
        run_many = lambda queries: [run(q) for q in queries]
    else:
        run_many = lambda bodies: run_python([_python_source(ex, b) for b in bodies])
        run = lambda body: run_many([body])[0]
    if kind == "predict_output":
        got = run(ex["code"])
        if got != ex["options"][ex["answer"]]:
            problems.append(f"marked option {ex['options'][ex['answer']]!r} but the code gives {got!r}")
    elif kind == "fill_blank":
        variants = []
        for answer in ex["answers"]:
            variants.append(answer)
            if ex.get("ignore_case"):          # case-insensitive answers must still be right in any case
                variants += [answer.lower(), answer.upper()]
        outputs = run_many([ex["code"].replace(BLANK, v) for v in variants])
        for variant, got in zip(variants, outputs):
            if got != ex["expected_output"]:
                problems.append(f"accepted answer {variant!r} gives {got!r}, expected {ex['expected_output']!r}")
        blank = run(ex["code"])                 # the unfinished code must not already give the expected output
        if blank == ex["expected_output"]:
            problems.append("the code gives the expected output even with the blank left empty")
    elif kind == "find_bug":
        fixed = list(ex["lines"])
        fixed[ex["answer"]] = ex["fix"]
        original, repaired = run_many(["\n".join(ex["lines"]), "\n".join(fixed)])
        if original == ex["expected_output"]:
            problems.append("the buggy code already gives the expected output, so the marked line is not a bug")
        if repaired != ex["expected_output"]:
            problems.append(f"fixing the marked line gives {repaired!r}, expected {ex['expected_output']!r}")
    else:   # order_steps: the correct order works and no other order gives the same output
        others = [list(p) for p in itertools.permutations(ex["lines"]) if list(p) != ex["lines"]]
        bodies = ["\n".join(p) for p in [ex["lines"]] + others]
        if language == "python":               # orders that do not even compile cannot give the output
            bodies = [bodies[0]] + [b for b in bodies[1:] if _compiles(_python_source(ex, b))]
        outputs = run_many(bodies)
        if outputs[0] != ex["expected_output"]:
            problems.append(f"the correct order gives {outputs[0]!r}, expected {ex['expected_output']!r}")
        clashes = [b for b, got in zip(bodies[1:], outputs[1:]) if got == ex["expected_output"]]
        if clashes:
            problems.append(f"{len(clashes)} other order(s) also give the expected output, e.g. {clashes[0]!r}")
    return problems
