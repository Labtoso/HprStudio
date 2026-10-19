"""Tastenkürzel-Editor: Zeilen aus Modifikatoren, aufgenommener Taste, Aktion und Ziel."""

import sys

from . import model, theme
from .i18n import t
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
    """Klicken, dann Kombination drücken; Esc bricht ab."""
    captured = Signal(list, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("KeyBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(130)
        self.key = ""
        self.listening = False
        self.clicked.connect(self.start)

    def set_key(self, key: str):
        self.key = key
        self.listening = False
        self.setText(key or t("keys.none"))

    def start(self):
        self.listening = True
        self.setText(t("keys.press"))
        self.setFocus()
        self.grabKeyboard()

    def _stop(self):
        if self.listening:
            self.releaseKeyboard()
        self.set_key(self.key)

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
        self.action.setFixedWidth(210)
        for a in model.ACTIONS:
            self.action.addItem(t("act." + a), a)
        self.action.setCurrentIndex(list(model.ACTIONS).index(b["action"]))
        self.action.currentIndexChanged.connect(self._action_changed)
        lay.addWidget(self.action)
        self.arg = QtWidgets.QComboBox()
        self.arg.setMinimumWidth(200)
        self.arg.currentTextChanged.connect(lambda _: self.changed.emit())
        lay.addWidget(self.arg, 1)
        lay.addStretch(0)
        self.warn = QtWidgets.QLabel("!")
        self.warn.setObjectName("Warn")
        self.warn.setFixedSize(22, 22)
        self.warn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.warn.hide()
        lay.addWidget(self.warn)
        self.rm = QtWidgets.QToolButton()
        self.rm.setIcon(draw_icon("close", theme.MUTED, 16))
        self.rm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rm.setToolTip(t("keys.remove"))
        self.rm.clicked.connect(lambda: self.removed.emit(self))
        lay.addWidget(self.rm)
        self._fill_arg(b["arg"])

    def _captured(self, mods, _key):
        if mods:
            for m, btn in self.mods.items():
                btn.blockSignals(True)
                btn.setChecked(m in mods)
                btn.blockSignals(False)
        self.changed.emit()

    def _fill_arg(self, value: str):
        a = self.action.currentData()
        self.arg.blockSignals(True)
        self.arg.clear()
        need = model.ACTIONS[a]
        self.arg.setVisible(need)
        if a == "focus":
            self.arg.setEditable(False)
            for d in model.DIRECTIONS:
                self.arg.addItem(t("dir." + d), d)
            i = self.arg.findData(value)
            self.arg.setCurrentIndex(max(0, i))
        elif need:
            self.arg.setEditable(True)
            items = model.EXEC_SUGGEST if a == "exec" else [str(i) for i in range(1, 11)] + ["special:magic"]
            for it in items:
                self.arg.addItem(it, it)
            self.arg.setEditText(value or (items[0] if a != "exec" else ""))
        self.arg.blockSignals(False)

    def _action_changed(self):
        self._fill_arg("")
        self.changed.emit()

    def value(self) -> dict:
        a = self.action.currentData()
        if a == "focus":
            arg = self.arg.currentData() or ""
        elif model.ACTIONS[a]:
            arg = self.arg.currentText().strip()
        else:
            arg = ""
        return {"mods": [m for m, b in self.mods.items() if b.isChecked()], "key": self.keybtn.key,
                "action": a, "arg": arg}

    def set_warning(self, text: str | None):
        self.warn.setVisible(bool(text))
        self.warn.setToolTip(text or "")


class BindEditor(QtWidgets.QWidget):
    changed = Signal()
    fix_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        top = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton()
        self.btn_add.setObjectName("Primary")
        self.btn_defaults = QtWidgets.QPushButton()
        self.btn_fix = QtWidgets.QPushButton()
        self.btn_fix.setObjectName("Danger")
        for b in (self.btn_add, self.btn_defaults, self.btn_fix):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            top.addWidget(b)
        top.addStretch()
        self.count = QtWidgets.QLabel()
        self.count.setObjectName("RowLabel")
        top.addWidget(self.count)
        lay.addLayout(top)
        self.rows_lay = QtWidgets.QVBoxLayout()
        self.rows_lay.setSpacing(6)
        lay.addLayout(self.rows_lay)
        self.rows: list[BindRow] = []
        self.btn_add.clicked.connect(self.add_empty)
        self.btn_defaults.clicked.connect(lambda: (self.load(model.default_binds() + self.read()), self.changed.emit()))
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

    def _add_row(self, b: dict) -> BindRow:
        r = BindRow(b)
        r.changed.connect(self.changed.emit)
        r.removed.connect(self._remove)
        self.rows_lay.addWidget(r)
        self.rows.append(r)
        return r

    def add_empty(self):
        r = self._add_row({"mods": ["SUPER"], "key": "", "action": "exec", "arg": ""})
        r.keybtn.start()
        self.changed.emit()

    def _remove(self, row):
        self.rows.remove(row)
        row.hide()
        row.setParent(None)
        row.deleteLater()
        self.changed.emit()

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
        self.btn_defaults.setText(t("keys.defaults"))
        self.btn_fix.setText(t("keys.fix"))
        self.btn_fix.setToolTip(t("tip.keys.fix"))
        self.btn_defaults.setToolTip(t("tip.keys.defaults"))
        self.load(self.read())
