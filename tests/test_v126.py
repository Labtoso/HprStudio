import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import fonts, hardware, model  # noqa: E402


class LaptopKeys(unittest.TestCase):
    def test_binds_like_official_example(self):
        s = model.hypr_state({"laptop_keys": True, "binds": [model._bind([], "XF86AudioMute", "exec", "old")]})
        lua = model.hypr_lua(s)
        self.assertIn('hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%+"), '
                      '{ locked = true, repeating = true })', lua)
        self.assertIn('hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+")',
                      lua)
        self.assertEqual(lua.count('hl.bind("XF86AudioMute"'), 1)  # eigenes altes Kürzel fällt weg
        self.assertNotIn('"old"', lua)
        conf = model.hypr_conf(dict(s, vol_tool="pactl"))
        self.assertIn("pactl set-sink-mute @DEFAULT_SINK@ toggle", conf)
        self.assertNotIn("XF86", model.hypr_lua(model.hypr_state(None)))

    def test_foreign_keys_commented(self):
        with tempfile.TemporaryDirectory() as d:
            hdir = Path(d)
            main = hdir / "hyprland.lua"
            main.write_text('hl.bind("XF86AudioMute", hl.dsp.exec_cmd("x"))\nhl.bind("SUPER + Q", hl.dsp.exec_cmd("kitty"))\n',
                            encoding="utf-8")
            old, model.FORMAT = model.FORMAT, "lua"
            try:
                s = model.hypr_state({"laptop_keys": True, "laptop_managed": True})
                self.assertEqual(model.manage_laptop_keys(hdir, s, lambda *_: None), 1)
                text = main.read_text(encoding="utf-8")
                self.assertIn('-- [Hypr Studio] hl.bind("XF86AudioMute"', text)
                self.assertIn('\nhl.bind("SUPER + Q"', text)
            finally:
                model.FORMAT = old
        self.assertEqual(model.foreign_key_lines("bindel = , XF86AudioRaiseVolume, exec, a\n"
                                                 "bind = SUPER, XF86AudioMute, exec, b\n", "conf"), [0])

    def test_detect_lenovo(self):
        with tempfile.TemporaryDirectory() as d:
            dmi = Path(d)
            for k, v in {"sys_vendor": "LENOVO", "product_name": "82LM", "product_version": "IdeaPad 5 14ALC05",
                         "chassis_type": "10"}.items():
                (dmi / k).write_text(v + "\n")
            old_dmi, old_dry = hardware.DMI, model.DRY
            hardware.DMI, model.DRY = dmi, False
            try:
                dev = hardware.detect()
            finally:
                hardware.DMI, model.DRY = old_dmi, old_dry
            self.assertEqual(hardware.label(dev), "Lenovo IdeaPad 5 14ALC05")
            self.assertTrue(dev["laptop"])


class ComicSans(unittest.TestCase):
    def test_catalog_and_cab_finder(self):
        self.assertIn(("ComicSansMS", "Comic Sans MS"), fonts.CATALOG)
        fake_cab = b"MSCF" + bytes(4) + (40).to_bytes(4, "little") + bytes(12) + bytes((3, 1)) + bytes(14)
        exe = b"MZ...MSCF-not-a-header..." + fake_cab + b"tail"
        self.assertEqual(fonts.find_cab(exe), fake_cab)


if __name__ == "__main__":
    unittest.main()
