"""Bausteine: Einstellungen speichern, Symbole, Schalter, Regler-Zeilen, Farbwahl, Preset-Karten, Modul-Spalten."""

import json
import locale
import math
import os
from pathlib import Path

import hyprstudio
from . import model, theme
from .i18n import t
from .qt import QtCore, QtGui, QtWidgets, Qt, Signal

CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "LabtosoStudios" / "hyprstudio.json"


def load_cfg() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        loc = (locale.getlocale()[0] or os.environ.get("LANG", "de")).lower()
        return {"lang": "en", "theme": "blue"}  # Standard: Englisch (Deutsch im Zahnrad-Menü)


def save_cfg(cfg: dict) -> None:
    try:
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


# ---------- gezeichnete Symbole ----------

def draw_icon(kind: str, color: str, size: int = 20) -> QtGui.QIcon:
    pm = QtGui.QPixmap(size * 2, size * 2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    p.scale(2, 2)
    p.setPen(QtGui.QPen(QtGui.QColor(color), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    c = size / 2
    if kind == "gear":
        teeth, ro, ri = 8, c * 0.9, c * 0.66
        path = QtGui.QPainterPath()
        for i in range(teeth * 4):
            a = (i / (teeth * 4)) * 2 * math.pi - math.pi / 2
            rad = ro if i % 4 in (1, 2) else ri
            pt = QtCore.QPointF(c + rad * math.cos(a), c + rad * math.sin(a))
            path.moveTo(pt) if i == 0 else path.lineTo(pt)
        path.closeSubpath()
        hole = QtGui.QPainterPath()
        hole.addEllipse(QtCore.QPointF(c, c), c * 0.28, c * 0.28)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(color))
        p.drawPath(path.subtracted(hole))
    elif kind == "close":
        m = size * 0.3
        p.drawLine(QtCore.QPointF(m, m), QtCore.QPointF(size - m, size - m))
        p.drawLine(QtCore.QPointF(size - m, m), QtCore.QPointF(m, size - m))
    elif kind == "min":
        m = size * 0.3
        p.drawLine(QtCore.QPointF(m, c), QtCore.QPointF(size - m, c))
    elif kind == "dots":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(color))
        for x in (0.25, 0.5, 0.75):
            p.drawEllipse(QtCore.QPointF(size * x, c), size * 0.08, size * 0.08)
    elif kind == "play":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(color))
        p.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(size * 0.32, size * 0.22), QtCore.QPointF(size * 0.8, c),
                                       QtCore.QPointF(size * 0.32, size * 0.78)]))
    p.end()
    return QtGui.QIcon(pm)


def app_icon() -> QtGui.QIcon:
    ic = QtGui.QIcon.fromTheme(hyprstudio.APP_ID)
    if not ic.isNull():
        return ic
    f = Path(__file__).parent / "assets" / "hyprstudio.svg"
    if f.is_file():
        return QtGui.QIcon(str(f))
    try:  # im .pyz
        import importlib.resources as res
        data = res.files("hyprstudio").joinpath("assets/hyprstudio.svg").read_bytes()
        pm = QtGui.QPixmap()
        pm.loadFromData(data, "SVG")
        return QtGui.QIcon(pm)
    except Exception:
        return QtGui.QIcon()


# ---------- Grundbausteine ----------

def set_chip(lb: QtWidgets.QLabel, ok: bool, text: str) -> None:
    """Statusschild (grün = ok, gelb = Hinweis); Stil direkt am Widget, damit die Größe stimmt."""
    col = theme.OK if ok else "#d29922"
    lb.setText(text)
    lb.setStyleSheet(f"QLabel {{ background: transparent; border: 1px solid {col}; border-radius: 10px;"
                     f" padding: 3px 10px; color: {col}; font-size: 9pt; font-weight: 600; }}")
    lb.setMinimumSize(0, 0)
    lb.setMaximumSize(16777215, 16777215)
    lb.adjustSize()
    lb.setFixedSize(lb.sizeHint())

class Segmented(QtWidgets.QFrame):
    changed = Signal(str)

    def __init__(self, keys, parent=None, prefix: str = ""):
        super().__init__(parent)
        self.setObjectName("SegBox")
        self.prefix = prefix
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self.group = QtWidgets.QButtonGroup(self)
        self.btns = {}
        for k in keys:
            b = QtWidgets.QPushButton()
            b.setObjectName("Seg")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=k: self.changed.emit(k))
            self.group.addButton(b)
            self.btns[k] = b
            lay.addWidget(b)

    def select(self, key) -> None:
        if key in self.btns:
            self.btns[key].setChecked(True)

    def retranslate(self):
        for k, b in self.btns.items():
            b.setText(t(f"{self.prefix}{k}").replace("&", "&&"))
            f = QtGui.QFont(b.font())
            f.setWeight(QtGui.QFont.Weight.DemiBold)
            b.setMinimumWidth(int(QtGui.QFontMetrics(f).horizontalAdvance(b.text())) + 30)


class Switch(QtWidgets.QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(42, 24)
        self.accent = theme.THEMES["blue"]
        self._pos = 0.0
        self._anim = QtCore.QVariantAnimation(self)
        self._anim.setDuration(140)
        self._anim.valueChanged.connect(self._move)
        self.toggled.connect(self._animate)

    def _move(self, v):
        self._pos = float(v)
        self.update()

    def _animate(self, on):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def set_now(self, on: bool):
        self.blockSignals(True)
        self.setChecked(on)
        self.blockSignals(False)
        self._pos = 1.0 if on else 0.0
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1)
        off, on = QtGui.QColor(theme.SURFACE2), QtGui.QColor(self.accent)
        c = QtGui.QColor(int(off.red() + (on.red() - off.red()) * self._pos),
                         int(off.green() + (on.green() - off.green()) * self._pos),
                         int(off.blue() + (on.blue() - off.blue()) * self._pos))
        p.setPen(QtGui.QPen(QtGui.QColor(theme.BORDER) if self._pos < 0.5 else c, 1))
        p.setBrush(c)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 6
        x = r.left() + 3 + (r.width() - d - 6) * self._pos
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor("#ffffff"))
        p.drawEllipse(QtCore.QRectF(x, r.top() + 3, d, d))
        p.end()


def _checker(p: QtGui.QPainter, r: QtCore.QRectF, s: float = 5):
    p.fillRect(r, QtGui.QColor("#d0d6de"))
    y, row = r.top(), 0
    while y < r.bottom():
        x = r.left() + (s if row % 2 else 0)
        while x < r.right():
            p.fillRect(QtCore.QRectF(x, y, s, s).intersected(r), QtGui.QColor("#9aa4b1"))
            x += 2 * s
        y += s
        row += 1


class ColorButton(QtWidgets.QPushButton):
    """Farbfeld mit Alpha (Schachbrett dahinter), öffnet einen Farbwähler mit Live-Vorschau."""
    color_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.color = "#3d8bfdff"
        self.setFixedSize(64, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self.pick)

    def set_color(self, c: str):
        self.color = model.norm(c)
        self.setToolTip(self.color)
        self.update()

    def pick(self):
        from .preview import qcolor
        old = self.color
        dlg = QtWidgets.QColorDialog(qcolor(old), self.window())
        dlg.setOption(QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel, True)
        dlg.setOption(QtWidgets.QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
        dlg.currentColorChanged.connect(lambda c: self._live(c))
        if dlg.exec():
            self._live(dlg.currentColor())
        else:
            self.set_color(old)
            self.color_changed.emit(old)

    def _live(self, c: QtGui.QColor):
        self.set_color(f"#{c.red():02x}{c.green():02x}{c.blue():02x}{c.alpha():02x}")
        self.color_changed.emit(self.color)

    def paintEvent(self, _):
        from .preview import qcolor
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QtGui.QPainterPath()
        path.addRoundedRect(r, 9, 9)
        p.setClipPath(path)
        _checker(p, r)
        p.fillRect(r, qcolor(self.color))
        p.setClipping(False)
        p.setPen(QtGui.QPen(QtGui.QColor(theme.TEXT if self.underMouse() else theme.BORDER), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r, 9, 9)
        p.end()


# ---------- Karten mit Zeilen ----------

class Card(QtWidgets.QFrame):
    """Karte mit Titel und Zeilen (Beschriftung | Steuerelement | Wert)."""

    def __init__(self, title_key: str, page, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.page = page
        self.title_key = title_key
        self.rows = []
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 16)
        lay.setSpacing(10)
        self.title = QtWidgets.QLabel()
        self.title.setObjectName("CardTitle")
        lay.addWidget(self.title)
        self.grid = QtWidgets.QGridLayout()
        self.grid.setHorizontalSpacing(14)
        self.grid.setVerticalSpacing(10)
        self.grid.setColumnStretch(1, 1)
        lay.addLayout(self.grid)

    def _label(self, key: str, tip: str | None = None) -> QtWidgets.QLabel:
        lb = QtWidgets.QLabel()
        lb.setObjectName("RowLabel")
        lb.setProperty("tkey", key)
        if tip:
            lb.setProperty("tipkey", tip)
        lb.setMinimumWidth(130)
        return lb

    def _add(self, key, widget, value=None, tip=None, refresh=None, label_key=None):
        r = self.grid.rowCount()
        lb = self._label(label_key or key, tip)
        self.grid.addWidget(lb, r, 0)
        if value is None:
            self.grid.addWidget(widget, r, 1, 1, 2, Qt.AlignmentFlag.AlignLeft)
        else:
            self.grid.addWidget(widget, r, 1)
            self.grid.addWidget(value, r, 2)
        self.rows.append((lb, refresh))
        return lb

    def slider(self, key, lo, hi, step=1.0, fmt="{:.0f}", tip=None, label_key=None):
        sl = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        sl.setRange(int(round(lo / step)), int(round(hi / step)))
        sl.setCursor(Qt.CursorShape.PointingHandCursor)
        val = QtWidgets.QLabel()
        val.setObjectName("Value")
        val.setMinimumWidth(44)
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        is_float = isinstance(self.page.state[key], float)

        def changed(i):
            v = i * step
            v = round(v, 4) if is_float else int(round(v))
            val.setText(fmt.format(v))
            self.page.set(key, v)

        def refresh(s):
            sl.blockSignals(True)
            sl.setValue(int(round(s[key] / step)))
            sl.blockSignals(False)
            val.setText(fmt.format(s[key]))
        sl.valueChanged.connect(changed)
        self._add(key, sl, val, tip, refresh, label_key=label_key)
        return sl

    def toggle(self, key, tip=None, label_key=None):
        sw = Switch()
        sw.toggled.connect(lambda on: self.page.set(key, bool(on)))
        self._add(key, sw, None, tip, lambda s: sw.set_now(bool(s[key])), label_key=label_key)
        self.page.switches.append(sw)
        return sw

    def color(self, key, label_key=None, tip=None):
        cb = ColorButton()
        cb.color_changed.connect(lambda c: self.page.set(key, c))
        self._add(key, cb, None, tip, lambda s: cb.set_color(s[key]), label_key=label_key)
        return cb

    def choice(self, key, options, prefix, tip=None, label_key=None):
        seg = Segmented(options, prefix=prefix)
        seg.changed.connect(lambda v: self.page.set(key, int(v) if isinstance(self.page.state[key], int) else v))
        self._add(key, seg, None, tip, lambda s: seg.select(str(s[key])), label_key=label_key)
        self.page.segs.append(seg)
        return seg

    def text(self, key, tip=None, width=220, label_key=None):
        le = QtWidgets.QLineEdit()
        le.setFixedWidth(width)
        le.textEdited.connect(lambda v: self.page.set(key, v.strip()))

        def refresh(s):
            if le.text().strip() != s[key]:
                le.setText(s[key])
        self._add(key, le, None, tip, refresh, label_key=label_key)
        return le

    def lines(self, key, tip=None):
        """Mehrzeiliges Feld: eine Zeile = ein Listeneintrag."""
        ed = QtWidgets.QPlainTextEdit()
        ed.setFixedHeight(110)
        ed.setMinimumWidth(380)
        ed.textChanged.connect(lambda: self.page.set(key, [x.strip() for x in ed.toPlainText().splitlines()
                                                           if x.strip()]))

        def refresh(s):
            if [x.strip() for x in ed.toPlainText().splitlines() if x.strip()] != s[key]:
                ed.blockSignals(True)
                ed.setPlainText("\n".join(s[key]))
                ed.blockSignals(False)
        self._add(key, ed, None, tip, refresh)
        return ed

    def refresh(self, s):
        for _, fn in self.rows:
            if fn:
                fn(s)

    def retranslate(self):
        self.title.setText(t(self.title_key))
        for lb, _ in self.rows:
            if not lb.property("tkey"):
                continue
            lb.setText(t(lb.property("tkey")))
            tip = lb.property("tipkey")
            if tip:
                lb.setToolTip(t(tip))


class PresetCard(QtWidgets.QFrame):
    clicked = Signal(str)

    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.setObjectName("Preset")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(212, 160)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 10)
        lay.setSpacing(8)
        self.pic = QtWidgets.QLabel()
        self.pic.setFixedSize(196, 110)
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.name = QtWidgets.QLabel()
        self.name.setStyleSheet("font-weight:600; background:transparent; padding-left:4px;")
        self.chip = QtWidgets.QLabel()
        self.chip.setObjectName("ChipOk")
        self.chip.hide()
        row.addWidget(self.name)
        row.addStretch()
        row.addWidget(self.chip)
        lay.addWidget(self.pic)
        lay.addLayout(row)

    def set_pixmap(self, pm):
        self.pic.setPixmap(pm)

    def refresh(self, selected: bool, accent: str, applied: bool = False):
        self.chip.setText(t("applied"))
        self.chip.setVisible(applied)
        border = accent if selected else theme.BORDER
        bg = theme.SURFACE2 if selected else theme.SURFACE
        self.setStyleSheet(f"#Preset {{ background:{bg}; border:{2 if selected else 1}px solid {border};"
                           f" border-radius:14px; }}")

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)


class FlowGrid(QtWidgets.QWidget):
    """Einfaches Raster, das die Spaltenzahl der Breite anpasst."""

    def __init__(self, cell_w: int, parent=None):
        super().__init__(parent)
        self.cell_w = cell_w
        self.items = []
        self.grid = QtWidgets.QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(14)
        self._cols = 0

    def add(self, w):
        self.items.append(w)
        self._relayout(force=True)

    def _relayout(self, force=False):
        cols = max(1, (self.width() + 14) // (self.cell_w + 14))
        if cols == self._cols and not force:
            return
        self._cols = cols
        for w in self.items:
            self.grid.removeWidget(w)
        for i, w in enumerate(self.items):
            self.grid.addWidget(w, i // cols, i % cols, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        for c in range(cols + 1):
            self.grid.setColumnStretch(c, 1 if c == cols else 0)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._relayout()


class ModuleColumns(QtWidgets.QWidget):
    """Vier Listen (Verfügbar, Links, Mitte, Rechts), Module per Ziehen verschieben."""
    changed = Signal()

    SIDES = ("avail", "left", "center", "right")

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.lists, self.heads = {}, {}
        self._loading = False
        for side in self.SIDES:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(6)
            h = QtWidgets.QLabel()
            h.setObjectName("RowLabel")
            lw = QtWidgets.QListWidget()
            lw.setObjectName("ModList")
            lw.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
            lw.setDefaultDropAction(Qt.DropAction.MoveAction)
            lw.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
            lw.setMinimumHeight(250)
            m = lw.model()
            m.rowsInserted.connect(self._later)
            m.rowsRemoved.connect(self._later)
            m.rowsMoved.connect(self._later)
            col.addWidget(h)
            col.addWidget(lw, 1)
            lay.addLayout(col)
            self.lists[side], self.heads[side] = lw, h
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self.changed.emit)

    def _later(self, *_):
        if not self._loading:
            self._timer.start()

    def load(self, s: dict):
        self._loading = True
        used = set(s["left"] + s["center"] + s["right"])
        data = {"avail": [m for m in model.MODULES if m not in used],
                "left": s["left"], "center": s["center"], "right": s["right"]}
        for side, lw in self.lists.items():
            lw.clear()
            for m in data[side]:
                it = QtWidgets.QListWidgetItem(t("m." + m))
                it.setData(Qt.ItemDataRole.UserRole, m)
                lw.addItem(it)
        self._loading = False

    def read(self) -> dict:
        out = {}
        for side in ("left", "center", "right"):
            lw = self.lists[side]
            seen = []
            for i in range(lw.count()):
                m = lw.item(i).data(Qt.ItemDataRole.UserRole)
                if m in model.MODULES and m not in seen:
                    seen.append(m)
            out[side] = seen
        return out

    def retranslate(self):
        for side, h in self.heads.items():
            h.setText(t("col." + side))
        for lw in self.lists.values():
            for i in range(lw.count()):
                it = lw.item(i)
                it.setText(t("m." + it.data(Qt.ItemDataRole.UserRole)))
        self.setToolTip(t("tip.modules"))


class SettingsPanel(QtWidgets.QFrame):
    lang_changed = Signal(str)
    theme_changed = Signal(str)
    reset_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setFixedWidth(300)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(22, 22, 22, 22)
        lay.setSpacing(12)
        self.title = QtWidgets.QLabel()
        self.title.setObjectName("PanelTitle")
        lay.addWidget(self.title)
        lay.addSpacing(10)
        self.l_lang = QtWidgets.QLabel()
        self.l_lang.setObjectName("Label")
        lay.addWidget(self.l_lang)
        row = QtWidgets.QHBoxLayout()
        self.lang_btns = {}
        grp = QtWidgets.QButtonGroup(self)
        for code, label in (("de", "Deutsch"), ("en", "English")):
            b = QtWidgets.QPushButton(label)
            b.setObjectName("Lang")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=code: self.lang_changed.emit(c))
            grp.addButton(b)
            self.lang_btns[code] = b
            row.addWidget(b)
        lay.addLayout(row)
        lay.addSpacing(10)
        self.l_theme = QtWidgets.QLabel()
        self.l_theme.setObjectName("Label")
        lay.addWidget(self.l_theme)
        row2 = QtWidgets.QHBoxLayout()
        row2.setSpacing(12)
        self.theme_btns = {}
        for name in theme.THEMES:
            b = QtWidgets.QPushButton()
            b.setFixedSize(38, 38)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip(name.capitalize())
            b.clicked.connect(lambda _=False, n=name: self.theme_changed.emit(n))
            self.theme_btns[name] = b
            row2.addWidget(b)
        row2.addStretch()
        lay.addLayout(row2)
        lay.addStretch()
        self.l_reset = QtWidgets.QLabel()
        self.l_reset.setObjectName("Label")
        lay.addWidget(self.l_reset)
        self.btn_reset = QtWidgets.QPushButton()
        self.btn_reset.setObjectName("DangerFill")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setMinimumHeight(40)
        self.btn_reset.clicked.connect(self.reset_requested.emit)
        lay.addWidget(self.btn_reset)
        lay.addSpacing(14)
        self.info = QtWidgets.QLabel()
        self.info.setObjectName("Label")
        self.info.setWordWrap(True)
        lay.addWidget(self.info)

    def sync(self, cfg: dict, info: str) -> None:
        self.title.setText(t("settings"))
        self.l_lang.setText(t("language"))
        self.l_theme.setText(t("theme"))
        self.l_reset.setText(t("reset.section"))
        self.btn_reset.setText(t("reset.button"))
        self.btn_reset.setToolTip(t("reset.tip"))
        self.lang_btns[cfg["lang"]].setChecked(True)
        for name, b in self.theme_btns.items():
            ring = "#ffffff" if name == cfg["theme"] else theme.SURFACE
            b.setStyleSheet(f"QPushButton {{ background:{theme.THEMES[name]}; border:3px solid {ring};"
                            f" border-radius:19px; padding:0; }}")
        self.info.setText(f"{info}\nv{hyprstudio.__version__} · LabtosoStudios")


class ResetDialog(QtWidgets.QDialog):
    """Bestätigung für „Alles zurücksetzen“: Knopf erst aktiv, wenn der Haken gesetzt ist."""

    def __init__(self, parent, lua_ok: bool):
        super().__init__(parent)
        self.setWindowTitle(t("reset.title"))
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        frame = QtWidgets.QFrame()
        frame.setObjectName("DialogFrame")
        outer.addWidget(frame)
        lay = QtWidgets.QVBoxLayout(frame)
        lay.setContentsMargins(24, 22, 24, 20)
        lay.setSpacing(12)
        title = QtWidgets.QLabel(t("reset.title"))
        title.setObjectName("PanelTitle")
        lay.addWidget(title)
        text = QtWidgets.QLabel(t("reset.text"))
        text.setWordWrap(True)
        lay.addWidget(text)
        self.factory = QtWidgets.QCheckBox(t("reset.factory"))
        self.factory.setEnabled(lua_ok)
        self.factory.setToolTip(t("reset.factory_tip") if lua_ok else t("reset.factory_off"))
        lay.addWidget(self.factory)
        lay.addSpacing(6)
        self.sure = QtWidgets.QCheckBox(t("reset.sure"))
        self.sure.setObjectName("Sure")
        lay.addWidget(self.sure)
        row = QtWidgets.QHBoxLayout()
        row.addStretch()
        cancel = QtWidgets.QPushButton(t("cancel"))
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        cancel.setDefault(True)
        self.ok = QtWidgets.QPushButton(t("reset.button"))
        self.ok.setObjectName("DangerFill")
        self.ok.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok.setEnabled(False)
        self.ok.clicked.connect(self.accept)
        self.sure.toggled.connect(self.ok.setEnabled)
        row.addWidget(cancel)
        row.addWidget(self.ok)
        lay.addLayout(row)
