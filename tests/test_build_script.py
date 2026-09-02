"""End-to-end tests for the composition-by-code path.

emit_tokens → check_script → node --permission (the sandbox) → lint_pptx →
stamp → deck_to_spec --against, beneath a package.json that declares
"type": "module" (so the .cjs contract is proven against that failure mode).
Needs Node 22+ and pptxgenjs 4.0.1, resolved from <repo>/.build/runtime
(`npm install --prefix .build/runtime pptxgenjs@4.0.1`) or from NODE_PATH;
skips otherwise, so CI (no npm packages) stays green.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(REPO_ROOT, "source", "skills", "build-deck", "scripts")
SOURCE_DIR = os.path.join(REPO_ROOT, "source")
EXAMPLE = os.path.join(REPO_ROOT, "source", "skills", "build-deck", "reference", "example.build.cjs")
SAMPLE_SPEC = os.path.join(REPO_ROOT, "tests", "fixtures", "sample-deck.md")
RUNTIME = os.path.join(REPO_ROOT, ".build", "runtime")
RUNTIME_MODULES = os.path.join(RUNTIME, "node_modules")
sys.path.insert(0, SCRIPTS)

from pptx import Presentation  # noqa: E402

BRAND = {
    "fidelity": "brand",
    "fonts": {"heading": "Georgia", "body": "Calibri"},
    "colours": {
        "accent": "#4F81BD",
        "accent2": "#C0504D",
        "ink": "#101010",
        "paper": "#FFFFFF",
    },
}
SCALE = {96.0, 60.0, 40.0, 24.0, 16.0}


def _env():
    env = dict(os.environ)
    if os.path.isdir(RUNTIME_MODULES):
        env["NODE_PATH"] = RUNTIME_MODULES + (
            os.pathsep + env["NODE_PATH"] if env.get("NODE_PATH") else ""
        )
    return env


def _node_major():
    exe = shutil.which("node")
    if not exe:
        return 0
    out = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout
    match = re.match(r"v(\d+)", out.strip())
    return int(match.group(1)) if match else 0


NODE_MAJOR = _node_major()
HAVE_PPTXGENJS = NODE_MAJOR > 0 and subprocess.run(
    ["node", "-e", "require('pptxgenjs')"], capture_output=True, env=_env()
).returncode == 0


def _py(script, *args, cwd=None):
    return subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, script), *args],
        capture_output=True, text=True, cwd=cwd,
    )


def _node_sandboxed(tmp, script, tokens, out):
    """The exact form build-deck uses: fs read of the project (+ runtime and
    the pack's source, where the example lives), fs write of the deck dir."""
    cmd = [
        "node", "--permission",
        f"--allow-fs-read={tmp}",
        f"--allow-fs-read={RUNTIME}",
        f"--allow-fs-read={SOURCE_DIR}",
        f"--allow-fs-write={tmp}",
        script, "--tokens", tokens, "--out", out,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=tmp, env=_env())


def _run_sizes(prs):
    sizes = set()
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        if run.text.strip() and run.font.size is not None:
                            sizes.add(float(run.font.size.pt))
    return sizes


@unittest.skipUnless(
    HAVE_PPTXGENJS and NODE_MAJOR >= 22,
    "needs Node 22+ and pptxgenjs (npm install --prefix .build/runtime pptxgenjs@4.0.1, or NODE_PATH)",
)
class BuildScriptTest(unittest.TestCase):
    def setUp(self):
        # Real path: Node resolves symlinks before checking the allowlists.
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="slides-build-script-"))
        with open(os.path.join(self.tmp, "package.json"), "w", encoding="utf-8") as fh:
            json.dump({"type": "module"}, fh)
        os.makedirs(os.path.join(self.tmp, ".slides"))
        self.brand = os.path.join(self.tmp, ".slides", "brand.json")
        with open(self.brand, "w", encoding="utf-8") as fh:
            json.dump(BRAND, fh)
        self.tokens = os.path.join(self.tmp, ".slides", "tokens.cjs")
        proc = _py("emit_tokens.py", self.brand, "--out", self.tokens)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _gate(self, pptx, spec):
        lint = _py("lint_pptx.py", pptx, "--brand", self.brand)
        self.assertEqual(lint.returncode, 0, lint.stdout + lint.stderr)
        self.assertIn("lint: clean", lint.stdout)
        stamped = _py("stamp.py", pptx, "--spec", spec)
        self.assertEqual(stamped.returncode, 0, stamped.stderr)
        against = _py("deck_to_spec.py", pptx, "--brand", self.brand, "--against", spec)
        self.assertEqual(against.returncode, 0, against.stdout + against.stderr)
        self.assertEqual(against.stdout, "")

    def test_example_round_trips(self):
        guard = _py("check_script.py", EXAMPLE)
        self.assertEqual(guard.returncode, 0, guard.stdout + guard.stderr)
        self.assertIn("script: clean", guard.stdout)
        spec = os.path.join(self.tmp, "sample-deck.md")
        shutil.copy(SAMPLE_SPEC, spec)
        out = os.path.join(self.tmp, "sample.pptx")
        built = _node_sandboxed(self.tmp, EXAMPLE, self.tokens, out)
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        self._gate(out, spec)
        prs = Presentation(out)
        self.assertEqual(len(prs.slides), 6)
        self.assertEqual(prs.slides[0].name, "slides-role:title")
        self.assertTrue(_run_sizes(prs) <= SCALE, _run_sizes(prs))

    def test_adversarial_content_round_trips(self):
        statement = 'He said "hi" `there` ${x} \\ end'
        notes_line_1 = "First line with 'quotes' and a \\ backslash."
        notes_line_2 = 'Second line with "double quotes" and ${braces}.'
        spec = os.path.join(self.tmp, "adv.deck.md")
        with open(spec, "w", encoding="utf-8") as fh:
            fh.write(
                "---\ndeck: Adversarial\naudience: Anyone who types punctuation.\n"
                "register: presented\n---\n\n## Slide 1\nlayout: statement\n"
                f"Statement: {statement}\nNotes: {notes_line_1} {notes_line_2}\n"
            )
        content = {"statement": statement, "notes": notes_line_1 + "\n" + notes_line_2}
        literal = json.dumps(json.dumps(content))  # a JS string literal holding JSON
        script = os.path.join(self.tmp, "adv.build.cjs")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(
                'const args = process.argv.slice(2);\n'
                'const tokensPath = args[args.indexOf("--tokens") + 1];\n'
                'const outPath = args[args.indexOf("--out") + 1];\n'
                'const T = require(require("path").resolve(tokensPath));\n'
                'const pptxgen = T.loadPptxgen();\n'
                f'const C = JSON.parse({literal});\n'
                'const pres = new pptxgen();\n'
                'pres.layout = "LAYOUT_WIDE";\n'
                'const s = pres.addSlide();\n'
                's.addText(C.statement, { x: T.margins.x, y: 1.5, w: T.slide.w - 2 * T.margins.x, h: 2.5, '
                'fontSize: T.scale.h1, color: T.colours.ink, fontFace: T.fonts.heading, '
                'objectName: "slides-lead:Statement", margin: 0 });\n'
                's.addNotes(C.notes);\n'
                'pres.writeFile({ fileName: outPath }).then(() => console.log("wrote " + outPath));\n'
            )
        guard = _py("check_script.py", script)
        self.assertEqual(guard.returncode, 0, guard.stdout + guard.stderr)
        out = os.path.join(self.tmp, "adv.pptx")
        built = _node_sandboxed(self.tmp, script, self.tokens, out)
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        self._gate(out, spec)
        prs = Presentation(out)
        slide = prs.slides[0]
        texts = [sh.text_frame.text for sh in slide.shapes if sh.has_text_frame]
        self.assertIn(statement, texts)
        self.assertEqual(
            slide.notes_slide.notes_text_frame.text, notes_line_1 + "\n" + notes_line_2
        )

    def test_example_usage_exit_2(self):
        proc = subprocess.run(["node", EXAMPLE], capture_output=True, text=True, env=_env())
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
