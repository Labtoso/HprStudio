"""Hyprland › Hintergrundbild (Hyprpaper) und › Mauszeiger (Hyprcursor/XCursor).
Beide haben eine Bibliothek bzw. Suche und können Neues aus dem Netz installieren (online.py)."""

import os
from pathlib import Path

from . import model, online, paper
from .i18n import t
from .qt import QtCore, QtGui, QtWidgets, Qt, Signal
from .widgets import Card, FlowGrid, Switch, set_chip
from .workspaces import monitors


def _load(path: str, w: int, h: int) -> QtGui.QImage:
    """Bild verkleinert laden (schnell auch bei großen Dateien)."""
    r = QtGui.QImageReader(path)
    r.setAutoTransform(True)
    size = r.size()
    if size.isValid() and size.width() > 0:
        scale = max(w / size.width(), h / size.height())
        r.setScaledSize(QtCore.QSize(max(1, int(size.width() * scale)), max(1, int(size.height() * scale))))
    return r.read()


def _thumb(path: str, w: int, h: int, radius: int = 12) -> QtGui.QPixmap:
    pm = QtGui.QPixmap(w, h)
    pm.fill(Qt.GlobalColor.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
    clip = QtGui.QPainterPath()
    clip.addRoundedRect(QtCore.QRectF(0, 0, w, h), radius, radius)
    p.setClipPath(clip)
    full = os.path.expanduser(path) if path else ""
    img = QtGui.QImage()
    if full and Path(full).is_dir():  # Ordner: erstes Bild zeigen
        for f in sorted(Path(full).iterdir()):
            if f.suffix.lower() in paper.IMAGE_EXT:
                img = _load(str(f), w, h)
                if not img.isNull():
                    break
    elif full:
        img = _load(full, w, h)
    if img.isNull():
        p.fillRect(QtCore.QRectF(0, 0, w, h), QtGui.QColor("#1b2430"))
        p.setPen(QtGui.QColor("#8a98ab"))
        p.drawText(QtCore.QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, t("paper.none"))
    else:
        scale = max(w / img.width(), h / img.height())
        sw, sh = w / scale, h / scale
        p.drawImage(QtCore.QRectF(0, 0, w, h), img, QtCore.QRectF((img.width() - sw) / 2, (img.height() - sh) / 2, sw, sh))
    p.end()
    return pm


def _pick(parent, folder: bool, start: str) -> str:
    start = os.path.expanduser(start) if start else str(online.wall_dir() if online.wall_dir().is_dir() else Path.home())
    if folder:
        return QtWidgets.QFileDialog.getExistingDirectory(parent, t("paper.folder"), start)
    path, _ = QtWidgets.QFileDialog.getOpenFileName(parent, t("paper.image"), start,
                                                    "Bilder (*.png *.jpg *.jpeg *.webp *.jxl *.bmp)")
    return path


def _short(path: str) -> str:
    home = str(Path.home())
    return "~" + path[len(home):] if path.startswith(home) else path


def _btn(primary: bool = False) -> QtWidgets.QPushButton:
    b = QtWidgets.QPushButton()
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary:
        b.setObjectName("Primary")
    return b


def _action(primary: bool = False) -> QtWidgets.QPushButton:
    """Knopf für die Kopfzeile (Anwenden/Rückgängig) – überall gleich groß."""
    b = _btn(primary)
    b.setFixedSize(170, 40)
    return b


def card_header(card: Card, *widgets) -> None:
    """Titel der Karte links, Knöpfe rechts in derselben Zeile."""
    lay = card.layout()
    lay.removeWidget(card.title)
    row = QtWidgets.QHBoxLayout()
    row.setSpacing(8)
    row.addWidget(card.title)
    row.addStretch()
    for w in widgets:
        row.addWidget(w)
    lay.insertLayout(0, row)


def _scroll(owner: QtWidgets.QWidget) -> QtWidgets.QVBoxLayout:
    outer = QtWidgets.QVBoxLayout(owner)
    outer.setContentsMargins(0, 0, 0, 0)
    sa = QtWidgets.QScrollArea()
    sa.setWidgetResizable(True)
    sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    inner = QtWidgets.QWidget()
    inner.setObjectName("ScrollInner")
    lay = QtWidgets.QVBoxLayout(inner)
    lay.setContentsMargins(0, 0, 6, 0)
    lay.setSpacing(14)
    sa.setWidget(inner)
    outer.addWidget(sa)
    return lay


class Job(QtCore.QThread):
    """Download im Hintergrund; Protokollzeilen und Ergebnis kommen als Signal in den GUI-Thread."""
    line = Signal(str)
    result = Signal(object)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn

    def run(self):
        try:
            r = self.fn(self.line.emit)
        except Exception as e:  # noqa: BLE001 – Netzfehler sauber melden
            r = e
        self.result.emit(r)


class Thumb(QtWidgets.QLabel):
    clicked = Signal(str)

    def __init__(self, path: Path, parent=None):
        super().__init__(parent)
        self.path = str(path)
        self.setFixedSize(176, 99)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(online.short(path))

    def mark(self, on: bool, accent: str):
        self.setStyleSheet(f"border: 2px solid {accent}; border-radius: 12px;" if on
                           else "border: 2px solid transparent; border-radius: 12px;")

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.path)


class PaperEditor(QtWidgets.QWidget):
    KIND = "paper"

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.state = paper.paper_state(win.cfg.get("paper"))
        self.cards, self.switches, self.segs = [], [], []
        self.job = None
        self.thumbs = []
        self._todo = []
        self.btn_undo, self.btn_apply = _action(), _action(True)
        self.btn_apply.clicked.connect(self.apply)
        self.btn_undo.clicked.connect(self.undo)
        self.actions = [self.btn_undo, self.btn_apply]
        lay = _scroll(self)

        # Alle Monitore
        c = Card("paper.all", self)
        self.cards.append(c)
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(16)
        self.thumb = QtWidgets.QLabel()
        self.thumb.setFixedSize(320, 180)
        row.addWidget(self.thumb)
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(8)
        self.path_lbl = QtWidgets.QLabel()
        self.path_lbl.setObjectName("Mono")
        self.path_lbl.setWordWrap(True)
        col.addWidget(self.path_lbl)
        self.btn_img, self.btn_dir = _btn(), _btn()
        for b in (self.btn_img, self.btn_dir):
            b.setMinimumWidth(220)
            col.addWidget(b, 0, Qt.AlignmentFlag.AlignLeft)
        self.btn_img.clicked.connect(lambda: self._choose("", False))
        self.btn_dir.clicked.connect(lambda: self._choose("", True))
        col.addStretch()
        row.addLayout(col, 1)
        c.layout().addLayout(row)
        c.choice("fit", paper.FITS, "fit.", label_key="paper.fit")
        lay.addWidget(c)

        # Bibliothek: installierte Bilder, Klick = für alle Monitore
        self.lib_card = Card("paper.lib", self)
        self.cards.append(self.lib_card)
        self.btn_get = _btn(True)
        self.btn_get.clicked.connect(self._get_menu)
        self.btn_lib_open = _btn()
        self.btn_lib_open.clicked.connect(lambda: online.open_dir(online.wall_dir()))
        card_header(self.lib_card, self.btn_lib_open, self.btn_get)
        self.lib_empty = QtWidgets.QLabel()
        self.lib_empty.setObjectName("RowLabel")
        self.lib_card.layout().addWidget(self.lib_empty)
        self.grid = FlowGrid(176)
        self.lib_card.layout().addWidget(self.grid)
        lay.addWidget(self.lib_card)

        # Pro Monitor
        self.mon_card = Card("paper.per_monitor", self)
        self.cards.append(self.mon_card)
        self.mon_lay = QtWidgets.QVBoxLayout()
        self.mon_lay.setSpacing(8)
        self.mon_card.layout().addLayout(self.mon_lay)
        lay.addWidget(self.mon_card)

        # Diashow + Sonstiges
        c = Card("paper.extra", self)
        self.cards.append(c)
        c.slider("timeout", 5, 600, 5, "{:.0f} s", label_key="paper.timeout", tip="tip.paper.timeout")
        c.toggle("random", label_key="paper.random")
        c.toggle("recursive", label_key="paper.recursive")
        c.toggle("splash", label_key="paper.splash")
        self.auto = Switch()
        self.auto.toggled.connect(self._autostart)
        c._add("paper.autostart", self.auto, None, "tip.paper.autostart", None, label_key="paper.autostart")
        self.switches.append(self.auto)
        lay.addWidget(c)
        lay.addStretch()
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._thumb_step)
        self.refresh_controls()

    # ----- Zustand -----
    def set(self, key, value):
        self.state[key] = value
        self.changed()

    def changed(self):
        self.win.cfg["paper"] = self.state
        self.win.save_later()
        self.thumb.setPixmap(_thumb(self.state["path"], 320, 180))
        self.path_lbl.setText(_short(self.state["path"]))
        self.path_lbl.setVisible(bool(self.state["path"]))
        self._mark()

    def refresh_controls(self):
        for c in self.cards:
            c.refresh(self.state)
        self.auto.set_now("hyprpaper" in self.win.hypr_page.state["autostart"])
        self._monitors()
        self.changed()

    def refresh(self):
        """Beim Öffnen des Bereichs: Bibliothek neu einlesen."""
        self.load_library()

    # ----- Bibliothek -----
    def load_library(self):
        self._timer.stop()
        for w in self.grid.items:
            w.hide()
            w.setParent(None)
            w.deleteLater()
        self.grid.items, self.thumbs = [], []
        files = online.library_images(60)
        for f in files:
            th = Thumb(f)
            th.clicked.connect(self._lib_pick)
            self.grid.add(th)
            self.thumbs.append(th)
        self._todo = list(self.thumbs)
        self.lib_empty.setText(t("paper.lib_empty", dir=online.short(online.wall_dir())))
        self.lib_empty.setVisible(not files)
        self._mark()
        self._timer.start(15)

    def _thumb_step(self):
        for _ in range(3):  # ein paar pro Takt, damit die Oberfläche flüssig bleibt
            if not self._todo:
                self._timer.stop()
                return
            th = self._todo.pop(0)
            th.setPixmap(_thumb(th.path, 172, 95, 10))

    def _mark(self):
        acc = self.win.accent()
        for th in self.thumbs:
            th.mark(th.path == os.path.expanduser(self.state["path"]), acc)

    def _lib_pick(self, path: str):
        self.state["path"] = path
        self.changed()
        self._monitors()
        self.win.set_status(t("paper.picked", name=Path(path).name))

    def _get_menu(self):
        m = QtWidgets.QMenu(self)
        for pack in online.WALL_PACKS:
            a = m.addAction(t("paper.pack", name=pack[1], n=online.MAX_WALLS))
            a.triggered.connect(lambda _=False, p=pack: self._install(p))
        m.exec(self.btn_get.mapToGlobal(QtCore.QPoint(0, self.btn_get.height() + 4)))

    def _install(self, pack):
        if self.job:
            return
        self.win.log("")
        self.win.set_status(t("dl.loading", name=pack[1]))
        self.btn_get.setEnabled(False)
        self.job = Job(lambda log: online.install_walls(pack, log), self)
        self.job.line.connect(self.win.log)
        self.job.result.connect(lambda r, p=pack: self._installed(p, r))
        self.job.start()

    def _installed(self, pack, r):
        self.job = None
        self.btn_get.setEnabled(True)
        if isinstance(r, Exception):
            self.win.log(f"Fehler: {r}")
            self.win.set_status(t("dl.fail", err=r))
            return
        self.win.set_status(t("paper.got", name=pack[1], n=r))
        self.load_library()

    # ----- Auswahl -----
    def _choose(self, mon: str, folder: bool):
        cur = self.state["monitors"].get(mon, {}).get("path", "") if mon else self.state["path"]
        path = _pick(self, folder, cur)
        if not path:
            return
        if mon:
            self.state["monitors"][mon] = {"path": path, "fit": self.state["fit"]}
            self._monitors()
        else:
            self.state["path"] = path
        self.changed()

    def _clear(self, mon: str):
        self.state["monitors"].pop(mon, None)
        self._monitors()
        self.changed()

    def _monitors(self):
        while self.mon_lay.count():
            w = self.mon_lay.takeAt(0).widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        for mon in sorted(set(monitors()) | set(self.state["monitors"])):
            m = self.state["monitors"].get(mon)
            row = QtWidgets.QFrame()
            row.setObjectName("BindRow")
            rl = QtWidgets.QHBoxLayout(row)
            rl.setContentsMargins(12, 8, 10, 8)
            rl.setSpacing(10)
            th = QtWidgets.QLabel()
            th.setPixmap(_thumb(m["path"] if m else self.state["path"], 96, 54, 8))
            name = QtWidgets.QLabel(mon)
            name.setObjectName("Mono")
            name.setFixedWidth(110)
            path = QtWidgets.QLabel(_short(m["path"]) if m else t("paper.same"))
            path.setObjectName("RowLabel")
            rl.addWidget(th)
            rl.addWidget(name)
            rl.addWidget(path, 1)
            btns = [(t("paper.image_btn"), lambda _=False, x=mon: self._choose(x, False)),
                    (t("paper.folder_btn"), lambda _=False, x=mon: self._choose(x, True))]
            if m:
                btns.append((t("paper.reset"), lambda _=False, x=mon: self._clear(x)))
            for txt, fn in btns:
                b = _btn()
                b.setText(txt)
                b.setMinimumWidth(96)
                b.clicked.connect(fn)
                rl.addWidget(b)
            self.mon_lay.addWidget(row)
        self.mon_card.setVisible(self.mon_lay.count() > 0)

    def _autostart(self, on: bool):
        hp = self.win.hypr_page
        cmds = [c for c in hp.state["autostart"] if c.strip() != "hyprpaper"]
        if on:
            cmds.insert(0, "hyprpaper")
        hp.state["autostart"] = cmds
        hp.refresh_controls()
        hp.changed()
        self.win.set_status(t("paper.auto_hint"))

    def apply(self):
        self.win.log("")
        ok, info = paper.apply_paper(self.state, model.config_home() / "hypr", self.win.log)
        self.win.set_status(t("done") if ok else t(info))

    def undo(self):
        ok = model.undo_file(model.config_home() / "hypr" / "hyprpaper.conf")
        if ok:
            paper.restart_paper(self.win.log)
        self.win.set_status(t("undone") if ok else t("nothing"))

    def retranslate(self):
        for c in self.cards:
            c.retranslate()
        for sg in self.segs:
            sg.retranslate()
        self.btn_img.setText(t("paper.image"))
        self.btn_dir.setText(t("paper.folder"))
        self.btn_get.setText(t("paper.get"))
        self.btn_lib_open.setText(t("paper.open"))
        self.btn_undo.setText(t("undo"))
        self.btn_apply.setText(t("apply"))
        self.lib_empty.setText(t("paper.lib_empty", dir=online.short(online.wall_dir())))
        self._monitors()
        self.changed()

    def apply_theme(self, accent):
        for sw in self.switches:
            sw.accent = accent
            sw.update()
        self._mark()


class CursorEditor(QtWidgets.QWidget):
    """Mauszeiger: suchen, installierte wählen, neue aus dem Netz installieren, Größe, auch für GTK-Apps."""

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.job = None
        self.state = {}
        self.btn_apply = _action(True)
        self.btn_apply.clicked.connect(self.apply)
        self.actions = [self.btn_apply]
        lay = _scroll(self)

        self.search = QtWidgets.QLineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumHeight(40)
        self.search.textChanged.connect(self._filter)
        lay.addWidget(self.search)

        # Installiert
        self.inst_card = Card("cur.title", self)
        self.btn_refresh, self.btn_open = _btn(), _btn()
        self.btn_refresh.clicked.connect(self.load)
        self.btn_open.clicked.connect(lambda: online.open_dir(online.icons_dir()))
        card_header(self.inst_card, self.btn_refresh, self.btn_open)
        self.list = QtWidgets.QListWidget()
        self.list.setObjectName("ModList")
        self.list.setMinimumHeight(220)
        self.list.currentItemChanged.connect(self._picked)
        self.inst_card.layout().addWidget(self.list)
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        self.l_size = QtWidgets.QLabel()
        self.l_size.setObjectName("RowLabel")
        self.l_size.setMinimumWidth(130)
        self.size = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.size.setRange(8, 32)  # ×2 → 16 … 64
        self.size_val = QtWidgets.QLabel()
        self.size_val.setObjectName("Value")
        self.size_val.setMinimumWidth(44)
        self.size_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.size.valueChanged.connect(lambda v: self.size_val.setText(f"{v * 2} px"))
        self.l_gtk = QtWidgets.QLabel()
        self.l_gtk.setObjectName("RowLabel")
        self.gtk = Switch()
        self.gtk.set_now(bool(win.cfg.get("cursor_gtk", True)))
        grid.addWidget(self.l_size, 0, 0)
        grid.addWidget(self.size, 0, 1)
        grid.addWidget(self.size_val, 0, 2)
        grid.addWidget(self.l_gtk, 1, 0)
        grid.addWidget(self.gtk, 1, 1, Qt.AlignmentFlag.AlignLeft)
        grid.setColumnStretch(1, 1)
        self.inst_card.layout().addLayout(grid)
        lay.addWidget(self.inst_card)

        # Online installieren
        self.web_card = Card("cur.online", self)
        self.rows = {}
        for e in online.CURSORS:
            row = QtWidgets.QFrame()
            row.setObjectName("BindRow")
            rl = QtWidgets.QHBoxLayout(row)
            rl.setContentsMargins(14, 8, 10, 8)
            rl.setSpacing(10)
            name = QtWidgets.QLabel(e[1])
            name.setStyleSheet("font-weight:600; background:transparent;")
            src = QtWidgets.QLabel("github.com/" + e[2].split("github.com/")[1].split("/releases")[0])
            src.setObjectName("RowLabel")
            chip = QtWidgets.QLabel()
            btn = _btn(True)
            btn.setMinimumWidth(120)
            btn.clicked.connect(lambda _=False, x=e: self._install(x))
            rl.addWidget(name)
            rl.addSpacing(6)
            rl.addWidget(src, 1)
            rl.addWidget(chip)
            rl.addWidget(btn)
            self.web_card.layout().addWidget(row)
            self.rows[e[0]] = (row, chip, btn, e)
        self.no_hit = QtWidgets.QLabel()
        self.no_hit.setObjectName("RowLabel")
        self.web_card.layout().addWidget(self.no_hit)
        lay.addWidget(self.web_card)
        lay.addStretch()

    def refresh(self):
        self.load()

    def load(self):
        hs = self.win.hypr_page.state
        self.list.blockSignals(True)
        self.list.clear()
        items = paper.cursor_themes()
        sel = None
        for name, kind in items:
            it = QtWidgets.QListWidgetItem(f"{name}    ·  {t('cur.' + kind)}")
            it.setData(Qt.ItemDataRole.UserRole, name)
            self.list.addItem(it)
            if name == hs["cursor_theme"]:
                sel = it
        if not items:
            it = QtWidgets.QListWidgetItem(t("cur.none"))
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(it)
        if sel:
            self.list.setCurrentItem(sel)
        self.list.blockSignals(False)
        self.size.setValue(max(8, min(32, hs["cursor_size"] // 2)))
        self.size_val.setText(f"{self.size.value() * 2} px")
        self._rows()
        self._filter()

    def _rows(self):
        busy = self.job is not None
        for row, chip, btn, e in self.rows.values():
            inst = online.installed_cursor(e)
            set_chip(chip, True, t("cur.installed"))
            chip.setVisible(inst)
            btn.setVisible(not inst)
            btn.setText(t("cur.install"))
            btn.setEnabled(not busy)

    def _filter(self, *_):
        q = self.search.text().strip().lower()
        for i in range(self.list.count()):
            it = self.list.item(i)
            name = (it.data(Qt.ItemDataRole.UserRole) or "").lower()
            it.setHidden(bool(q) and bool(name) and q not in name)
        hits = 0
        for row, _, _, e in self.rows.values():
            ok = not q or q in e[1].lower() or any(q in n.lower() for n in e[3])
            row.setVisible(ok)
            hits += ok
        self.no_hit.setText(t("cur.nomatch"))
        self.no_hit.setVisible(hits == 0)

    def _install(self, e):
        if self.job:
            return
        self.win.log("")
        self.win.set_status(t("dl.loading", name=e[1]))
        self.job = Job(lambda log: online.install_cursor(e, log), self)
        self._rows()
        self.job.line.connect(self.win.log)
        self.job.result.connect(lambda r, x=e: self._installed(x, r))
        self.job.start()

    def _installed(self, e, r):
        self.job = None
        if isinstance(r, Exception):
            self.win.log(f"Fehler: {r}")
            self.win.set_status(t("dl.fail", err=r))
            self._rows()
            return
        self.load()
        for i in range(self.list.count()):  # neues Thema gleich auswählen
            if self.list.item(i).data(Qt.ItemDataRole.UserRole) == (r[0] if r else e[3][0]):
                self.list.setCurrentRow(i)
        self.win.set_status(t("cur.got", name=e[1]))

    def _picked(self, cur, _prev):
        if cur and cur.data(Qt.ItemDataRole.UserRole):
            self.win.set_status(t("cur.picked", name=cur.data(Qt.ItemDataRole.UserRole)))

    def apply(self):
        it = self.list.currentItem()
        theme = it.data(Qt.ItemDataRole.UserRole) if it else ""
        size = self.size.value() * 2
        hp = self.win.hypr_page
        hp.state["cursor_theme"] = theme or hp.state["cursor_theme"]
        hp.state["cursor_size"] = size
        self.win.cfg["cursor_gtk"] = self.gtk.isChecked()
        hp.refresh_controls()
        hp.changed()
        hp.apply()
        paper.set_cursor_live(hp.state["cursor_theme"], size, self.gtk.isChecked(), self.win.log)
        self.win.set_status(t("cur.done", name=hp.state["cursor_theme"] or "–", size=size))

    def retranslate(self):
        self.inst_card.retranslate()
        self.web_card.retranslate()
        self.search.setPlaceholderText(t("cur.search"))
        self.btn_refresh.setText(t("bak.refresh"))
        self.btn_open.setText(t("cur.open"))
        self.l_size.setText(t("cursor_size"))
        self.l_gtk.setText(t("cur.gtk"))
        self.btn_apply.setText(t("apply"))
        self.load()

    def apply_theme(self, accent):
        self.gtk.accent = accent
        self.gtk.update()
