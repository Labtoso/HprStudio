"""Sonstiges › Hintergrundbild (Hyprpaper) und › Mauszeiger (Hyprcursor/XCursor)."""

import os
from pathlib import Path

from . import model, paper
from .i18n import t
from .qt import QtCore, QtGui, QtWidgets, Qt
from .widgets import Card, Segmented, Switch
from .workspaces import monitors


def _thumb(path: str, w: int, h: int) -> QtGui.QPixmap:
    pm = QtGui.QPixmap(w, h)
    pm.fill(Qt.GlobalColor.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
    clip = QtGui.QPainterPath()
    clip.addRoundedRect(QtCore.QRectF(0, 0, w, h), 12, 12)
    p.setClipPath(clip)
    full = os.path.expanduser(path) if path else ""
    img = QtGui.QPixmap()
    if full and Path(full).is_dir():  # Ordner: erstes Bild zeigen
        for f in sorted(Path(full).iterdir()):
            if f.suffix.lower() in paper.IMAGE_EXT and img.load(str(f)):
                break
    elif full:
        img.load(full)
    if img.isNull():
        p.fillRect(QtCore.QRectF(0, 0, w, h), QtGui.QColor("#1b2430"))
        p.setPen(QtGui.QColor("#8a98ab"))
        p.drawText(QtCore.QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, t("paper.none"))
    else:
        scale = max(w / img.width(), h / img.height())
        sw, sh = w / scale, h / scale
        p.drawPixmap(QtCore.QRectF(0, 0, w, h), img, QtCore.QRectF((img.width() - sw) / 2, (img.height() - sh) / 2, sw, sh))
    p.end()
    return pm


def _pick(parent, folder: bool, start: str) -> str:
    start = os.path.expanduser(start) if start else str(Path.home())
    if folder:
        return QtWidgets.QFileDialog.getExistingDirectory(parent, t("paper.folder"), start)
    path, _ = QtWidgets.QFileDialog.getOpenFileName(parent, t("paper.image"), start,
                                                    "Bilder (*.png *.jpg *.jpeg *.webp *.jxl *.bmp)")
    return path


def _short(path: str) -> str:
    home = str(Path.home())
    return "~" + path[len(home):] if path.startswith(home) else path


class PaperEditor(QtWidgets.QWidget):
    KIND = "paper"

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.state = paper.paper_state(win.cfg.get("paper"))
        self.cards, self.switches, self.segs = [], [], []
        sa_lay = QtWidgets.QVBoxLayout(self)
        sa_lay.setContentsMargins(0, 0, 0, 0)
        sa = QtWidgets.QScrollArea()
        sa.setWidgetResizable(True)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QtWidgets.QWidget()
        inner.setObjectName("ScrollInner")
        lay = QtWidgets.QVBoxLayout(inner)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(12)
        sa.setWidget(inner)
        sa_lay.addWidget(sa)

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
        self.btn_img = QtWidgets.QPushButton()
        self.btn_dir = QtWidgets.QPushButton()
        for b in (self.btn_img, self.btn_dir):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            col.addWidget(b, 0, Qt.AlignmentFlag.AlignLeft)
        self.btn_img.clicked.connect(lambda: self._choose("", False))
        self.btn_dir.clicked.connect(lambda: self._choose("", True))
        col.addStretch()
        row.addLayout(col, 1)
        c.layout().addLayout(row)
        c.choice("fit", paper.FITS, "fit.", label_key="paper.fit")
        lay.addWidget(c)

        # Pro Monitor
        self.mon_card = Card("paper.per_monitor", self)
        self.cards.append(self.mon_card)
        self.mon_lay = QtWidgets.QVBoxLayout()
        self.mon_lay.setSpacing(6)
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
        self.l_auto = c._add("paper.autostart", self.auto, None, "tip.paper.autostart", None, label_key="paper.autostart")
        self.switches.append(self.auto)
        lay.addWidget(c)

        acts = QtWidgets.QHBoxLayout()
        acts.addStretch()
        self.btn_undo = QtWidgets.QPushButton()
        self.btn_apply = QtWidgets.QPushButton()
        self.btn_apply.setObjectName("Primary")
        for b in (self.btn_undo, self.btn_apply):
            b.setFixedSize(170, 40)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            acts.addWidget(b)
        self.btn_apply.clicked.connect(self.apply)
        self.btn_undo.clicked.connect(self.undo)
        lay.addLayout(acts)
        lay.addStretch()
        self.refresh_controls()

    # ----- Zustand -----
    def set(self, key, value):
        self.state[key] = value
        self.changed()

    def changed(self):
        self.win.cfg["paper"] = self.state
        self.win.save_later()
        self.thumb.setPixmap(_thumb(self.state["path"], 320, 180))
        self.path_lbl.setText(_short(self.state["path"]) or t("paper.none"))

    def refresh_controls(self):
        for c in self.cards:
            c.refresh(self.state)
        self.auto.set_now("hyprpaper" in self.win.hypr_page.state["autostart"])
        self._monitors()
        self.changed()

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
            th.setPixmap(_thumb(m["path"] if m else self.state["path"], 96, 54))
            name = QtWidgets.QLabel(mon)
            name.setObjectName("Mono")
            name.setFixedWidth(110)
            path = QtWidgets.QLabel(_short(m["path"]) if m else t("paper.same"))
            path.setObjectName("RowLabel" if not m else "")
            rl.addWidget(th)
            rl.addWidget(name)
            rl.addWidget(path, 1)
            for txt, fn in ((t("paper.image_btn"), lambda _=False, x=mon: self._choose(x, False)),
                            (t("paper.folder_btn"), lambda _=False, x=mon: self._choose(x, True))):
                b = QtWidgets.QPushButton(txt)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.clicked.connect(fn)
                rl.addWidget(b)
            if m:
                b = QtWidgets.QPushButton(t("paper.reset"))
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.clicked.connect(lambda _=False, x=mon: self._clear(x))
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
        for s in self.segs:
            s.retranslate()
        self.btn_img.setText(t("paper.image"))
        self.btn_dir.setText(t("paper.folder"))
        self.btn_undo.setText(t("undo"))
        self.btn_apply.setText(t("apply"))
        self._monitors()
        self.changed()

    def apply_theme(self, accent):
        for sw in self.switches:
            sw.accent = accent
            sw.update()


class CursorEditor(QtWidgets.QWidget):
    """Mauszeiger: Thema aus den installierten wählen, Größe, auch für GTK-Apps. Schreibt über Hyprland (hl.env)."""

    def __init__(self, win):
        super().__init__()
        self.win = win
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        card = QtWidgets.QFrame()
        card.setObjectName("Card")
        cl = QtWidgets.QVBoxLayout(card)
        cl.setContentsMargins(18, 14, 18, 16)
        cl.setSpacing(10)
        top = QtWidgets.QHBoxLayout()
        self.title = QtWidgets.QLabel()
        self.title.setObjectName("CardTitle")
        self.btn_refresh = QtWidgets.QPushButton()
        self.btn_open = QtWidgets.QPushButton()
        for b in (self.btn_refresh, self.btn_open):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.load)
        self.btn_open.clicked.connect(self._open)
        top.addWidget(self.title)
        top.addStretch()
        top.addWidget(self.btn_refresh)
        top.addWidget(self.btn_open)
        cl.addLayout(top)
        self.list = QtWidgets.QListWidget()
        self.list.setObjectName("ModList")
        self.list.setMinimumHeight(260)
        self.list.currentItemChanged.connect(self._picked)
        cl.addWidget(self.list)
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(14)
        self.l_size = QtWidgets.QLabel()
        self.l_size.setObjectName("RowLabel")
        self.size = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.size.setRange(8, 32)  # ×2 → 16 … 64
        self.size_val = QtWidgets.QLabel()
        self.size_val.setObjectName("Value")
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
        cl.addLayout(grid)
        lay.addWidget(card)
        acts = QtWidgets.QHBoxLayout()
        acts.addStretch()
        self.btn_apply = QtWidgets.QPushButton()
        self.btn_apply.setObjectName("Primary")
        self.btn_apply.setFixedSize(170, 40)
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.clicked.connect(self.apply)
        acts.addWidget(self.btn_apply)
        lay.addLayout(acts)
        lay.addStretch()

    def load(self):
        hs = self.win.hypr_page.state
        self.list.blockSignals(True)
        self.list.clear()
        items = paper.cursor_themes()
        if model.DRY and not items:
            items = [("Bibata-Modern-Classic", "hyprcursor"), ("Adwaita", "xcursor"), ("breeze_cursors", "xcursor")]
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

    def _picked(self, cur, _prev):
        if cur and cur.data(Qt.ItemDataRole.UserRole):
            self.win.set_status(t("cur.picked", name=cur.data(Qt.ItemDataRole.UserRole)))

    def _open(self):
        d = Path.home() / ".local/share/icons"
        d.mkdir(parents=True, exist_ok=True)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(d)))

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
        self.title.setText(t("cur.title"))
        self.btn_refresh.setText(t("bak.refresh"))
        self.btn_open.setText(t("cur.open"))
        self.l_size.setText(t("cursor_size"))
        self.l_gtk.setText(t("cur.gtk"))
        self.btn_apply.setText(t("apply"))
        self.load()

    def apply_theme(self, accent):
        self.gtk.accent = accent
        self.gtk.update()
