"""Contract checks only: no real model call and no persisted chat."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

PLUGIN = Path(__file__).resolve().parents[2] / "screenplay-asset-extractor"
sys.path.insert(0, str(PLUGIN / "runtime"))
from harness_core.appserver import AppServer


class FakeServer(AppServer):
    def __init__(self, ephemeral=True):
        super().__init__()
        self.confirmed = ephemeral
        self.calls = []

    def start(self):
        pass

    def request(self, method, params, timeout=30):
        self.calls.append((method, params))
        if method == "thread/start":
            return {"thread": {"id": "transient", "ephemeral": self.confirmed}}
        if method == "turn/start":
            self.events.append({"method": "turn/completed", "params": {
                "threadId": "transient", "turnId": "t1", "turn": {
                    "id": "t1", "status": "completed", "items": [
                        {"type": "agentMessage", "text": json.dumps({"status": "succeeded"})}
                    ]}}})
            return {"turn": {"id": "t1"}}
        raise AssertionError(method)


class DispatchIsolation(unittest.TestCase):
    def test_existing_thread_id_does_not_resume_persistent_chat(self):
        server = FakeServer()
        with tempfile.TemporaryDirectory() as directory:
            result, thread = server.run(PLUGIN / "skills/extract-asset-table/SKILL.md",
                                        {}, {}, directory, thread_id="old-saved-chat")
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(thread, "transient")
        self.assertTrue(server.calls[0][1]["ephemeral"])
        self.assertNotIn("thread/resume", [method for method, _ in server.calls])

    def test_server_must_confirm_ephemeral_before_turn(self):
        for confirmed in (False, None):
            with self.subTest(confirmed=confirmed):
                server = FakeServer(confirmed)
                with tempfile.TemporaryDirectory() as directory:
                    with self.assertRaisesRegex(RuntimeError, "ephemeral"):
                        server.run(PLUGIN / "skills/extract-asset-table/SKILL.md", {}, {}, directory)
                self.assertEqual([method for method, _ in server.calls], ["thread/start"])


if __name__ == "__main__":
    unittest.main()
