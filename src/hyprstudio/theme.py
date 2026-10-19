"""Dunkles Design (Design-Vorlage Nr. 1) mit 3 Akzentfarben, kein Light-Theme."""

THEMES = {
    "blue": "#3d8bfd",
    "teal": "#22b8cf",
    "violet": "#8b7cf6",
}

BG = "#0e131a"
SURFACE = "#151c26"
SURFACE2 = "#1b2430"
BORDER = "#253142"
TEXT = "#e6edf5"
MUTED = "#8a98ab"
DANGER = "#e5534b"
OK = "#3fb950"


def qss(accent: str) -> str:
    return f"""
    QWidget {{ color: {TEXT}; font-size: 10pt; }}
    #Root {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 16px; }}
    #Title {{ font-size: 12pt; font-weight: 600; }}
    #Side {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 16px; }}
    QPushButton#Nav {{ background: transparent; border: none; border-radius: 10px; padding: 9px 14px;
                       text-align: left; color: {MUTED}; }}
    QPushButton#Nav:hover {{ background: {SURFACE2}; color: {TEXT}; }}
    QPushButton#Nav:checked {{ background: {SURFACE2}; color: {TEXT}; font-weight: 600;
                               border-left: 3px solid {accent}; border-top-left-radius: 4px;
                               border-bottom-left-radius: 4px; }}
    #Card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 14px; }}
    #CardTitle {{ font-size: 10.5pt; font-weight: 600; }}
    #RowLabel {{ color: {MUTED}; }}
    #Value {{ color: {TEXT}; font-family: "Hack", "JetBrains Mono", "DejaVu Sans Mono", monospace; }}
    #PageTitle {{ font-size: 16pt; font-weight: 700; }}
    QSlider::groove:horizontal {{ height: 6px; background: {SURFACE2}; border-radius: 3px; }}
    QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 3px; }}
    QSlider::handle:horizontal {{ background: {TEXT}; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }}
    QSlider::handle:horizontal:hover {{ background: #ffffff; }}
    QLineEdit, QComboBox {{ background: {SURFACE2}; border: 1px solid {BORDER}; border-radius: 10px; padding: 6px 10px; }}
    QLineEdit:focus, QComboBox:hover {{ border-color: {accent}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{ background: {SURFACE2}; border: 1px solid {BORDER}; border-radius: 8px;
                                   selection-background-color: {accent}; outline: none; padding: 4px; }}
    QListWidget#ModList {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 12px; padding: 6px; outline: none; }}
    QListWidget#ModList::item {{ background: {SURFACE2}; border: 1px solid {BORDER}; border-radius: 8px;
                                 padding: 6px 8px; margin: 2px 0; }}
    QListWidget#ModList::item:selected {{ border-color: {accent}; color: {TEXT}; }}
    #TabBox {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; }}
    #TabBox QPushButton#Seg {{ padding: 7px 22px; font-weight: 600; }}
    QPushButton {{ background: {SURFACE2}; border: 1px solid {BORDER}; border-radius: 10px; padding: 8px 16px; }}
    QPushButton:hover {{ border-color: {accent}; }}
    QPushButton:disabled {{ color: #4d5a6b; border-color: {SURFACE2}; }}
    QPushButton#Primary {{ background: {accent}; border: 1px solid {accent}; color: #ffffff; font-weight: 600; }}
    QPushButton#Primary:hover {{ background: {accent}; border-color: #ffffff; }}
    QPushButton#Primary:disabled {{ background: {SURFACE2}; border-color: {SURFACE2}; color: #4d5a6b; }}
    QPushButton#Danger:hover {{ border-color: {DANGER}; color: {DANGER}; }}
    QPushButton#Seg {{ background: transparent; border: none; border-radius: 8px; padding: 6px 14px; color: {MUTED}; }}
    QPushButton#Seg:checked {{ background: {accent}; color: #ffffff; font-weight: 600; }}
    #SegBox {{ background: {SURFACE2}; border: 1px solid {BORDER}; border-radius: 10px; }}
    QToolButton {{ background: transparent; border: none; border-radius: 8px; padding: 4px; }}
    QToolButton:hover {{ background: {SURFACE2}; }}
    QToolButton#CloseBtn:hover {{ background: {DANGER}; }}
    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget#qt_scrollarea_viewport {{ background: transparent; }}
    #ScrollInner {{ background: transparent; }}
    QScrollBar:vertical {{ width: 8px; background: transparent; margin: 4px 0; }}
    QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {accent}; }}
    QScrollBar:horizontal {{ height: 8px; background: transparent; }}
    QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 4px; min-width: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ width: 0; height: 0; background: none; }}
    #BindRow {{ background: {SURFACE2}; border: 1px solid {BORDER}; border-radius: 12px; }}
    #BindRow QComboBox {{ background: {BG}; }}
    QPushButton#Mod {{ background: transparent; padding: 4px 9px; border-radius: 8px; color: {MUTED}; font-size: 9pt; }}
    QPushButton#Mod:checked {{ border-color: {accent}; color: {accent}; font-weight: 600; }}
    QPushButton#KeyBtn {{ background: {BG}; font-family: "JetBrains Mono", "Hack", "Consolas", "JetBrains Mono", "DejaVu Sans Mono", monospace;
                          font-weight: 600; }}
    #Warn {{ background: transparent; border: 1px solid {DANGER}; border-radius: 11px; color: {DANGER}; font-weight: 700; }}
    #Status {{ color: {MUTED}; }}
    QPlainTextEdit {{ background: #0a0e13; border: 1px solid {BORDER}; border-radius: 12px; padding: 8px;
                      font-family: "Hack", "JetBrains Mono", "DejaVu Sans Mono", monospace; font-size: 9pt;
                      color: #b8c4d4; }}
    #Panel {{ background: {SURFACE}; border-right: 1px solid {BORDER}; border-top-left-radius: 16px;
              border-bottom-left-radius: 16px; }}
    #PanelTitle {{ font-size: 13pt; font-weight: 600; }}
    #Label {{ color: {MUTED}; font-size: 9pt; }}
    QPushButton#Lang {{ padding: 6px 14px; }}
    QPushButton#Lang:checked {{ border-color: {accent}; color: {accent}; font-weight: 600; }}
    QToolTip {{ background: {SURFACE2}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 6px; padding: 6px; }}
    QColorDialog, QColorDialog QWidget {{ background: {SURFACE}; }}
    """
