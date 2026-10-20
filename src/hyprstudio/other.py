"""Tab „Sonstiges“: Config-Fehler reparieren, Werkzeuge, Sicherungen wiederherstellen."""

import time
from pathlib import Path

import shutil

from . import appearance, dialogs, fixer, model, packages, theme
from .i18n import t
from .qt import QtCore, QtGui, QtWidgets, Qt
from .gate import Gate
from .kitty_page import KittyEditor
from .paper_page import CursorEditor, PaperEditor
from .widgets import Card, Segmented, Switch, set_chip


def _clear(lay: QtWidgets.QLayout):
    while lay.count():
        it = lay.takeAt(0)
        w = it.widget()
        if w:
            w.hide()
            w.setParent(None)
            w.deleteLater()


class ErrorRow(QtWidgets.QFrame):
    def __init__(self, e: dict, page, parent=None):
        super().__init__(parent)
        self.setObjectName("BindRow")
        self.e = e
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 10, 10)
        lay.setSpacing(12)
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(4)
        where = QtWidgets.QLabel(f"{Path(e['file']).name}:{e['line']}" if e["file"] else t("fix.nofile"))
        where.setObjectName("Mono")
        where.setToolTip(e["file"])
        msg = QtWidgets.QLabel(e["msg"])
        msg.setWordWrap(True)
        col.addWidget(where)
        col.addWidget(msg)
        src = fixer.line_text(e) if e["file"] else ""
        if src:
            code = QtWidgets.QLabel(src)
            code.setObjectName("Code")
            code.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            col.addWidget(code)
        lay.addLayout(col, 1)
        p = fixer.plan(e)
        self.btn = QtWidgets.QPushButton(t("fix.one"))
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.setEnabled(p["kind"] != "none")
        tip = {"skip": t("fix.tip.skip", opt=p.get("option", "")), "state": t("fix.tip.state"),
               "bind": t("fix.tip.bind"), "comment": t("fix.tip.comment"), "none": t("fix.tip.none")}[p["kind"]]
        self.btn.setToolTip(tip)
        self.btn.clicked.connect(lambda: page.fix([self.e]))
        lay.addWidget(self.btn, 0, Qt.AlignmentFlag.AlignTop)


class OtherPage(QtWidgets.QWidget):
    SECTIONS = ("fix", "install", "kitty", "look", "scroll", "tools", "backups")

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.errors = []
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
        lay.addWidget(side)

        right = QtWidgets.QVBoxLayout()
        right.setSpacing(14)
        head = QtWidgets.QHBoxLayout()
        self.title = QtWidgets.QLabel()
        self.title.setObjectName("PageTitle")
        self.title.setMinimumHeight(40)
        self.chip = QtWidgets.QLabel()
        head.addWidget(self.title)
        head.addSpacing(10)
        head.addWidget(self.chip)
        head.addStretch()
        right.addLayout(head)
        self.stack = QtWidgets.QStackedWidget()
        right.addWidget(self.stack, 1)
        lay.addLayout(right, 1)

        # --- Reparatur ---
        self.p_fix, fl = self._page()
        top = QtWidgets.QHBoxLayout()
        self.btn_scan = QtWidgets.QPushButton()
        self.btn_scan.setObjectName("Primary")
        self.btn_all = QtWidgets.QPushButton()
        self.btn_reload = QtWidgets.QPushButton()
        for b in (self.btn_scan, self.btn_all, self.btn_reload):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            top.addWidget(b)
        top.addStretch()
        fl.addLayout(top)
        self.err_lay = QtWidgets.QVBoxLayout()
        self.err_lay.setSpacing(8)
        fl.addLayout(self.err_lay)
        fl.addStretch()
        self.btn_scan.clicked.connect(self.scan)
        self.btn_all.clicked.connect(lambda: self.fix(list(self.errors)))
        self.btn_reload.clicked.connect(self.reload)

        # --- Werkzeuge ---
        self.p_tools, tl = self._page()
        self.tool_btns = {}
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(10)
        tools = (("reload", self.reload), ("waybar", lambda: (model.restart_waybar(self.win.log),
                                                               self.win.set_status(t("done")))),
                 ("open_hypr", lambda: self.open_dir("hypr")), ("open_waybar", lambda: self.open_dir("waybar")),
                 ("open_launcher", lambda: self.open_dir(self.win.launcher_page.state["app"])),
                 ("open_kitty", lambda: self.open_dir("kitty")),
                 ("open_backups", lambda: self.show_section("backups")))
        for i, (k, fn) in enumerate(tools):
            b = QtWidgets.QPushButton()
            b.setMinimumHeight(44)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(fn)
            grid.addWidget(b, i // 2, i % 2)
            self.tool_btns[k] = b
        tl.addLayout(grid)
        tl.addStretch()

        # --- Sicherungen ---
        self.p_bak, bl = self._page()
        btop = QtWidgets.QHBoxLayout()
        self.btn_bak_refresh = QtWidgets.QPushButton()
        self.btn_bak_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_bak_refresh.clicked.connect(self.load_backups)
        btop.addWidget(self.btn_bak_refresh)
        btop.addStretch()
        bl.addLayout(btop)
        self.bak_lay = QtWidgets.QVBoxLayout()
        self.bak_lay.setSpacing(6)
        bl.addLayout(self.bak_lay)
        bl.addStretch()

        # --- Installieren ---
        self.p_inst, il = self._page()
        itop = QtWidgets.QHBoxLayout()
        self.btn_inst = QtWidgets.QPushButton()
        self.btn_inst.setObjectName("Primary")
        self.btn_inst.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_inst.clicked.connect(self.install_selected)
        self.pm_label = QtWidgets.QLabel()
        self.pm_label.setObjectName("RowLabel")
        self.btn_rm = QtWidgets.QPushButton()
        self.btn_rm.setObjectName("DangerFill")
        self.btn_rm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rm.clicked.connect(self.remove_selected)
        itop.addWidget(self.btn_inst)
        itop.addWidget(self.btn_rm)
        itop.addSpacing(10)
        itop.addWidget(self.pm_label)
        itop.addStretch()
        il.addLayout(itop)
        self.pkg_rows, self.pkg_acts = {}, {}
        for g in packages.GROUPS:
            head = QtWidgets.QLabel()
            head.setObjectName("CardTitle")
            head.setProperty("tkey", "pkgg." + g)
            il.addWidget(head)
            self.pkg_rows["_" + g] = head
            for key, (grp, _, _) in packages.PACKAGES.items():
                if grp != g:
                    continue
                row = QtWidgets.QFrame()
                row.setObjectName("BindRow")
                rl = QtWidgets.QHBoxLayout(row)
                rl.setContentsMargins(14, 8, 12, 8)
                cb = QtWidgets.QCheckBox()
                cb.setCursor(Qt.CursorShape.PointingHandCursor)
                cb.toggled.connect(self._inst_count)
                desc = QtWidgets.QLabel()
                desc.setObjectName("RowLabel")
                chip = QtWidgets.QLabel()
                act = QtWidgets.QPushButton()
                act.setCursor(Qt.CursorShape.PointingHandCursor)
                act.setMinimumWidth(120)
                act.clicked.connect(lambda _=False, k=key: self._row_action(k))
                rl.addWidget(cb)
                rl.addWidget(desc, 1)
                rl.addWidget(chip)
                rl.addWidget(act)
                il.addWidget(row)
                self.pkg_rows[key] = (cb, desc, chip)
                self.pkg_acts[key] = act
        il.addStretch()
        self.proc = None

        # --- Hell/Dunkel für alle Programme ---
        self.p_look, ll = self._page()
        self.look_card = Card("look.title", self)
        self.look_seg = Segmented(appearance.MODES, prefix="look.")
        self.look_seg.changed.connect(self.set_look)
        self.look_card.layout().addWidget(self.look_seg, 0, Qt.AlignmentFlag.AlignLeft)
        self.look_state = QtWidgets.QLabel()
        self.look_state.setObjectName("RowLabel")
        self.look_card.layout().addWidget(self.look_state)
        ll.addWidget(self.look_card)
        ll.addStretch()

        # --- Scrollrichtung (schreibt über Hyprland und wendet sofort an) ---
        self.p_scroll, scl = self._page()
        self.scroll_card = Card("scroll.title", self)
        self.scroll_sw = {}
        for key in ("mouse_natural", "natural_scroll"):
            sw = Switch()
            sw.toggled.connect(lambda on, k=key: self.set_scroll(k, on))
            self.scroll_card._add("scroll." + key, sw, None, "tip.scroll", None, label_key="scroll." + key)
            self.scroll_sw[key] = sw
        # Mausbeschleunigung: aus = accel_profile flat, an = Standard (adaptiv)
        self.accel_sw = Switch()
        self.accel_sw.toggled.connect(self.set_accel)
        self.scroll_card._add("scroll.accel", self.accel_sw, None, "tip.accel", None, label_key="scroll.accel")
        # Regler schreiben in den Hyprland-Zustand (Card ruft self.state / self.set)
        self._apply_later = QtCore.QTimer(self)
        self._apply_later.setSingleShot(True)
        self._apply_later.setInterval(600)
        self._apply_later.timeout.connect(self._apply_hypr)
        self.switches = []
        self.scroll_card.slider("sensitivity", -1.0, 1.0, 0.05, "{:+.2f}", tip="tip.sens", label_key="scroll.sens")
        self.scroll_card.slider("scroll_factor", 0.1, 3.0, 0.1, "{:.1f}×", tip="tip.scroll_factor",
                                label_key="scroll.speed")
        scl.addWidget(self.scroll_card)
        scl.addStretch()

        # Kitty hier; Hintergrundbild und Mauszeiger hängt das Hauptfenster in den Hyprland-Tab
        self.kitty = KittyEditor(win)
        self.paper = PaperEditor(win)
        self.cursor = CursorEditor(win)
        self.gates = {"kitty": Gate(self.kitty, "kitty", win), "wallpaper": Gate(self.paper, "hyprpaper", win),
                      "cursor": Gate(self.cursor, "hyprcursor", win)}
        self.stack.addWidget(self.gates["kitty"])
        self.pages = {"fix": self.p_fix, "install": self.p_inst, "kitty": self.gates["kitty"], "look": self.p_look, "scroll": self.p_scroll,
                      "tools": self.p_tools, "backups": self.p_bak}
        self.show_section(win.cfg.get("other_section", "fix"))

    def _page(self):
        sa = QtWidgets.QScrollArea()
        sa.setWidgetResizable(True)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QtWidgets.QWidget()
        inner.setObjectName("ScrollInner")
        il = QtWidgets.QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 6, 0)
        il.setSpacing(12)
        sa.setWidget(inner)
        self.stack.addWidget(sa)
        return sa, il

    def show_section(self, key):
        if key not in self.SECTIONS:
            key = "fix"
        self.nav[key].setChecked(True)
        self.stack.setCurrentWidget(self.pages[key])
        self.win.cfg["other_section"] = key
        self.win.save_later()
        self.title.setText(t("sec." + key))
        self.chip.setVisible(key == "fix")
        if key in self.gates:
            self.gates[key].refresh()
        if key == "look":
            self.refresh_look()
        if key == "scroll":
            self.refresh_scroll()
        if key == "backups":
            self.load_backups()
        elif key == "install":
            self.refresh_packages()
        elif key == "fix" and hasattr(self, "chip") and self.isVisible():
            self.scan(quiet=True)

    # ----- Hell/Dunkel -----
    def refresh_look(self):
        mode = self.win.cfg.get("appearance", appearance.DEFAULT)
        self.look_card.retranslate()
        self.look_seg.retranslate()
        self.look_seg.select(mode)
        self.look_state.setText(t("look.active", name=t("look." + mode)))

    def set_look(self, mode: str):
        self.win.log("")
        appearance.apply(mode, model.config_home(), self.win.log)
        self.win.cfg["appearance"] = mode
        self.win.save_later()
        self.refresh_look()
        self.win.set_status(t("look.active", name=t("look." + mode)))

    # ----- Scrollrichtung -----
    @property
    def state(self) -> dict:
        return self.win.hypr_page.state

    def set(self, key, value):
        """Regler unter Maus & Touchpad: Wert merken, kurz nach dem Loslassen anwenden."""
        hp = self.win.hypr_page
        if hp.state.get(key) == value:
            return
        hp.state[key] = value
        hp.refresh_controls()
        hp.changed()
        self._apply_later.start()

    def _apply_hypr(self):
        self.win.log("")
        self.win.hypr_page.apply()

    def refresh_scroll(self):
        self.scroll_card.retranslate()
        self.scroll_card.refresh(self.win.hypr_page.state)
        hs = self.win.hypr_page.state
        for k, sw in self.scroll_sw.items():
            sw.set_now(bool(hs[k]))
            sw.accent = self.win.accent()
        self.accel_sw.set_now(hs["accel"] != "flat")
        self.accel_sw.accent = self.win.accent()

    def set_accel(self, on: bool):
        hp = self.win.hypr_page
        want = "default" if on else "flat"
        if hp.state["accel"] == want or (on and hp.state["accel"] != "flat"):
            return
        hp.state["accel"] = want
        hp.refresh_controls()
        hp.changed()
        self.win.log("")
        hp.apply()

    def set_scroll(self, key: str, on: bool):
        hp = self.win.hypr_page
        if hp.state[key] == on:
            return
        hp.state[key] = on
        hp.refresh_controls()
        hp.changed()
        self.win.log("")
        hp.apply()

    # ----- Reparatur -----
    def hdir(self) -> Path:
        return model.config_home() / "hypr"

    def scan(self, quiet: bool = False) -> int:
        self.errors = fixer.parse(fixer.read_errors(self.hdir(), self.win.log))
        _clear(self.err_lay)
        for e in self.errors:
            self.err_lay.addWidget(ErrorRow(e, self))
        n = len(self.errors)
        set_chip(self.chip, not n, t("fix.none") if not n else t("fix.count", n=n))
        self.btn_all.setEnabled(n > 0)
        if not quiet:
            self.win.set_status(t("fix.none") if not n else t("fix.count", n=n))
        return n

    def fix(self, errors: list):
        if not errors:
            return
        self.win.log("")
        hp = self.win.hypr_page
        own, fixed = False, []
        for e in errors:
            kind = fixer.plan(e)["kind"]
            if fixer.apply_fix(e, hp.state, self.win.log):
                fixed.append(e)
                own = own or kind in ("skip", "state", "bind")
        if own:  # eigene Datei neu schreiben (lädt Hyprland auch neu)
            hp.refresh_controls()
            hp.changed()
            hp.apply()
        else:
            model.run(["hyprctl", "reload"], self.win.log)
        if model.DRY:  # Testmodus: behobene Meldungen aus der Testdatei nehmen
            f = self.hdir().parent / fixer.TESTFILE
            if f.is_file():
                gone = {e["raw"] for e in fixed}
                f.write_text("\n".join(x for x in f.read_text(encoding="utf-8").splitlines() if x not in gone) + "\n",
                             encoding="utf-8")
        # Hyprland braucht einen Moment für das Neuladen
        QtCore.QTimer.singleShot(700, lambda: (self.scan(quiet=True),
                                               self.win.set_status(t("fix.done", n=len(fixed), left=len(self.errors)))))

    def reload(self):
        self.win.log("")
        model.run(["hyprctl", "reload"], self.win.log)
        QtCore.QTimer.singleShot(700, self.scan)

    # ----- Installieren -----
    def refresh_packages(self):
        pm = packages.manager()
        self.pm_label.setText(t("pkg.pm", pm=pm) if pm else t("pkg.nopm"))
        for key in packages.PACKAGES:
            cb, desc, chip = self.pkg_rows[key]
            inst = packages.installed(key)
            avail = packages.available(key, pm)
            cb.setText(t("pkg." + key))
            desc.setText(t("pkgd." + key) + "  ·  " + " ".join(packages.PACKAGES[key][2].get(pm or "pacman", [])))
            cb.setEnabled(avail and self.proc is None)
            if not avail:
                cb.setChecked(False)
            act = self.pkg_acts[key]
            act.setText(t("pkg.remove_one") if inst else t("pkg.install_one"))
            act.setObjectName("DangerFill" if inst else "Primary")
            act.style().unpolish(act)
            act.style().polish(act)
            act.setEnabled(avail and self.proc is None)
            set_chip(chip, inst, t("pkg.installed") if inst else t("pkg.missing") if avail else t("pkg.unavailable"))
        self._inst_count()

    def _inst_count(self, *_):
        sel = self._selected()
        n = len([k for k in sel if not packages.installed(k)])
        r = len([k for k in sel if packages.installed(k)])
        self.btn_inst.setText(t("pkg.install", n=n) if n else t("pkg.install0"))
        self.btn_inst.setEnabled(n > 0 and self.proc is None)
        self.btn_rm.setText(t("pkg.remove", n=r) if r else t("pkg.remove0"))
        self.btn_rm.setEnabled(r > 0 and self.proc is None)

    def _selected(self) -> list:
        return [k for k in packages.PACKAGES if self.pkg_rows[k][0].isChecked()]

    def install_selected(self):
        self.install_keys([k for k in self._selected() if not packages.installed(k)])

    def remove_selected(self):
        self.remove_keys([k for k in self._selected() if packages.installed(k)])

    def _row_action(self, key: str):
        if packages.installed(key):
            self.remove_keys([key])
        else:
            self.install_keys([key])

    def remove_keys(self, keys: list):
        pm = packages.manager()
        if not keys or not pm:
            return
        names = ", ".join(t("pkg." + k) for k in keys)
        pkgs = " ".join(packages.pkg_names(keys, pm))
        if not dialogs.confirm(self, t("pkg.remove_title"), t("pkg.remove_q", names=names, pkgs=pkgs),
                               t("pkg.remove_one"), danger=True):
            return
        self.install_keys(keys, remove=True)

    def install_keys(self, keys: list, remove: bool = False):
        pm = packages.manager()
        cmd = (packages.remove_command(keys, pm) if remove else packages.command(keys, pm)) if pm else []
        if not cmd:
            return
        self.win.log("")
        for k in keys:
            self.pkg_rows[k][0].setChecked(False)
        if model.DRY:
            self.win.log("$ pkexec " + " ".join(cmd) + "  (Testmodus)")
            if remove:
                packages.DRY_REMOVED.update(keys)
                packages.DRY_INSTALLED.difference_update(keys)
            else:
                packages.DRY_INSTALLED.update(keys)
                packages.DRY_REMOVED.difference_update(keys)
            self.refresh_packages()
            self.win.set_status(t("pkg.done"))
            self.win.refresh_gates()
            if not self.win.logview.isVisible():
                self.win.btn_log.setChecked(True)
            return
        if not shutil.which("pkexec") or not packages.polkit_agent():
            # ohne Polkit-Agent scheitert pkexec lautlos → sichtbares Terminal mit sudo-Passwortabfrage
            self.win.log(t("pkg.noagent"))
            self._terminal(cmd)
            self._watch(keys, remove)
            return
        self._pkg_out = []
        self.proc = QtCore.QProcess(self)
        self.proc.setWorkingDirectory("/tmp")  # nie aus einem Cloud-Ordner als root starten
        self.proc.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._pkg_read)
        self.proc.finished.connect(lambda code, _s=None, k=keys, r=remove: self._installed(code, cmd, k, r))
        self.win.log("$ pkexec " + " ".join(cmd))
        self.win.set_status(t("pkg.busy"))
        self.win.bar_busy(True)
        self.proc.start("pkexec", cmd)
        self.refresh_packages()

    def _pkg_read(self):
        for x in bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace").splitlines():
            if x.strip():
                self._pkg_out.append(x)
                self.win.log(x)

    def _installed(self, code: int, cmd: list, keys: list = (), remove: bool = False):
        self.proc.deleteLater()
        self.proc = None
        self.win.bar_busy(False)
        if code in (126, 127):  # abgebrochen oder kein Polkit-Agent → im Terminal mit sudo
            self.win.log(t("pkg.fallback"))
            self._terminal(cmd)
            self._watch(list(keys), remove)
        elif code == 0:
            self.win.set_status(t("pkg.done"))
        else:
            why = packages.fail_reason("\n".join(getattr(self, "_pkg_out", [])))
            self.win.set_status(t("pkg.failed") + (" – " + t(why) if why else ""))
            if not self.win.logview.isVisible():
                self.win.btn_log.setChecked(True)
        self.refresh_packages()
        self.win.refresh_gates()

    def _watch(self, keys: list, remove: bool):
        """Nach Installation im Terminal: alle 2 s nachsehen, bis das Programm da (bzw. weg) ist – max. 10 min."""
        if not keys:
            return
        self._watch_left = 300
        if not hasattr(self, "_watch_timer"):
            self._watch_timer = QtCore.QTimer(self)
            self._watch_timer.setInterval(2000)
            self._watch_timer.timeout.connect(self._watch_tick)
        self._watch_keys, self._watch_remove = list(keys), remove
        self._watch_timer.start()

    def _watch_tick(self):
        self._watch_left -= 1
        done = all(packages.installed(k) != self._watch_remove for k in self._watch_keys)
        if done or self._watch_left <= 0:
            self._watch_timer.stop()
            if done:
                self.win.set_status(t("pkg.done"))
            self.refresh_packages()
            self.win.refresh_gates()

    def _terminal(self, cmd: list):
        line = "cd /tmp && sudo " + " ".join(cmd) + "; echo; read -r -p 'Enter = schließen' _"
        for term, args in (("kitty", ["sh", "-c", line]), ("foot", ["sh", "-c", line]),
                           ("alacritty", ["-e", "sh", "-c", line]), ("wezterm", ["start", "--", "sh", "-c", line]),
                           ("konsole", ["-e", "sh", "-c", line]), ("gnome-terminal", ["--", "sh", "-c", line]),
                           ("xterm", ["-e", "sh", "-c", line])):
            if shutil.which(term):
                QtCore.QProcess.startDetached(term, args, "/tmp")
                self.win.set_status(t("pkg.terminal", term=term))
                return
        self.win.set_status(t("pkg.noterm"))

    # ----- Werkzeuge -----
    def open_dir(self, name: str):
        d = model.config_home() / name
        d.mkdir(parents=True, exist_ok=True)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(d)))

    # ----- Sicherungen -----
    def load_backups(self):
        _clear(self.bak_lay)
        items = fixer.backups(model.config_home())
        if not items:
            lb = QtWidgets.QLabel(t("bak.none"))
            lb.setObjectName("RowLabel")
            self.bak_lay.addWidget(lb)
        for bak, orig in items[:80]:
            row = QtWidgets.QFrame()
            row.setObjectName("BindRow")
            rl = QtWidgets.QHBoxLayout(row)
            rl.setContentsMargins(14, 8, 10, 8)
            name = QtWidgets.QLabel(f"{bak.parent.name}/{bak.name}")
            name.setObjectName("Mono")
            when = QtWidgets.QLabel(time.strftime("%d.%m.%Y %H:%M", time.localtime(bak.stat().st_mtime)))
            when.setObjectName("RowLabel")
            btn = QtWidgets.QPushButton(t("bak.restore"))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(t("bak.tip", target=orig.name))
            btn.clicked.connect(lambda _=False, b=bak, o=orig: self.restore(b, o))
            rl.addWidget(name, 1)
            rl.addWidget(when)
            rl.addSpacing(10)
            rl.addWidget(btn)
            self.bak_lay.addWidget(row)

    def restore(self, bak: Path, orig: Path):
        if not dialogs.confirm(self, t("bak.restore"), t("bak.confirm", src=bak.name, target=orig.name),
                               t("bak.restore")):
            return
        self.win.log("")
        fixer.restore(bak, orig, self.win.log)
        if orig.parent.name == "hypr":
            model.run(["hyprctl", "reload"], self.win.log)
        elif orig.parent.name == "waybar":
            model.restart_waybar(self.win.log)
        self.win.set_status(t("bak.done", target=orig.name))
        self.load_backups()

    def apply_theme(self, accent):
        self.kitty.apply_theme(accent)
        self.paper.apply_theme(accent)
        self.cursor.apply_theme(accent)

    def retranslate(self):
        for k, b in self.nav.items():
            b.setText(t("sec." + k).replace("&", "&&"))
        self.title.setText(t("sec." + self.win.cfg.get("other_section", "fix")))
        self.btn_scan.setText(t("fix.scan"))
        self.btn_all.setText(t("fix.all"))
        self.btn_reload.setText(t("fix.reload"))
        for k, b in self.tool_btns.items():
            b.setText(t("tool." + k))
        self.btn_bak_refresh.setText(t("bak.refresh"))
        self.kitty.retranslate()
        self.paper.retranslate()
        self.cursor.retranslate()
        for g in self.gates.values():
            g.refresh()
        for g in packages.GROUPS:
            self.pkg_rows["_" + g].setText(t("pkgg." + g))
        self.refresh_packages()
        if self.chip.text():
            self.scan(quiet=True)
