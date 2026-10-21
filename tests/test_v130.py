import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import applauncher, sysactions  # noqa: E402


class SystemCommands(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = sysactions.apps_dir
        sysactions.apps_dir = lambda: Path(self.tmp.name)

    def tearDown(self):
        sysactions.apps_dir = self.saved
        self.tmp.cleanup()

    def test_both_languages_shut_down(self):
        sysactions.apply(True, lambda *_: None)
        apps = applauncher.load_apps([Path(self.tmp.name)])
        for q in ("shutdown", "herunterfahren"):
            hit = applauncher.filter_apps(apps, q, {})
            self.assertEqual(applauncher.command(hit[0]), "systemctl poweroff", q)
        text = (Path(self.tmp.name) / "hyprstudio-poweroff-de.desktop").read_text(encoding="utf-8")
        self.assertIn("Keywords=shutdown;", text)  # Rofi/Wofi/Fuzzel suchen auch in Keywords

    def test_off_hides_without_deleting(self):
        sysactions.apply(True, lambda *_: None)
        sysactions.apply(False, lambda *_: None)
        self.assertEqual(len(list(Path(self.tmp.name).glob("*.desktop"))), 9)
        self.assertEqual(applauncher.load_apps([Path(self.tmp.name)]), [])

    def test_lock_only_with_hyprlock(self):
        sysactions.apply(True, lambda *_: None, lock_ok=False)
        names = [a["name"] for a in applauncher.load_apps([Path(self.tmp.name)])]
        self.assertNotIn("Sperren", names)
        self.assertIn("Herunterfahren", names)


if __name__ == "__main__":
    unittest.main()
