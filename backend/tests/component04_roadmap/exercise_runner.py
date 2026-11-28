# Owner: Dewmi - Component 04.
"""Runs the interactive exercises' code so their answers are checked by execution, not only by structure.

Python: every program runs in ONE separate interpreter (python -I, empty temporary working directory, time limit), each
with its own globals and captured stdout. Its "observed output" is stdout (stripped) or, when it raises, the exception's
type name (e.g. TypeError), which is how the exercises show errors.
SQL: an in-memory sqlite3 database built from the exercise's setup script; result rows are written as
"value, value; value, value" (NULL for None), the format used in the exercise options.
JavaScript: every program runs as its own `node` process (empty temporary folder, time limit) as a CommonJS script, so
plain browser-style code behaves as in a <script>; uncaught errors (also in callbacks and rejected promises) end it and
are shown by the error's class name (TypeError). When the exercise's setup starts with "// file: name.mjs", it is an ES
module: setup is saved as name.mjs and the program as main.mjs, which imports it (the student sees both).
Java: all programs of one check run in ONE JVM (JavaExerciseRunner.java, compiled in memory with javax.tools). A program
without "static void main" is a snippet: it runs inside Main.main, after java.util / java.util.function /
java.util.stream imports, with the exercise's setup (helper classes, records, interfaces) placed before class Main.
Uncaught exceptions are shown by their simple name (ArithmeticException); code that does not compile by "compile error".
Drafted with an AI assistant, checked by the curriculum validator and tests, and reviewed by the C4 author (JavaScript/Java).
bash / text / html / css exercises are not run (see curriculum.RUNNABLE_LANGUAGES); they are reported as checked by structure
only. node and java must be installed for the JavaScript and Java checks; missing_tool() names a missing one so tests can skip.
"""
import base64
import itertools
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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


TOOLS = {"javascript": ("node",), "java": ("java", "javac")}     # javac: the JDK compiler that the Java runner needs
JAVA_RUNNER = Path(__file__).resolve().parent / "JavaExerciseRunner.java"
JAVA_IMPORTS = "import java.util.*;\nimport java.util.function.*;\nimport java.util.stream.*;\n"
MODULE_MARK = "// file: "
MODULE_NAME = re.compile(r"(?:\./)?([A-Za-z0-9_-]+\.mjs)")
NODE_HARNESS = r"""
const fs = require('fs');
const { pathToFileURL } = require('url');
const [program, errorFile] = process.argv.slice(2);
const fail = (e) => {
  fs.writeFileSync(errorFile, String((e && e.constructor && e.constructor.name) || (e && e.name) || 'Error'));
  process.exit(0);
};
process.on('uncaughtException', fail);
process.on('unhandledRejection', fail);
if (program.endsWith('.mjs')) import(pathToFileURL(program).href).catch(fail);
else { try { require(program); } catch (e) { fail(e); } }
"""


def missing_tool(language):
    """The name of a program the language's checks need but that is not installed, or None."""
    return next((tool for tool in TOOLS.get(language, ()) if shutil.which(tool) is None), None)


def _clean(text):
    return text.replace("\r\n", "\n").strip()


def _run_node(files):
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        for name, source in files.items():
            (root / name).write_text(source, encoding="utf-8")
        (root / "harness.cjs").write_text(NODE_HARNESS, encoding="utf-8")
        main = "main.mjs" if "main.mjs" in files else "main.cjs"
        with open(root / "stdout.txt", "w+", encoding="utf-8") as out:
            subprocess.run(["node", "harness.cjs", str(root / main), str(root / "error.txt")], stdout=out,
                           stderr=subprocess.DEVNULL, cwd=folder, timeout=TIME_LIMIT)
            out.seek(0)
            stdout = out.read()
        error_file = root / "error.txt"
        error = error_file.read_text(encoding="utf-8") if error_file.exists() else None
    return _observed(_clean(stdout), error)


def run_javascript(programs):
    """[observed output] for each program ({file name: source}), each in its own node process (8 at a time)."""
    if missing_tool("javascript"):
        raise RuntimeError("not verified: node not installed")
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(_run_node, programs))


def run_java(sources):
    """[observed output] for each complete Java source (entry class Main), all run in one JVM."""
    if missing_tool("java"):
        raise RuntimeError("not verified: java not installed")
    if not sources:
        return []
    lines = "\n".join(base64.b64encode(s.encode("utf-8")).decode("ascii") for s in sources) + "\n"
    with tempfile.TemporaryDirectory() as folder:
        done = subprocess.run(["java", str(JAVA_RUNNER)], input=lines, capture_output=True, text=True,
                              timeout=TIME_LIMIT * 3, cwd=folder)
    if done.returncode != 0:
        raise RuntimeError(f"java exercise runner failed: {done.stderr[-2000:]}")
    results = [base64.b64decode(x).decode("utf-8") for x in done.stdout.split()]
    if len(results) != len(sources):
        raise RuntimeError(f"java exercise runner returned {len(results)} results for {len(sources)} programs")
    return results


def js_program(ex, body):
    """{file name: source} for one JavaScript program of the exercise (see the module docstring)."""
    setup = ex.get("setup")
    if setup and setup.startswith(MODULE_MARK):
        found = MODULE_NAME.fullmatch(setup.splitlines()[0][len(MODULE_MARK):].strip())
        if not found:
            raise ValueError(f"{ex['id']}: module setup must start with '// file: ./name.mjs'")
        return {"main.mjs": body, found.group(1): setup}
    return {"main.cjs": f"{setup}\n{body}" if setup else body}


def java_source(ex, body):
    """A complete Java source for one program of the exercise (see the module docstring)."""
    if "static void main" in body:
        return f"{ex['setup']}\n{body}" if ex.get("setup") else body
    return (f"{JAVA_IMPORTS}{ex.get('setup', '')}\npublic class Main {{\n"
            f"    public static void main(String[] args) throws Exception {{\n{body}\n    }}\n}}\n")


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
        run_many = lambda queries: [run_sql(ex["setup"], q) for q in queries]
    elif language == "javascript":
        run_many = lambda bodies: run_javascript([js_program(ex, b) for b in bodies])
    elif language == "java":
        run_many = lambda bodies: run_java([java_source(ex, b) for b in bodies])
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
