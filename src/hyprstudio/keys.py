"""Tastenkürzel-Editor: Zeilen aus Modifikatoren, aufgenommener Taste, Aktion und Ziel."""

import sys

from . import model, theme
from .i18n import TEXT, t
from .qt import QtCore, QtGui, QtWidgets, Qt, Signal
from .widgets import draw_icon

K = Qt.Key
KEYNAMES = {
    K.Key_Return: "Return", K.Key_Enter: "Return", K.Key_Space: "space", K.Key_Tab: "Tab",
    K.Key_Backspace: "BackSpace", K.Key_Delete: "Delete", K.Key_Insert: "Insert", K.Key_Print: "Print",
    K.Key_Left: "left", K.Key_Right: "right", K.Key_Up: "up", K.Key_Down: "down",
    K.Key_Home: "Home", K.Key_End: "End", K.Key_PageUp: "Prior", K.Key_PageDown: "Next",
    K.Key_Comma: "comma", K.Key_Period: "period", K.Key_Minus: "minus", K.Key_Plus: "plus",
    K.Key_Slash: "slash", K.Key_Semicolon: "semicolon", K.Key_QuoteLeft: "grave",
    K.Key_VolumeUp: "XF86AudioRaiseVolume", K.Key_VolumeDown: "XF86AudioLowerVolume",
    K.Key_VolumeMute: "XF86AudioMute", K.Key_MediaPlay: "XF86AudioPlay", K.Key_MediaTogglePlayPause: "XF86AudioPlay",
    K.Key_MediaNext: "XF86AudioNext", K.Key_MediaPrevious: "XF86AudioPrev",
    K.Key_MonBrightnessUp: "XF86MonBrightnessUp", K.Key_MonBrightnessDown: "XF86MonBrightnessDown",
}
MOD_KEYS = (K.Key_Shift, K.Key_Control, K.Key_Alt, K.Key_Meta, K.Key_Super_L, K.Key_Super_R, K.Key_AltGr,
            K.Key_CapsLock)


def key_name(e: QtGui.QKeyEvent) -> str | None:
    k = e.key()
    sc = e.nativeScanCode()
    # Zahlenreihe über die Position, damit SHIFT + 1 nicht zu „!“ wird
    if sys.platform.startswith("linux") and 10 <= sc <= 19:
        return str((sc - 9) % 10)
    if sys.platform == "win32" and 2 <= sc <= 11:
        return str((sc - 1) % 10)
    if K.Key_A.value <= _v(k) <= K.Key_Z.value or K.Key_0.value <= _v(k) <= K.Key_9.value:
        return chr(_v(k))
    if K.Key_F1.value <= _v(k) <= K.Key_F24.value:
        return f"F{_v(k) - K.Key_F1.value + 1}"
    for qk, name in KEYNAMES.items():
        if _v(qk) == _v(k):
            return name
    txt = QtGui.QKeySequence(_v(k)).toString()
    return txt or None


def _v(k) -> int:
    return k.value if hasattr(k, "value") else int(k)


class KeyButton(QtWidgets.QPushButton):
    """Linksklick: Kombination drücken (Esc bricht ab). Rechtsklick: Sondertasten oder von Hand eingeben."""
    captured = Signal(list, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("KeyBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(150)
        self.key = ""
        self.listening = False
        self.clicked.connect(self.start)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)

    def set_key(self, key: str):
        self.key = key
        self.listening = False
        self.setText(QtGui.QFontMetrics(self.font()).elidedText(key or t("keys.none"),
                                                                 Qt.TextElideMode.ElideMiddle, 132))
        self.setToolTip(t("tip.keybtn") + (f"\n{key}" if key else ""))

    def start(self):
        self.listening = True
        self.setText(t("keys.press"))
        self.setFocus()
        self.grabKeyboard()

    def _stop(self):
        if self.listening:
            self.releaseKeyboard()
        self.set_key(self.key)

    def _menu(self, pos):
        m = QtWidgets.QMenu(self)
        manual = m.addAction(t("keys.manual"))
        m.addSeparator()
        for k in model.SPECIAL_KEYS:
            m.addAction(t("key." + k) if ("key." + k) in TEXT["de"] else k).setData(k)
        a = m.exec(self.mapToGlobal(pos))
        if a is None:
            return
        if a is manual:
            txt, ok = QtWidgets.QInputDialog.getText(self, t("keys.manual"), t("keys.manual_q"), text=self.key)
            if ok and txt.strip():
                self.set_key(txt.strip())
                self.captured.emit([], self.key)
        elif a.data():
            self.set_key(a.data())
            self.captured.emit([], self.key)

    def keyPressEvent(self, e):
        if not self.listening:
            return super().keyPressEvent(e)
        if _v(e.key()) in {_v(k) for k in MOD_KEYS}:
            return
        if _v(e.key()) == _v(K.Key_Escape):
            self._stop()
            return
        name = key_name(e)
        if not name:
            return
        m = e.modifiers()
        mods = [mod for mod, flag in (("SUPER", Qt.KeyboardModifier.MetaModifier),
                                      ("SHIFT", Qt.KeyboardModifier.ShiftModifier),
                                      ("CTRL", Qt.KeyboardModifier.ControlModifier),
                                      ("ALT", Qt.KeyboardModifier.AltModifier)) if m & flag]
        self.releaseKeyboard()
        self.set_key(name)
        self.captured.emit(mods, name)

    def focusOutEvent(self, e):
        self._stop()
        super().focusOutEvent(e)


class BindRow(QtWidgets.QFrame):
    changed = Signal()
    removed = Signal(object)
    duplicated = Signal(object)

    def __init__(self, b: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("BindRow")
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 8, 8)
        lay.setSpacing(6)
        self.mods = {}
        for m in model.MODS:
            btn = QtWidgets.QPushButton(t("mod." + m))
            btn.setObjectName("Mod")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setChecked(m in b["mods"])
            btn.toggled.connect(lambda _=False: self.changed.emit())
            btn.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
            self.mods[m] = btn
            lay.addWidget(btn)
        self.keybtn = KeyButton()
        self.keybtn.set_key(b["key"])
        self.keybtn.captured.connect(self._captured)
        lay.addWidget(self.keybtn)
        lay.addSpacing(6)
        self.action = QtWidgets.QComboBox()
        self.action.setFixedWidth(220)
        self.action.setMaxVisibleItems(20)
        for a in model.ACTIONS:
            self.action.addItem(t("act." + a), a)
        self.action.setCurrentIndex(list(model.ACTIONS).index(b["action"]))
        self.action.currentIndexChanged.connect(self._action_changed)
        lay.addWidget(self.action)
        self.arg = QtWidgets.QComboBox()
        self.arg.setMinimumWidth(200)
        self.arg.setMaxVisibleItems(20)
        self.arg.currentTextChanged.connect(lambda _: self.changed.emit())
        lay.addWidget(self.arg, 1)
        lay.addStretch(0)
        self.warn = QtWidgets.QLabel("!")
        self.warn.setObjectName("Warn")
        self.warn.setFixedSize(22, 22)
        self.warn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.warn.hide()
        lay.addWidget(self.warn)
        # Flags + Duplizieren im Menü
        self.more = QtWidgets.QToolButton()
        self.more.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.more.setCursor(Qt.CursorShape.PointingHandCursor)
        menu = QtWidgets.QMenu(self.more)
        self.flag_acts = {}
        for f in model.FLAGS:
            a = menu.addAction(t("flag." + f))
            a.setCheckable(True)
            a.setChecked(f in b.get("flags", []))
            a.toggled.connect(self._flags_changed)
            self.flag_acts[f] = a
        menu.addSeparator()
        menu.addAction(t("keys.duplicate")).triggered.connect(lambda: self.duplicated.emit(self))
        self.more.setMenu(menu)
        lay.addWidget(self.more)
        self.rm = QtWidgets.QToolButton()
        self.rm.setIcon(draw_icon("close", theme.MUTED, 16))
        self.rm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rm.setToolTip(t("keys.remove"))
        self.rm.clicked.connect(lambda: self.removed.emit(self))
        lay.addWidget(self.rm)
        self._fill_arg(b["arg"])
        self._flags_changed()

    def _flags_changed(self, *_):
        on = [f for f, a in self.flag_acts.items() if a.isChecked()]
        self.more.setIcon(draw_icon("dots", theme.THEMES["blue"] if on else theme.MUTED, 16))
        self.more.setToolTip(t("keys.flags") + (": " + ", ".join(t("flag." + f) for f in on) if on else ""))
        self.changed.emit()

    def _captured(self, mods, _key):
        if mods:
            for m, btn in self.mods.items():
                btn.blockSignals(True)
                btn.setChecked(m in mods)
                btn.blockSignals(False)
        self.changed.emit()

    def _fill_arg(self, value: str):
        a = self.action.currentData()
        kind = model.ACTIONS[a]
        self.arg.blockSignals(True)
        self.arg.clear()
        self.arg.setVisible(kind is not None)
        if kind == "dir":
            self.arg.setEditable(False)
            for d in model.DIRECTIONS:
                self.arg.addItem(t("dir." + d), d)
            self.arg.setCurrentIndex(max(0, self.arg.findData(value)))
        elif kind:
            self.arg.setEditable(True)
            items = list(model.EXEC_SUGGEST) if kind == "cmd" else [str(i) for i in range(1, 11)]
            for it in items:
                self.arg.addItem(it, it)
            self.arg.setEditText(value or ("" if kind == "cmd" else "1"))
        self.arg.blockSignals(False)

    def _action_changed(self):
        self._fill_arg("")
        self.changed.emit()

    def value(self) -> dict:
        a = self.action.currentData()
        kind = model.ACTIONS[a]
        if kind == "dir":
            arg = self.arg.currentData() or ""
        elif kind:
            arg = self.arg.currentText().strip()
        else:
            arg = ""
        return {"mods": [m for m, b in self.mods.items() if b.isChecked()], "key": self.keybtn.key,
                "action": a, "arg": arg, "flags": [f for f, x in self.flag_acts.items() if x.isChecked()]}

    def text(self) -> str:
        v = self.value()
        return " ".join([model.combo_text(v), t("act." + v["action"]), v["arg"]]).lower()

    def set_warning(self, text: str | None):
        self.warn.setVisible(bool(text))
        self.warn.setToolTip(text or "")


class BindEditor(QtWidgets.QWidget):
    changed = Signal()
    fix_requested = Signal()
    import_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        top = QtWidgets.QHBoxLayout()
        top.setSpacing(8)
        self.btn_add = QtWidgets.QPushButton()
        self.btn_add.setObjectName("Primary")
        self.btn_tpl = QtWidgets.QPushButton()
        self.tpl_menu = QtWidgets.QMenu(self.btn_tpl)
        self.btn_tpl.setMenu(self.tpl_menu)
        self.btn_import = QtWidgets.QPushButton()
        self.btn_fix = QtWidgets.QPushButton()
        self.btn_fix.setObjectName("Danger")
        for b in (self.btn_add, self.btn_tpl, self.btn_import, self.btn_fix):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            top.addWidget(b)
        top.addStretch()
        self.search = QtWidgets.QLineEdit()
        self.search.setObjectName("Search")
        self.search.setFixedWidth(200)
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        top.addWidget(self.search)
        self.count = QtWidgets.QLabel()
        self.count.setObjectName("RowLabel")
        top.addWidget(self.count)
        lay.addLayout(top)
        self.rows_lay = QtWidgets.QVBoxLayout()
        self.rows_lay.setSpacing(6)
        lay.addLayout(self.rows_lay)
        self.rows: list[BindRow] = []
        self.btn_add.clicked.connect(self.add_empty)
        self.btn_import.clicked.connect(self.import_requested.emit)
        self.btn_fix.clicked.connect(self.fix_requested.emit)
        self.btn_fix.hide()

    def load(self, binds: list):
        for r in self.rows:
            r.hide()
            r.setParent(None)
            r.deleteLater()
        self.rows = []
        seen = set()
        for b in binds:
            c = model.combo(b["mods"], b["key"])
            if b["key"] and c in seen:
                continue
            seen.add(c)
            self._add_row(b)
        self._filter()

    def merge(self, binds: list):
        """Neue Kürzel anhängen; schon vorhandene Tastenkombinationen bleiben unverändert."""
        self.load(self.read() + binds)
        self.changed.emit()

    def _add_row(self, b: dict, after: BindRow | None = None) -> BindRow:
        r = BindRow(b)
        r.changed.connect(self.changed.emit)
        r.removed.connect(self._remove)
        r.duplicated.connect(self._duplicate)
        if after is not None:
            i = self.rows.index(after) + 1
            self.rows_lay.insertWidget(i, r)
            self.rows.insert(i, r)
        else:
            self.rows_lay.addWidget(r)
            self.rows.append(r)
        return r

    def add_empty(self):
        self.search.clear()
        r = self._add_row({"mods": ["SUPER"], "key": "", "action": "exec", "arg": "", "flags": []})
        r.keybtn.start()
        self.changed.emit()

    def _duplicate(self, row):
        v = row.value()
        v["key"] = ""
        r = self._add_row(v, after=row)
        r.keybtn.start()
        self.changed.emit()

    def _remove(self, row):
        self.rows.remove(row)
        row.hide()
        row.setParent(None)
        row.deleteLater()
        self.changed.emit()

    def _filter(self, *_):
        q = self.search.text().strip().lower()
        for r in self.rows:
            r.setVisible(not q or all(w in r.text() for w in q.split()))

    def read(self) -> list:
        return [r.value() for r in self.rows]

    def mark(self, conflicts: set):
        """Doppelte Kombinationen und Treffer in hyprland.lua markieren."""
        counts = {}
        for r in self.rows:
            v = r.value()
            if v["key"]:
                c = model.combo(v["mods"], v["key"])
                counts[c] = counts.get(c, 0) + 1
        for r in self.rows:
            v = r.value()
            c = model.combo(v["mods"], v["key"])
            if v["key"] and counts.get(c, 0) > 1:
                r.set_warning(t("keys.dup"))
            elif v["key"] and c in conflicts:
                r.set_warning(t("keys.conflict"))
            else:
                r.set_warning(None)
        self.btn_fix.setVisible(bool(conflicts))
        self.count.setText(t("keys.count", n=len([r for r in self.rows if model.bind_ok(r.value())])))

    def retranslate(self):
        self.btn_add.setText(t("keys.add"))
        self.btn_tpl.setText(t("keys.templates"))
        self.btn_import.setText(t("keys.import"))
        self.btn_import.setToolTip(t("tip.keys.import"))
        self.btn_fix.setText(t("keys.fix"))
        self.btn_fix.setToolTip(t("tip.keys.fix"))
        self.search.setPlaceholderText(t("search"))
        self.tpl_menu.clear()
        for name in model.TEMPLATES:
            self.tpl_menu.addAction(t("tpl." + name)).triggered.connect(
                lambda _=False, n=name: self.merge([dict(b) for b in model.TEMPLATES[n]]))
        self.tpl_menu.addSeparator()
        self.tpl_menu.addAction(t("tpl.all")).triggered.connect(lambda: self.merge(
            [dict(b) for n in model.TEMPLATES for b in model.TEMPLATES[n]]))
        self.load(self.read())
