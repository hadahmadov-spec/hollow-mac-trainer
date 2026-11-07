"""Qt integration checks; skipped when the optional desktop dependencies are absent."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    from PySide6.QtWidgets import QApplication
    from trainer.app import Window
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "PySide6 desktop dependencies are not installed")
class LanguageWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.support = patch("trainer.app.SUPPORT", self.root)
        self.support.start()
        self.poll = patch("trainer.app.Client.poll", return_value=None)
        self.poll.start()
        self.close_client = patch("trainer.app.Client.close")
        self.close_client.start()
        self.window = Window()
        self.window.timer.stop()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.close_client.stop()
        self.poll.stop()
        self.support.stop()
        self.directory.cleanup()

    def test_language_change_keeps_session_game_and_unsent_values(self):
        self.window.select_game("silksong")
        client = self.window.clients["silksong"]
        client.pending = ("request", "session", 1)
        self.window.numbers["currency"].setValue(2345)
        self.window.change_language("ru")
        self.assertIs(self.window.clients["silksong"], client)
        self.assertEqual(client.pending, ("request", "session", 1))
        self.assertEqual(self.window.game, "silksong")
        self.assertEqual(self.window.numbers["currency"].value(), 2345)
        self.assertEqual(self.window.start.text(), "Запустить с модом")
        self.assertEqual(json.loads((self.root / "preferences.json").read_text())["language"], "ru")
        self.window.change_language("en")
        self.assertEqual(self.window.start.text(), "Launch with mods")
        self.assertEqual(self.window.switches["tools"].accessibleName(), "Infinite tools")

    def test_library_change_preserves_language_and_restart_restores_it(self):
        self.window.change_language("ru")
        with patch("trainer.app.QFileDialog.getExistingDirectory", return_value="/test/SteamLibrary"):
            self.window.choose_library()
        self.window.close()
        self.window = Window()
        self.window.timer.stop()
        self.assertEqual(self.window.library, "/test/SteamLibrary")
        self.assertEqual(self.window.language_combo.currentData(), "ru")
        self.assertEqual(self.window.start.text(), "Запустить с модом")

    def test_failed_preference_write_keeps_previous_language(self):
        with patch("trainer.app.atomic_json", side_effect=OSError("Read-only location")):
            self.window.change_language("ru")
        self.assertEqual(self.window.language_combo.currentData(), "en")
        self.assertEqual(self.window.start.text(), "Launch with mods")
        self.assertEqual(self.window.error.text(), "Read-only location")
