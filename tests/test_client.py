import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from trainer.client import Client, atomic_json, read_status, find_game, GAMES, backup_saves


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.client = Client("knight", self.root)
        self.folder = self.client.folder
        self.state = {"protocol": 1, "game": "knight", "session": "game-session", "timestamp": time.time(), "ready": True}
        atomic_json(self.folder / "status.json", self.state)

    def tearDown(self):
        self.temporary.cleanup()

    def test_backup_includes_steam_account_saves(self):
        source = self.root / "Library/Application Support" / GAMES["silksong"]["save"]
        account = source / "123456"
        account.mkdir(parents=True)
        (account / "user1.dat").write_bytes(b"original-save")
        (source / "shared.dat").write_bytes(b"shared")
        with patch("pathlib.Path.home", return_value=self.root):
            backup = backup_saves("silksong", self.root / "backups")
        self.assertEqual((backup / "123456/user1.dat").read_bytes(), b"original-save")
        hashes = json.loads((backup / "hashes.json").read_text())
        self.assertIn("123456/user1.dat", hashes)
        self.assertEqual((account / "user1.dat").read_bytes(), b"original-save")

    def test_stale_status_is_not_connected(self):
        self.assertIsNone(read_status(self.folder, now=self.state["timestamp"] + 4))

    def test_future_status_is_not_connected(self):
        self.assertIsNone(read_status(self.folder, now=self.state["timestamp"] - 5))

    def test_invalid_json_and_schema_are_disconnected(self):
        (self.folder / "status.json").write_text("{")
        self.assertIsNone(read_status(self.folder))
        atomic_json(self.folder / "status.json", {"protocol": 3})
        self.assertIsNone(read_status(self.folder))

    def test_request_targets_exact_session(self):
        self.client.send("currency", 1000)
        command = json.loads((self.folder / "request.json").read_text())
        self.assertEqual(command["session"], "game-session")
        self.assertEqual(command["operation"], "currency")
        self.assertEqual(command["value"], 1000)
        self.assertEqual((self.folder / "request.json").stat().st_mode & 0o777, 0o600)

    def test_pending_currency_is_not_retried(self):
        self.client.send("currency", 1000)
        original = (self.folder / "request.json").read_bytes()
        with self.assertRaises(RuntimeError): self.client.send("currency", 1000)
        self.assertEqual(original, (self.folder / "request.json").read_bytes())

    def test_acknowledgement_and_error(self):
        self.client.send("speed", 2)
        self.state.update(lastCommand=self.client.pending[0], error="paused")
        atomic_json(self.folder / "status.json", self.state)
        self.client.poll()
        self.assertIsNone(self.client.pending)
        self.assertEqual(self.client.error, "paused")

    def test_disconnected_result_is_unknown(self):
        self.client.send("currency", 100)
        (self.folder / "status.json").unlink()
        self.client.poll()
        self.assertIn("неизвестен", self.client.error)

    def test_restart_does_not_replay(self):
        self.client.poll()
        self.client.send("invincible", 1)
        self.state["session"] = "new-process"
        atomic_json(self.folder / "status.json", self.state)
        self.client.poll()
        self.assertIsNone(self.client.pending)
        self.assertIn("перезапущена", self.client.error)

    def test_main_menu_rejects_changes_but_allows_reset(self):
        self.state["ready"] = False
        atomic_json(self.folder / "status.json", self.state)
        with self.assertRaises(RuntimeError): self.client.send("currency", 100)
        self.client.send("reset")

    def test_wrong_game_rejected(self):
        self.state["game"] = "silksong"
        atomic_json(self.folder / "status.json", self.state)
        self.assertIsNone(self.client.poll())
        with self.assertRaises(RuntimeError): self.client.send("currency", 100)

    def test_close_revokes_lease(self):
        self.client.poll()
        self.assertTrue((self.folder / "lease.json").exists())
        self.client.close()
        self.assertFalse((self.folder / "lease.json").exists())

    def test_custom_library_path(self):
        app = self.root / "steamapps/common" / GAMES["knight"]["folder"] / GAMES["knight"]["app"]
        app.mkdir(parents=True)
        self.assertEqual(find_game("knight", str(self.root)), app)


if __name__ == "__main__": unittest.main()
