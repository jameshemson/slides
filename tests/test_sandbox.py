"""The execution boundary for a deck build script is Node's permission model.

build-deck runs every <deck>.build.cjs as

    node --permission --allow-fs-read="<project root>" --allow-fs-write="<deck directory>" ...

Under those flags Node refuses child processes, native addons, worker threads
and any filesystem access outside the two allowlists, whatever the script
contains. This test proves the flags on this machine with a probe script that
writes a deck through pptxgenjs and then tries three escapes. It needs Node 22
or newer and the provisioned runtime (`npm install --prefix .build/runtime
pptxgenjs@4.0.1`); it skips otherwise, so CI (no npm packages) stays green.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME = os.path.join(REPO_ROOT, ".build", "runtime")
RUNTIME_MODULES = os.path.join(RUNTIME, "node_modules")


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
HAVE_RUNTIME = NODE_MAJOR > 0 and subprocess.run(
    ["node", "-e", "require('pptxgenjs')"], capture_output=True, env=_env()
).returncode == 0

PROBE = r"""
const pptxgen = require("pptxgenjs");
const out = process.argv[2];
const escapePath = process.argv[3];
const homeFile = process.argv[4];
function attempt(label, fn) {
  try { fn(); console.log(label + ": ALLOWED"); }
  catch (err) { console.log(label + ": blocked " + (err.code || err.name)); }
}
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
const slide = pres.addSlide();
slide.addText("probe", { x: 1, y: 1, w: 4, h: 1, fontSize: 24, color: "000000", fontFace: "Calibri" });
pres.writeFile({ fileName: out }).then((written) => {
  console.log("wrote " + written);
  attempt("child_process", () => require("child_process").execSync("echo x"));
  attempt("write-outside", () => require("fs").writeFileSync(escapePath, "x"));
  attempt("read-home", () => require("fs").readFileSync(homeFile));
}).catch((err) => { console.error("probe failed: " + err.message); process.exit(1); });
"""


@unittest.skipUnless(
    NODE_MAJOR >= 22 and HAVE_RUNTIME,
    "needs Node 22+ and pptxgenjs under .build/runtime (npm install --prefix .build/runtime pptxgenjs@4.0.1)",
)
class SandboxTest(unittest.TestCase):
    def setUp(self):
        # Real path: Node resolves symlinks (macOS /var -> /private/var) before
        # checking the allowlists, so the flags must name the resolved path.
        self.outer = os.path.realpath(tempfile.mkdtemp(prefix="slides-sandbox-"))
        self.project = os.path.join(self.outer, "project")
        self.deck_dir = os.path.join(self.project, "deck")
        os.makedirs(self.deck_dir)
        self.probe = os.path.join(self.project, "probe.cjs")
        with open(self.probe, "w", encoding="utf-8") as fh:
            fh.write(PROBE)
        self.escape = os.path.join(self.outer, "escape.txt")
        home = os.path.expanduser("~")
        candidates = [os.path.join(home, name) for name in (".zshrc", ".bashrc", ".profile")]
        self.home_file = next((c for c in candidates if os.path.isfile(c)), candidates[0])

    def tearDown(self):
        shutil.rmtree(self.outer, ignore_errors=True)

    def _run(self, flags):
        cmd = ["node", *flags, self.probe,
               os.path.join(self.deck_dir, "probe.pptx"), self.escape, self.home_file]
        return subprocess.run(cmd, capture_output=True, text=True, env=_env(), cwd=self.project)

    def test_permission_flags_hold(self):
        proc = self._run([
            "--permission",
            f"--allow-fs-read={self.project}",
            f"--allow-fs-read={RUNTIME}",
            f"--allow-fs-write={self.deck_dir}",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("wrote", proc.stdout)
        self.assertIn("child_process: blocked ERR_ACCESS_DENIED", proc.stdout)
        self.assertIn("write-outside: blocked ERR_ACCESS_DENIED", proc.stdout)
        self.assertIn("read-home: blocked ERR_ACCESS_DENIED", proc.stdout)
        self.assertTrue(os.path.isfile(os.path.join(self.deck_dir, "probe.pptx")))
        self.assertFalse(os.path.exists(self.escape))

    def test_plain_node_is_not_a_boundary(self):
        proc = self._run([])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ALLOWED", proc.stdout)

    def test_node_version_gate(self):
        self.assertGreaterEqual(NODE_MAJOR, 22)


if __name__ == "__main__":
    unittest.main()
