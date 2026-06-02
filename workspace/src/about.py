#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# about.py — Diálogo "Acerca de" para K-Hello (CuerdOS GNU/Linux)
#
# Basado en la plantilla genérica AboutDialog de CuerdOS Project.
# Usa el sistema de traducciones T() y QIcon.fromTheme() en lugar de emojis.

import os

from PySide6.QtCore    import Qt, QUrl
from PySide6.QtGui     import QPixmap, QIcon, QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QWidget, QStyle,
)

from core import (
    APP_NAME, APP_VERSION, APP_WEBSITE,
    find_asset,
)
from translations import T

# ══════════════════════════════════════════════════════════════════════════════
# ── Paleta (dark green-accent, igual a la plantilla original) ─────────────────
# ══════════════════════════════════════════════════════════════════════════════

_C = {
    "header_bg":   "#192511",
    "body_bg":     "#242424",
    "row_alt":     "#2a2a2a",
    "footer_bg":   "#1e1e1e",
    "accent":      "#8aab4a",
    "text":        "#d0d0d0",
    "text_dim":    "#555555",
    "btn_web_bg":  "#2b3020",
    "btn_web_fg":  "#a8c96a",
    "btn_web_br":  "#5a7a30",
    "btn_web_hov": "#384028",
    "btn_cls_bg":  "#2e2e2e",
    "btn_cls_fg":  "#d0d0d0",
    "btn_cls_br":  "#4a4a4a",
    "btn_cls_hov": "#3a3a3a",
    "sep":         "#3a3a3a",
}


# ══════════════════════════════════════════════════════════════════════════════
# ── Helpers ───────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _hsep() -> QFrame:
    """Separador horizontal de 1 px."""
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(f"background:{_C['sep']}; border:none;")
    return line


def _btn(label: str, bg: str, fg: str, border: str, hover: str,
         icon: QIcon | None = None) -> QPushButton:
    b = QPushButton(label)
    if icon and not icon.isNull():
        b.setIcon(icon)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(
        f"QPushButton {{ background:{bg}; color:{fg}; border:1px solid {border};"
        f" border-radius:5px; padding:5px 14px; font-size:11px; }}"
        f"QPushButton:hover {{ background:{hover}; }}"
    )
    return b


def _app_logo() -> QPixmap | None:
    """Devuelve el QPixmap del logo de la aplicación, o None si no existe."""
    path = find_asset("k-hello.svg") or find_asset("cuerdos.svg")
    if path:
        pm = QPixmap(path)
        if not pm.isNull():
            return pm.scaled(
                80, 80,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
    return None


def _theme_icon(name: str, fallback_sp=None) -> QIcon:
    """
    Devuelve un QIcon del tema del sistema. Si no existe usa el StandardPixmap
    de fallback (si se proporciona).
    """
    icon = QIcon.fromTheme(name)
    if not icon.isNull():
        return icon
    if fallback_sp is not None:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            return app.style().standardIcon(fallback_sp)
    return QIcon()


# ══════════════════════════════════════════════════════════════════════════════
# AboutDialog
# ══════════════════════════════════════════════════════════════════════════════

class AboutDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        # ── Títulos / strings traducidos ──────────────────────────────────
        self.setWindowTitle(T("about_title"))
        self.setWindowIcon(_theme_icon("help-about",
                                       QStyle.StandardPixmap.SP_MessageBoxInformation))
        self.setFixedWidth(460)
        self.setModal(True)

        # Filas de información (etiqueta traducida, valor)
        info_rows = [
            (T("about_version"),  f"v{APP_VERSION}"),
            (T("about_license"),  "GNU GPL v3.0"),
            (T("about_authors"),  "CuerdOS Dev. Team"),
        ]

        # Subtítulo del header ("© 2026 CuerdOS Project")
        app_subtitle = "\u00a9 2026 CuerdOS Project"
        # Descripción al pie del body (en cursiva)
        app_desc = T("about_description")

        # ── Layout exterior ───────────────────────────────────────────────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet(f"background:{_C['header_bg']};")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(0, 24, 0, 20)
        hl.setSpacing(0)
        hl.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        logo_pm = _app_logo()
        if logo_pm:
            lbl_icon = QLabel()
            lbl_icon.setPixmap(logo_pm)
            lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hl.addWidget(lbl_icon)
            hl.addSpacing(8)

        lbl_name = QLabel(APP_NAME)
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_name.setStyleSheet(
            "font-size:20px; font-weight:bold; color:#ffffff; background:transparent;")
        hl.addWidget(lbl_name)

        lbl_sub = QLabel(app_subtitle)
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setStyleSheet(
            f"font-size:11px; color:{_C['accent']};"
            " background:transparent; margin-top:2px;")
        hl.addWidget(lbl_sub)

        outer.addWidget(header)
        outer.addWidget(_hsep())

        # ── Body ──────────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet(f"background:{_C['body_bg']};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 16, 28, 16)
        bl.setSpacing(0)

        for i, (label, value) in enumerate(info_rows):
            row_w = QWidget()
            row_w.setStyleSheet(
                f"background:{_C['row_alt']}; border-radius:6px;"
                if i % 2 == 0 else
                f"background:{_C['body_bg']};")
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(12, 7, 12, 7)
            rl.setSpacing(8)

            lbl_l = QLabel(label)
            lbl_l.setStyleSheet(
                f"color:{_C['accent']}; font-size:11px; font-weight:bold;"
                " min-width:90px; background:transparent;")

            lbl_v = QLabel(value)
            lbl_v.setStyleSheet(
                f"color:{_C['text']}; font-size:11px; background:transparent;")
            lbl_v.setWordWrap(True)

            rl.addWidget(lbl_l)
            rl.addWidget(lbl_v, 1)
            bl.addWidget(row_w)

        if app_desc:
            bl.addSpacing(12)
            lbl_desc = QLabel(app_desc)
            lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet(
                f"color:{_C['text_dim']}; font-size:10px;"
                " font-style:italic; background:transparent;")
            bl.addWidget(lbl_desc)

        outer.addWidget(body)
        outer.addWidget(_hsep())

        # ── Footer ────────────────────────────────────────────────────────
        footer = QWidget()
        footer.setFixedHeight(52)
        footer.setStyleSheet(f"background:{_C['footer_bg']};")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 0, 24, 0)
        fl.setSpacing(8)
        fl.addStretch()

        if APP_WEBSITE:
            web_icon = _theme_icon("internet-web-browser",
                                   QStyle.StandardPixmap.SP_DriveNetIcon)
            btn_web = _btn(
                T("visit_website"),
                _C["btn_web_bg"], _C["btn_web_fg"],
                _C["btn_web_br"], _C["btn_web_hov"],
                icon=web_icon,
            )
            btn_web.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(APP_WEBSITE)))
            fl.addWidget(btn_web)

        close_icon = _theme_icon("window-close",
                                 QStyle.StandardPixmap.SP_DialogCloseButton)
        btn_close = _btn(
            T("about_close"),
            _C["btn_cls_bg"], _C["btn_cls_fg"],
            _C["btn_cls_br"], _C["btn_cls_hov"],
            icon=close_icon,
        )
        btn_close.clicked.connect(self.accept)
        fl.addWidget(btn_close)

        outer.addWidget(footer)
