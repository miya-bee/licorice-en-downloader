"""Japanese / English catalog consistency and language selection."""
import ast
import json
import os
from pathlib import Path
import string
import tempfile
import unittest
from unittest.mock import patch

from licorice import i18n
from licorice.storage import Settings

PACKAGE = Path(__file__).resolve().parent.parent / "licorice"


def tr_literals():
    for path in sorted(PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tr"
                    and node.args and isinstance(node.args[0], ast.Constant)):
                yield path.name, node.lineno, node.args[0].value


def fields(text):
    return sorted(name for _, name, _, _ in string.Formatter().parse(text) if name is not None)


class CatalogTests(unittest.TestCase):
    def tearDown(self):
        i18n._language = None

    def test_every_translated_string_has_an_english_entry(self):
        missing = [f"{name}:{line}: {text!r}" for name, line, text in tr_literals() if text not in i18n.EN]
        self.assertEqual(missing, [])

    def test_no_unused_english_entries(self):
        used = {text for _, _, text in tr_literals()}
        self.assertEqual(sorted(set(i18n.EN) - used), [])

    def test_placeholders_match(self):
        for japanese, english in i18n.EN.items():
            self.assertEqual(fields(japanese), fields(english), japanese)

    def test_english_entries_contain_no_japanese(self):
        for japanese, english in i18n.EN.items():
            self.assertFalse(any("぀" <= char <= "鿿" or "！" <= char <= "～" for char in english),
                             english)

    def test_tr_switches_language_and_formats(self):
        key = "公式配布先への接続に失敗しました（HTTP {code}）。配布情報を再確認してください。"
        i18n.set_language("ja")
        self.assertIn("HTTP 503", i18n.tr(key, code=503))
        self.assertIn("（", i18n.tr(key, code=503))
        i18n.set_language("en")
        self.assertEqual(i18n.tr(key, code=503), i18n.EN[key].format(code=503))
        self.assertEqual(i18n.tr("unknown key"), "unknown key")

    def test_environment_override_and_auto_detection(self):
        with patch.dict(os.environ, {"LICORICE_LANG": "en"}):
            self.assertEqual(i18n.set_language("auto"), "en")
            self.assertEqual(i18n.set_language("ja"), "ja")
        with patch.dict(os.environ, {"LICORICE_LANG": "ja"}):
            self.assertEqual(i18n.set_language("bogus"), "ja")

    def test_settings_language_round_trip_and_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            settings = Settings(language="en")
            settings.save(base)
            loaded, warning = Settings.load(base)
            self.assertEqual((loaded.language, warning), ("en", ""))
            payload = json.loads((base / "settings.json").read_text(encoding="utf-8"))
            for value in ("fr", ["en"], None):
                payload["language"] = value
                (base / "settings.json").write_text(json.dumps(payload), encoding="utf-8")
                loaded, warning = Settings.load(base)
                self.assertEqual((loaded.language, warning, loaded.protected), ("auto", "", False))
            # Settings written by v0.1.x have no language key.
            del payload["language"]
            (base / "settings.json").write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(Settings.load(base)[0].language, "auto")


if __name__ == "__main__":
    unittest.main()
