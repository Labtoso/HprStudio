"""Seiten Hyprland und Waybar: Seitenleiste links, oben Live-Vorschau, darunter Presets bzw. Regler-Karten."""

from . import model, theme
from .i18n import t
from .preview import DesktopPreview, render_pixmap
from .qt import QtCore, QtWidgets, Qt
from .keys import BindEditor
from .widgets import Card, FlowGrid, ModuleColumns, PresetCard, draw_icon



class EditorPage(QtWidgets.QWidget):
    SECTIONS: tuple = ()
    NO_PREVIEW: tuple = ()
    HAS_PLAY = True
    KIND = ""

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.state = self.load_state()
        self.cards, self.switches, self.segs, self.presets = [], [], [], {}
        self._presets_dirty = True

        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        side = QtWidgets.QFrame()
        side.setObjectName("Side")
        side.setFixedWidth(190)
        sl = QtWidgets.QVBoxLayout(side)
        sl.setContentsMargins(10, 12, 10, 12)
        sl.setSpacing(4)
        self.nav = {}
        grp = QtWidgets.QButtonGroup(self)
        for key in self.SECTIONS:
            b = QtWidgets.QPushButton()
            b.setObjectName("Nav")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self.show_section(k))
            grp.addButton(b)
            sl.addWidget(b)
            self.nav[key] = b
        sl.addStretch()
        self.info = QtWidgets.QLabel()
        self.info.setObjectName("Label")
        self.info.setWordWrap(True)
        sl.addWidget(self.info)
        lay.addWidget(side)

        right = QtWidgets.QVBoxLayout()
        right.setSpacing(14)
        top = QtWidgets.QHBoxLayout()
        top.setSpacing(14)
        self.preview = DesktopPreview()
        self.preview.setFixedHeight(290)
        top.addWidget(self.preview, 1)
        acts = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.TopToBottom)
        acts.setSpacing(8)
        self.acts = acts
        self.page_title = QtWidgets.QLabel()
        self.page_title.setObjectName("PageTitle")
        acts.addWidget(self.page_title)
        acts.addStretch()
        self.btn_play = QtWidgets.QPushButton()
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.clicked.connect(self.preview.play)
        self.btn_undo = QtWidgets.QPushButton()
        self.btn_undo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_undo.clicked.connect(self.undo)
        self.btn_apply = QtWidgets.QPushButton()
        self.btn_apply.setObjectName("Primary")
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.clicked.connect(self.apply)
        for b in (self.btn_play, self.btn_undo, self.btn_apply):
            b.setFixedSize(170, 40)
            acts.addWidget(b)
        top.addLayout(acts)
        right.addLayout(top)

        self.stack = QtWidgets.QStackedWidget()
        self.pages = {}
        for key in self.SECTIONS:
            sa = QtWidgets.QScrollArea()
            sa.setWidgetResizable(True)
            sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            inner = QtWidgets.QWidget()
            inner.setObjectName("ScrollInner")
            il = QtWidgets.QVBoxLayout(inner)
            il.setContentsMargins(0, 0, 6, 0)
            il.setSpacing(14)
            self.build_section(key, il)
            il.addStretch()
            sa.setWidget(inner)
            self.stack.addWidget(sa)
            self.pages[key] = sa
        right.addWidget(self.stack, 1)
        lay.addLayout(right, 1)

        self.refresh_controls()
        self.show_section(win.cfg.get(f"{self.KIND}_section", self.SECTIONS[0]))

    # ----- Aufbau-Helfer -----
    def card(self, layout, title_key) -> Card:
        c = Card(title_key, self)
        layout.addWidget(c)
        self.cards.append(c)
        return c

    def preset_grid(self, layout, names, prefix):
        grid = FlowGrid(212)
        for n in names:
            pc = PresetCard(n)
            pc.setProperty("tkey", prefix + n)
            pc.clicked.connect(self.use_preset)
            grid.add(pc)
            self.presets[n] = pc
        layout.addWidget(grid)

    # ----- Zustand -----
    def set(self, key, value):
        if self.state.get(key) == value:
            return
        self.state[key] = value
        self.win.cfg[f"{self.KIND}_preset"] = ""
        self.changed()

    def changed(self):
        self.win.cfg[self.KIND] = self.state
        self.win.save_later()
        self.win.update_previews()
        self._presets_dirty = True
        self.refresh_presets_selection()

    def refresh_controls(self):
        for c in self.cards:
            c.refresh(self.state)

    def show_section(self, key):
        if key not in self.pages:
            key = self.SECTIONS[0]
        self.nav[key].setChecked(True)
        self.stack.setCurrentWidget(self.pages[key])
        self.win.cfg[f"{self.KIND}_section"] = key
        self.win.save_later()
        # Bereiche ohne sichtbare Wirkung: Vorschau weg, Knöpfe in eine Zeile → mehr Platz für Einstellungen
        compact = key in self.NO_PREVIEW
        self.preview.setVisible(not compact)
        self.btn_play.setVisible(self.HAS_PLAY and not compact)
        self.acts.setDirection(QtWidgets.QBoxLayout.Direction.LeftToRight if compact
                               else QtWidgets.QBoxLayout.Direction.TopToBottom)
        if key == "presets":
            self.render_presets()

    def render_presets(self, force=False):
        if not (self._presets_dirty or force) or not self.presets:
            return
        self._presets_dirty = False
        for name, pc in self.presets.items():
            hs, ws = self.preset_states(name)
            pc.set_pixmap(render_pixmap(hs, ws, 196, 110, 9))
        self.refresh_presets_selection()

    def refresh_presets_selection(self):
        sel = self.win.cfg.get(f"{self.KIND}_preset", "")
        for name, pc in self.presets.items():
            pc.refresh(name == sel, self.win.accent())

    def use_preset(self, name):
        self.state = self.preset_value(name)
        self.refresh_controls()
        self.changed()
        self.win.cfg[f"{self.KIND}_preset"] = name
        self.refresh_presets_selection()

    def apply_theme(self, accent):
        for sw in self.switches:
            sw.accent = accent
            sw.update()
        self.btn_play.setIcon(draw_icon("play", theme.TEXT, 16))
        self.refresh_presets_selection()

    def retranslate(self):
        for key, b in self.nav.items():
            b.setText(t("sec." + key).replace("&", "&&"))
        for c in self.cards:
            c.retranslate()
        for s in self.segs:
            s.retranslate()
        for pc in self.presets.values():
            pc.name.setText(t(pc.property("tkey")))
        self.page_title.setText(t("tab." + self.KIND))
        self.btn_play.setText(t("play"))
        self.btn_undo.setText(t("undo"))
        self.btn_undo.setToolTip(t("tip.undo"))
        self.btn_apply.setText(t("apply"))
        self.update_info()

    # von Unterklassen
    def load_state(self) -> dict: ...
    def build_section(self, key, layout): ...
    def preset_states(self, name): ...
    def preset_value(self, name) -> dict: ...
    def apply(self): ...
    def undo(self): ...
    def update_info(self): ...


class HyprPage(EditorPage):
    SECTIONS = ("presets", "windows", "colors", "effects", "anim", "input", "keys", "system")
    NO_PREVIEW = ("input", "keys", "system")
    KIND = "hypr"

    def load_state(self):
        return model.hypr_state(self.win.cfg.get("hypr"))

    def build_section(self, key, lay):
        if key == "presets":
            self.preset_grid(lay, model.HYPR_PRESETS, "p.")
        elif key == "windows":
            c = self.card(lay, "card.gaps")
            c.slider("gaps_in", 0, 40)
            c.slider("gaps_out", 0, 60)
            c.toggle("smart_gaps", tip="tip.smart_gaps")
            c = self.card(lay, "card.border")
            c.slider("border_size", 0, 8)
            c.slider("rounding", 0, 30)
            c.slider("rounding_power", 2, 10, 0.5, "{:.1f}", tip="tip.rounding_power")
            c.toggle("resize_on_border")
            c = self.card(lay, "card.layout")
            c.choice("layout", ("dwindle", "master"), "layout.")
            c = self.card(lay, "card.dwindle")
            c.toggle("dwindle_preserve")
            c.choice("dwindle_force", ("0", "1", "2"), "force.")
            c.toggle("dwindle_smart", tip="tip.dwindle_smart")
            c = self.card(lay, "card.master")
            c.choice("master_new", ("master", "slave", "inherit"), "mnew.")
            c.slider("master_mfact", 0.1, 0.9, 0.05, "{:.2f}")
            c.choice("master_orient", ("left", "right", "top", "bottom", "center"), "orient.")
        elif key == "colors":
            c = self.card(lay, "card.border_col")
            c.color("active1", label_key="active")
            c.toggle("gradient")
            c.color("active2")
            c.slider("angle", 0, 360, 5, "{:.0f}°")
            c.color("inactive")
            c.toggle("border_rotate", tip="tip.border_rotate")
            c.slider("border_rotate_speed", 10, 200, 5, "{:.0f}", tip="tip.border_rotate_speed")
            c = self.card(lay, "card.shadow")
            c.color("shadow_color")
            c = self.card(lay, "card.background")
            c.color("bg_color")
        elif key == "effects":
            c = self.card(lay, "card.opacity")
            c.slider("active_opacity", 0.3, 1.0, 0.01, "{:.2f}")
            c.slider("inactive_opacity", 0.3, 1.0, 0.01, "{:.2f}")
            c.toggle("dim_inactive")
            c.slider("dim_strength", 0.0, 1.0, 0.05, "{:.2f}")
            c = self.card(lay, "card.blur")
            c.toggle("blur")
            c.slider("blur_size", 1, 20)
            c.slider("blur_passes", 1, 6)
            c.slider("blur_vibrancy", 0.0, 1.0, 0.01, "{:.2f}")
            c.slider("blur_noise", 0.0, 0.2, 0.0025, "{:.4f}")
            c.slider("blur_contrast", 0.0, 2.0, 0.02, "{:.2f}")
            c.slider("blur_brightness", 0.0, 2.0, 0.02, "{:.2f}")
            c.toggle("blur_xray", tip="tip.blur_xray")
            c.toggle("blur_ignore_opacity")
            c = self.card(lay, "card.shadow")
            c.toggle("shadow")
            c.slider("shadow_range", 0, 40)
            c.slider("shadow_power", 1, 4)
            c.toggle("shadow_sharp")
        elif key == "anim":
            c = self.card(lay, "card.anim")
            c.toggle("anim")
            c.choice("anim_curve", tuple(model.CURVES), "curve.")
            c.slider("anim_tempo", 0.5, 2.0, 0.1, "{:.1f}×", tip="tip.anim_tempo")
            c.choice("win_style", tuple(model.WIN_STYLES), "win.")
            c.choice("ws_style", tuple(model.WS_STYLES), "ws.")
            c = self.card(lay, "card.anim_parts")
            for k in ("anim_windows", "anim_fade", "anim_ws", "anim_border", "anim_layers"):
                c.toggle(k)
        elif key == "input":
            c = self.card(lay, "card.kb")
            c.text("kb_layout", tip="tip.kb_layout", width=160)
            c.text("kb_variant", tip="tip.kb_variant", width=160)
            c.text("kb_options", tip="tip.kb_options", width=260)
            c.toggle("numlock")
            c.slider("repeat_rate", 10, 100, 1, "{:.0f}/s")
            c.slider("repeat_delay", 100, 1500, 50, "{:.0f} ms")
            c = self.card(lay, "card.mouse")
            c.slider("sensitivity", -1.0, 1.0, 0.05, "{:+.2f}")
            c.choice("accel", ("default", "flat", "adaptive"), "accel.")
            c.choice("follow_mouse", ("0", "1", "2"), "fm.")
            c.toggle("left_handed")
            c = self.card(lay, "card.touchpad")
            c.toggle("natural_scroll")
            c.toggle("dwt")
            c.slider("scroll_factor", 0.1, 3.0, 0.1, "{:.1f}×")
            c.choice("gesture", ("0", "3", "4"), "gest.", tip="tip.gesture")
            c = self.card(lay, "card.cursor")
            c.slider("cursor_size", 16, 64, 2, "{:.0f}")
            c.text("cursor_theme", tip="tip.cursor_theme", width=220)
            c.slider("cursor_timeout", 0.0, 30.0, 1.0, "{:.0f} s", tip="tip.cursor_timeout")
            c.toggle("cursor_hide_keys")
        elif key == "system":
            c = self.card(lay, "card.autostart")
            c.toggle("autostart_waybar")
            c.lines("autostart", tip="tip.autostart")
            c = self.card(lay, "card.monitor")
            c.toggle("monitor_on", tip="tip.monitor_on")
            c.choice("monitor_mode", ("preferred", "highrr", "highres"), "mmode.")
            c.choice("monitor_scale", ("auto", "1", "1.25", "1.5", "2"), "scale.")
            c = self.card(lay, "card.misc")
            c.toggle("no_logo")
            c.toggle("focus_on_activate")
            c.toggle("swallow", tip="tip.swallow")
            c.text("swallow_regex", width=260)
            c.toggle("mmb_paste")
            c.toggle("dpms_mouse")
            c.toggle("dpms_key")
        elif key == "keys":
            c = self.card(lay, "card.keys")
            self.binds = BindEditor()
            self.binds.changed.connect(self._binds_changed)
            self.binds.fix_requested.connect(self._fix_conflicts)
            self.binds.import_requested.connect(self._import_binds)
            c.layout().addWidget(self.binds)
            c.rows.append((QtWidgets.QLabel(), lambda s: (self.binds.load(s["binds"]), self._mark())))

    def _binds_changed(self):
        self.state["binds"] = self.binds.read()
        self._mark()
        self.changed()

    def _conflicts(self) -> set:
        main = self.hdir() / "hyprland.lua"
        if not main.is_file():
            return set()
        text = main.read_text(encoding="utf-8", errors="replace")
        mine = {model.combo(b["mods"], b["key"]) for b in self.state["binds"] if model.bind_ok(b)}
        return {c for _, c in model.lua_bind_combos(text) if c in mine}

    def _mark(self):
        if hasattr(self, "binds"):
            self.binds.mark(self._conflicts())

    def _import_binds(self):
        self.win.log("")
        got = model.import_binds(self.hdir(), self.win.log)
        if not got:
            self.win.set_status(t("keys.imported", n=0))
            return
        self.binds.merge(got)
        # Originale sind jetzt auskommentiert → sofort anwenden, sonst fehlen die Kürzel bis zum nächsten Klick
        self.apply()
        self.win.set_status(t("keys.imported", n=len(got)))

    def _fix_conflicts(self):
        self.win.log("")
        n = model.comment_conflicts(self.hdir(), self.state["binds"], self.win.log)
        self.win.set_status(t("keys.fixed", n=n))
        self._mark()

    def retranslate(self):
        super().retranslate()
        if hasattr(self, "binds"):
            self.binds.retranslate()
            self._mark()

    def set(self, key, value):
        super().set(key, value)
        if key in ("anim_curve", "anim_tempo", "win_style") and self.state["anim"]:
            self.preview.play()

    def preset_states(self, name):
        return model.preset_state(name, self.state), self.win.waybar_page.state if hasattr(self.win, "waybar_page") else None

    def preset_value(self, name):
        return model.preset_state(name, self.state)

    def hdir(self):
        return model.config_home() / "hypr"

    def apply(self):
        ok, info = model.apply_hypr(self.state, self.hdir(), self.win.log)
        self.win.report(ok, info)
        self.update_info()
        self._mark()

    def undo(self):
        self.win.log("")
        ok = model.undo_hypr(self.hdir(), self.win.log)
        self.win.set_status(t("undone") if ok else t("nothing"))

    def update_info(self):
        fmt = model.hypr_format(self.hdir())
        self.info.setText("Hyprland · " + t(f"fmt.{fmt or 'none'}"))


class WaybarPage(EditorPage):
    SECTIONS = ("presets", "bar", "modules", "options", "style")
    HAS_PLAY = False
    KIND = "waybar"

    def __init__(self, win):
        super().__init__(win)
        self.preview.zoom_bar = True
        self.preview.setFixedHeight(190)

    def load_state(self):
        return model.waybar_state(self.win.cfg.get("waybar"))

    def build_section(self, key, lay):
        if key == "presets":
            self.preset_grid(lay, model.WAYBAR_PRESETS, "wp.")
        elif key == "bar":
            c = self.card(lay, "card.shape")
            c.choice("position", ("top", "bottom"), "pos.")
            c.choice("style", ("bar", "float", "islands"), "st.")
            c.choice("layer", ("top", "bottom"), "layer.", tip="tip.layer")
            c.toggle("exclusive", tip="tip.exclusive")
            c = self.card(lay, "card.size")
            c.slider("height", 20, 60)
            c.slider("margin", 0, 30)
            c.slider("radius", 0, 30)
            c.slider("spacing", 0, 20)
            c.slider("pad", 0, 24)
            c.slider("border_width", 0, 4)
        elif key == "modules":
            c = self.card(lay, "sec.modules")
            self.mods = ModuleColumns()
            self.mods.changed.connect(self._mods_changed)
            c.layout().addWidget(self.mods)
            c.rows.append((QtWidgets.QLabel(), lambda s: self.mods.load(s)))
            c2 = self.card(lay, "card.extra")
            c2.text("launcher", width=260)
            c2.text("power_cmd", width=260)
            c2.text("vol_click", width=260)
        elif key == "options":
            c = self.card(lay, "card.ws")
            c.choice("ws_format", ("number", "dot"), "wsf.")
            c.choice("ws_look", ("pill", "box", "underline", "text"), "wsl.")
            c.slider("ws_persist", 0, 10, 1, "{:.0f}", tip="tip.ws_persist")
            c = self.card(lay, "card.clock")
            c.choice("clock_fmt", ("hm", "hms", "dhm", "full"), "cf.")
            c.toggle("clock24")
            c = self.card(lay, "card.modopts")
            c.slider("win_len", 10, 120)
            c.slider("mpris_len", 10, 80)
            c.choice("net_fmt", ("essid", "ip", "signal"), "net.")
            c.slider("vol_step", 1, 20, 1, "{:.0f} %")
            c.slider("bat_warn", 5, 60, 1, "{:.0f} %")
            c.slider("bat_crit", 2, 40, 1, "{:.0f} %")
            c.slider("interval", 1, 30, 1, "{:.0f} s")
            c.slider("tray_size", 12, 32)
            c.toggle("tooltips")
        elif key == "style":
            c = self.card(lay, "card.colors")
            c.color("bg")
            c.color("fg")
            c.color("accent")
            c.color("border")
            c.toggle("colorful", tip="tip.colorful")
            self.btn_from = QtWidgets.QPushButton()
            self.btn_from.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_from.clicked.connect(self.from_hypr)
            c.layout().addWidget(self.btn_from, 0, Qt.AlignmentFlag.AlignLeft)
            c = self.card(lay, "card.font")
            c.text("font", width=260)
            c.slider("font_size", 9, 24)
            c.choice("font_weight", ("normal", "600", "bold"), "fw.")
            c.toggle("icons")

    def _mods_changed(self):
        new = self.mods.read()
        if any(new[k] != self.state[k] for k in new):
            self.state.update(new)
            self.win.cfg["waybar_preset"] = ""
            self.changed()

    def from_hypr(self):
        hs = self.win.hypr_page.state
        self.state["accent"] = model.norm(hs["active1"])[:7] + "ff"
        self.state["border"] = model.norm(hs["inactive"])
        self.win.cfg["waybar_preset"] = ""
        self.refresh_controls()
        self.changed()

    def preset_states(self, name):
        return self.win.hypr_page.state, model.waybar_preset(name, self.state)

    def preset_value(self, name):
        return model.waybar_preset(name, self.state)

    def wdir(self):
        return model.config_home() / "waybar"

    def apply(self):
        if not model.which("waybar"):
            self.win.report(False, "nowaybar")
            return
        ok, info = model.apply_waybar(self.state, self.wdir(), self.win.log)
        self.win.report(ok, info)

    def undo(self):
        self.win.log("")
        ok = model.undo_waybar(self.wdir(), self.win.log)
        self.win.set_status(t("undone") if ok else t("nothing"))

    def retranslate(self):
        super().retranslate()
        if hasattr(self, "mods"):
            self.mods.retranslate()
        if hasattr(self, "btn_from"):
            self.btn_from.setText(t("from_hypr"))

    def update_info(self):
        self.info.setText("Waybar · " + ("✓" if model.which("waybar") else t("fmt.none")))
