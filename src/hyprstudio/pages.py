"""Seiten Hyprland und Waybar: Seitenleiste links, oben Live-Vorschau, darunter Presets bzw. Regler-Karten."""

from . import model, theme
from .i18n import t
from .preview import DesktopPreview, render_pixmap
from .qt import QtCore, QtWidgets, Qt
from .keys import BindEditor
from .widgets import Card, FlowGrid, ModuleColumns, PresetCard, draw_icon

KEEP_INPUT = ("kb_layout", "sensitivity", "follow_mouse", "natural_scroll", "no_logo", "binds")


class EditorPage(QtWidgets.QWidget):
    SECTIONS: tuple = ()
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
        acts = QtWidgets.QVBoxLayout()
        acts.setSpacing(8)
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
    SECTIONS = ("presets", "windows", "colors", "effects", "anim", "input", "keys")
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
            c = self.card(lay, "card.border")
            c.slider("border_size", 0, 8)
            c.slider("rounding", 0, 30)
            c.slider("rounding_power", 2, 10, 0.5, "{:.1f}", tip="tip.rounding_power")
            c = self.card(lay, "card.layout")
            c.choice("layout", ("dwindle", "master"), "layout.")
        elif key == "colors":
            c = self.card(lay, "card.border_col")
            c.color("active1", label_key="active")
            c.toggle("gradient")
            c.color("active2")
            c.slider("angle", 0, 360, 5, "{:.0f}°")
            c.color("inactive")
            c = self.card(lay, "card.shadow")
            c.color("shadow_color")
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
            c = self.card(lay, "card.shadow")
            c.toggle("shadow")
            c.slider("shadow_range", 0, 40)
            c.slider("shadow_power", 1, 4)
        elif key == "anim":
            c = self.card(lay, "card.anim")
            c.toggle("anim")
            c.choice("anim_curve", tuple(model.CURVES), "curve.")
            c.slider("anim_tempo", 0.5, 2.0, 0.1, "{:.1f}×", tip="tip.anim_tempo")
            c.choice("win_style", tuple(model.WIN_STYLES), "win.")
            c.choice("ws_style", tuple(model.WS_STYLES), "ws.")
        elif key == "input":
            c = self.card(lay, "card.kb")
            c.text("kb_layout", tip="tip.kb_layout", width=160)
            c.slider("sensitivity", -1.0, 1.0, 0.05, "{:+.2f}")
            c.choice("follow_mouse", ("0", "1", "2"), "fm.")
            c.toggle("natural_scroll")
            c = self.card(lay, "card.misc")
            c.toggle("no_logo")
        elif key == "keys":
            c = self.card(lay, "card.keys")
            self.binds = BindEditor()
            self.binds.changed.connect(self._binds_changed)
            self.binds.fix_requested.connect(self._fix_conflicts)
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
        return model.preset_state(name), self.win.waybar_page.state if hasattr(self.win, "waybar_page") else None

    def preset_value(self, name):
        s = model.preset_state(name)
        for k in KEEP_INPUT:
            s[k] = self.state[k]
        return s

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
    SECTIONS = ("presets", "bar", "modules", "style")
    KIND = "waybar"

    def __init__(self, win):
        super().__init__(win)
        self.btn_play.hide()
        self.preview.zoom_bar = True

    def load_state(self):
        return model.waybar_state(self.win.cfg.get("waybar"))

    def build_section(self, key, lay):
        if key == "presets":
            self.preset_grid(lay, model.WAYBAR_PRESETS, "wp.")
        elif key == "bar":
            c = self.card(lay, "card.shape")
            c.choice("position", ("top", "bottom"), "pos.")
            c.choice("style", ("bar", "float", "islands"), "st.")
            c = self.card(lay, "card.size")
            c.slider("height", 20, 60)
            c.slider("margin", 0, 30)
            c.slider("radius", 0, 30)
            c.slider("spacing", 0, 20)
            c.slider("border_width", 0, 4)
        elif key == "modules":
            c = self.card(lay, "sec.modules")
            self.mods = ModuleColumns()
            self.mods.changed.connect(self._mods_changed)
            c.layout().addWidget(self.mods)
            c.rows.append((QtWidgets.QLabel(), lambda s: self.mods.load(s)))
            c2 = self.card(lay, "card.extra")
            c2.text("launcher", width=260)
        elif key == "style":
            c = self.card(lay, "card.colors")
            c.color("bg")
            c.color("fg")
            c.color("accent")
            c.color("border")
            self.btn_from = QtWidgets.QPushButton()
            self.btn_from.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_from.clicked.connect(self.from_hypr)
            c.layout().addWidget(self.btn_from, 0, Qt.AlignmentFlag.AlignLeft)
            c = self.card(lay, "card.font")
            c.text("font", width=260)
            c.slider("font_size", 9, 24)
            c.toggle("icons")
            c.toggle("clock24")

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
