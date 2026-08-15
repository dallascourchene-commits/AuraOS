import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "block_destructive.py"


def run_hook(command=None, *, tool_name="Bash", raw=None, home=None):
    payload = raw if raw is not None else json.dumps({
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {"command": command} if command is not None else {},
        "cwd": "/work/project",
    })
    env = os.environ.copy()
    if home:
        env["HOME"] = str(home)
    return subprocess.run(
        [sys.executable, str(HOOK)], input=payload, text=True,
        capture_output=True, env=env, check=False,
    )


class HookTests(unittest.TestCase):
    def assertBlocked(self, command, expected_rule):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_hook(command, home=tmp)
            self.assertEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            output = data["hookSpecificOutput"]
            self.assertEqual(output["permissionDecision"], "deny")
            self.assertIn(expected_rule, output["permissionDecisionReason"])
            log = Path(tmp) / ".claude" / "hooks" / "blocked.log"
            text = log.read_text(encoding="utf-8")
            self.assertIn(command, text)
            self.assertIn("project=/work/project", text)

    def assertAllowed(self, command):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_hook(command, home=tmp)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertFalse((Path(tmp) / ".claude" / "hooks" / "blocked.log").exists())

    def test_required_blocks(self):
        cases = [
            ("rm -rf build", "rm -rf"),
            ("rm -r -f build", "rm -rf"),
            ('psql -c "DROP TABLE users"', "DROP TABLE"),
            ("git push origin main --force", "git push --force"),
            ("sqlite3 app.db 'TRUNCATE TABLE events'", "TRUNCATE"),
            ("sqlite3 app.db 'DELETE FROM events'", "DELETE FROM without WHERE"),
        ]
        for command, rule in cases:
            with self.subTest(command=command):
                self.assertBlocked(command, rule)

    def test_delete_with_where_is_allowed(self):
        self.assertAllowed("sqlite3 app.db 'DELETE FROM events WHERE id = 7'")

    def test_normal_commands_are_allowed(self):
        for command in ["npm test", "git push origin main", "rm build.tmp", "python -m pytest"]:
            with self.subTest(command=command):
                self.assertAllowed(command)

    def test_non_bash_tool_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_hook("rm -rf /", tool_name="Read", home=tmp)
            self.assertEqual(result.stdout, "")

    def test_malformed_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_hook(raw="{", home=tmp)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
