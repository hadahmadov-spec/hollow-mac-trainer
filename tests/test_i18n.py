import ast
from pathlib import Path
import re
import unittest

from trainer.i18n import EN, get_language, set_language, tr


class TranslationTests(unittest.TestCase):
    def tearDown(self):
        set_language("en")

    def test_catalog_covers_ui_client_and_bridge_messages(self):
        root = Path(__file__).resolve().parents[1]
        for filename in ("trainer/app.py", "trainer/client.py"):
            tree = ast.parse((root / filename).read_text())
            formatted_parts = {id(part) for node in ast.walk(tree)
                               if isinstance(node, ast.JoinedStr) for part in node.values}
            for node in ast.walk(tree):
                if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                        and id(node) not in formatted_parts and re.search("[А-Яа-яЁё]", node.value)):
                    self.assertIn(node.value, EN, (filename, node.lineno, node.value))
        bridge = (root / "bridge/TrainerBridge.cs").read_text()
        for message in re.findall(r'"([^"\n]*[А-Яа-яЁё][^"\n]*)"', bridge):
            self.assertIn(message, EN)

    def test_switching_and_unknown_messages(self):
        set_language("en")
        self.assertEqual(tr("Неуязвимость"), "Invincibility")
        set_language("ru")
        self.assertEqual(tr("Неуязвимость"), "Неуязвимость")
        self.assertEqual(tr("File {not-a-template} unavailable"), "File {not-a-template} unavailable")
        set_language("unsupported")
        self.assertEqual(get_language(), "en")

    def test_version_diagnostic_preserves_actual_versions(self):
        set_language("en")
        self.assertEqual(tr("Установлена версия 2.0; проверена 1.0. Нужна проверка совместимости."),
                         "Installed version 2.0; tested version 1.0. Compatibility needs to be verified.")

    def test_status_placeholder_parity(self):
        from string import Formatter
        for source, english in EN.items():
            fields = lambda text: {name for _, name, _, _ in Formatter().parse(text) if name}
            self.assertEqual(fields(source), fields(english), source)


if __name__ == "__main__":
    unittest.main()
