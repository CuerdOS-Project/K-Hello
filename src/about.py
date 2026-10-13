#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# about.py — Diálogo "Acerca de" para K-Hello (CuerdOS GNU/Linux)
#
# Basado en la plantilla genérica AboutDialog de CuerdOS Project.
# Usa el sistema de traducciones T() y QIcon.fromTheme() en lugar de emojis.
#
# Los colores se derivan de la paleta activa de Qt (QApplication.palette()),
# la misma que usa el resto de K-Hello, por lo que el diálogo sigue el modo
# claro/oscuro del sistema automáticamente, sin valores fijos.

import os

from PySide6.QtCore    import Qt, QUrl
from PySide6.QtGui     import QPixmap, QIcon, QDesktopServices, QPalette, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QWidget, QStyle, QApplication,
)

from core import (
    APP_NAME, APP_VERSION, APP_WEBSITE,
    find_asset,
)
from translations import T


# ══════════════════════════════════════════════════════════════════════════════
# ── Paleta dinámica (derivada de QApplication.palette(), sigue dark/light) ────
# ══════════════════════════════════════════════════════════════════════════════

def _readable_variant(color: QColor, on_light: bool) -> QColor:
    """
    Devuelve una variante del color de acento con la luminosidad forzada a
    un rango legible como texto: oscura sobre fondos claros, clara sobre
    fondos oscuros. Conserva el matiz/saturación del acento del tema
    (algunos temas usan un "highlight" muy pálido, poco legible como texto
    tal cual).
    """
    h, s, _l, a = color.getHsl()
    if h == -1:
        s = 0
    target_l = 95 if on_light else 190
    fixed = QColor()
    fixed.setHsl(h if h != -1 else 0, s, target_l, a)
    return fixed


def _build_colors() -> dict:
    """
    Construye la paleta de colores del diálogo a partir de la paleta activa
    de Qt. Se recalcula cada vez que se abre el diálogo, de modo que si el
    usuario cambia de tema claro a oscuro (o viceversa) en caliente, el
    "Acerca de" siempre coincide con el resto del sistema.
    """
    pal = QApplication.palette()
    hl = pal.color(QPalette.ColorRole.Highlight)
    window = pal.color(QPalette.ColorRole.Window)
    is_dark = window.lightness() < 128

    # Cabecera: una variante del color de acento, oscurecida para dar
    # contraste al logo y al texto en blanco/negro de encima.
    header_bg = hl.darker(170) if is_dark else hl.darker(120)
    header_fg = QColor("#ffffff") if header_bg.lightness() < 140 else QColor("#101010")

    # Variante del acento con contraste garantizado para usarse como texto
    # (etiquetas, botón "Visitar web") sobre el fondo del cuerpo/pie.
    accent_text = _readable_variant(hl, on_light=not is_dark)

    text = pal.color(QPalette.ColorRole.WindowText)
    text_dim = pal.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText)

    return {
        "header_bg":   header_bg.name(),
        "header_fg":   header_fg.name(),
        "accent":      accent_text.name(),
        "text":        text.name(),
        "text_dim":    text_dim.name(),
        "row_alt":     "rgba(128,128,128,0.10)",
        "footer_bg":   "rgba(128,128,128,0.06)",
        "sep":         "palette(mid)",
        "btn_web_bg":  f"rgba({accent_text.red()},{accent_text.green()},{accent_text.blue()},0.14)",
        "btn_web_fg":  accent_text.name(),
        "btn_web_br":  f"rgba({accent_text.red()},{accent_text.green()},{accent_text.blue()},0.55)",
        "btn_web_hov": f"rgba({accent_text.red()},{accent_text.green()},{accent_text.blue()},0.24)",
        "btn_cls_bg":  "rgba(128,128,128,0.12)",
        "btn_cls_fg":  text.name(),
        "btn_cls_br":  "palette(mid)",
        "btn_cls_hov": "rgba(128,128,128,0.22)",
    }


# ══════════════════════════════════════════════════════════════════════════════
# ── Helpers ───────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _hsep(color: str) -> QFrame:
    """Separador horizontal de 1 px."""
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(f"background:{color}; border:none;")
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
        from widgets import render_svg_pixmap
        pm = render_svg_pixmap(path, 80)
        if not pm.isNull():
            return pm
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

        _C = _build_colors()

        # ── Títulos / strings traducidos ──────────────────────────────────
        self.setWindowTitle(T("about_title"))
        self.setWindowIcon(_theme_icon("help-about",
                                       QStyle.StandardPixmap.SP_MessageBoxInformation))
        self.setFixedWidth(460)
        self.setModal(True)

        # Filas de información (etiqueta traducida, valor)
        info_rows = [
            (T("about_version"),  APP_VERSION),
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
            f"font-size:20px; font-weight:bold; color:{_C['header_fg']}; background:transparent;")
        hl.addWidget(lbl_name)

        _sub_rgb = "255,255,255" if _C["header_fg"] == "#ffffff" else "16,16,16"
        lbl_sub = QLabel(app_subtitle)
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setStyleSheet(
            f"font-size:11px; color:rgba({_sub_rgb},0.75);"
            " background:transparent; margin-top:2px;")
        hl.addWidget(lbl_sub)

        outer.addWidget(header)
        outer.addWidget(_hsep(_C["sep"]))

        # ── Body ──────────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet("background:palette(window);")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 16, 28, 16)
        bl.setSpacing(0)

        for i, (label, value) in enumerate(info_rows):
            row_w = QWidget()
            row_w.setStyleSheet(
                f"background:{_C['row_alt']}; border-radius:6px;"
                if i % 2 == 0 else
                "background:transparent;")
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
        outer.addWidget(_hsep(_C["sep"]))

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
