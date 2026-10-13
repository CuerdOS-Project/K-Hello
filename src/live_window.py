#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
live_window.py — Ventana de modo live de K-Hello.
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, QElapsedTimer, QTimer, QRectF
from PySide6.QtGui import QPixmap, QColor, QPalette, QPainter
from PySide6.QtWidgets import (
    QDialog, QApplication, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSizePolicy, QWidget,
)

from translations import T, set_language, get_language_pref, AVAILABLE_LANGUAGES
from core import find_asset, launch_app
from widgets import make_card, set_card_text
from theme import BRAND_GREEN, INSTALL_ACCENT


class LiveLogoIntro(QWidget):
    """Banner de CuerdOS centrado con una entrada y flotación suave."""

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._pixmap = pixmap
        self._elapsed_ms = 0
        self.setMinimumHeight(112)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setAccessibleName("CuerdOS")

    def set_animation_time(self, elapsed_ms: int):
        self._elapsed_ms = elapsed_ms
        self.update()

    def paintEvent(self, event):
        if self._pixmap.isNull() or self.width() <= 0 or self.height() <= 0:
            return

        elapsed = self._elapsed_ms / 1000.0
        scale, opacity = 1.0, 1.0
        # El logo flota arriba y abajo en un ciclo de cinco segundos,
        # conservando siempre el centro horizontal.
        dy = 7.0 * math.sin(2.0 * math.pi * (elapsed % 5.0) / 5.0)

        # Breve entrada inicial; después queda únicamente el movimiento
        # flotante, sin cambiar de estilo ni desplazarse hacia los lados.
        if elapsed < 1.0:
            progress = min(1.0, elapsed / 0.8)
            eased = 1.0 - (1.0 - progress) ** 3
            scale = 0.90 + 0.10 * eased
            opacity = 0.18 + 0.82 * eased

        bounds = self.rect().adjusted(24, 12, -24, -12)
        fit = min(
            bounds.width() / self._pixmap.width(),
            bounds.height() / self._pixmap.height(),
        )
        width = self._pixmap.width() * fit * scale
        height = self._pixmap.height() * fit * scale
        target = QRectF(
            bounds.center().x() - width / 2,
            bounds.center().y() - height / 2 + dy,
            width,
            height,
        )

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setOpacity(opacity)
        painter.drawPixmap(target, self._pixmap, QRectF(self._pixmap.rect()))


class LiveModeWindow(QDialog):
    """Diálogo compacto de modo live: selector de idioma + dos botones de acción."""

    def __init__(self, installer_cmd, on_try_callback, install_label=None):
        super().__init__()
        self.installer_cmd = installer_cmd
        self.on_try_callback = on_try_callback
        self.install_label = install_label
        self._intro_clock = QElapsedTimer()
        self._header_colors = tuple(map(QColor, (
            BRAND_GREEN, "#12444A", "#1B3655", "#49345E", "#633A4C",
            "#31513F",
        )))

        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )
        self.setFixedSize(710, 545)
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle(T("live_title"))

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Cabecera animada: el banner flota centrado; el selector vive junto
        # a la pregunta Live, debajo.
        header = QWidget()
        header.setObjectName("liveHeader")
        header.setAutoFillBackground(True)
        _pal = header.palette()
        _pal.setColor(QPalette.ColorRole.Window, QColor(BRAND_GREEN))
        # Mantener legible el banner sobre todos los tonos oscuros del ciclo.
        _header_fg = QColor("#EAF6EF")
        for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                     QPalette.ColorRole.ButtonText):
            _pal.setColor(role, _header_fg)
        header.setPalette(_pal)
        header.setMinimumHeight(158)

        h_lay = QVBoxLayout(header)
        h_lay.setContentsMargins(20, 12, 20, 16)
        h_lay.setSpacing(4)

        self._banner_lbl = LiveLogoIntro(QPixmap())
        banner_path = find_asset("cuerdos-banner.webp")
        if banner_path:
            self._banner_lbl = LiveLogoIntro(QPixmap(banner_path))
        h_lay.addWidget(self._banner_lbl, 1)

        root.addWidget(header)
        self._header = header

        self._lang_combo = QComboBox()
        self._lang_combo.setMinimumWidth(130)
        self._lang_combo.setPalette(QApplication.palette())
        self._lang_combo.view().setPalette(QApplication.palette())
        for code, name in AVAILABLE_LANGUAGES.items():
            self._lang_combo.addItem(name, code)
        self._lang_combo.currentIndexChanged.connect(self._on_lang_changed)

        self._subtitle_lbl = QLabel()
        self._subtitle_lbl.setWordWrap(True)
        self._subtitle_lbl.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        _fs = self._subtitle_lbl.font(); _fs.setPixelSize(13)
        self._subtitle_lbl.setFont(_fs)

        question_row = QHBoxLayout()
        question_row.setContentsMargins(28, 16, 28, 0)
        question_row.setSpacing(16)
        question_row.addWidget(self._lang_combo, 0, Qt.AlignmentFlag.AlignVCenter)
        question_row.addWidget(self._subtitle_lbl, 1)
        root.addLayout(question_row)

        cards_widget = QWidget()
        cards_lay = QHBoxLayout(cards_widget)
        cards_lay.setContentsMargins(28, 24, 28, 28)
        cards_lay.setSpacing(20)

        # El botón de instalar usa un color de acento propio (distinto del
        # resto de la GUI, que sigue el tema nativo) para diferenciarlo
        # claramente como la acción principal de esta ventana.
        self._install_btn = make_card(
            find_asset("install.svg"), "system-software-install", "", "",
            self._on_install, enabled=self.installer_cmd is not None,
            min_size=(220, 180), icon_size=56, tint=True,
            tint_color=QColor(INSTALL_ACCENT["text"]),
        )
        self._install_btn.setObjectName("installCard")
        self._install_btn.setStyleSheet(f"""
            QPushButton#installCard {{
                background-color: {INSTALL_ACCENT['base']};
                border: 1px solid {INSTALL_ACCENT['border']};
                border-radius: 12px;
            }}
            QPushButton#installCard:hover {{
                background-color: {INSTALL_ACCENT['hover']};
            }}
            QPushButton#installCard:pressed {{
                background-color: {INSTALL_ACCENT['pressed']};
            }}
            QPushButton#installCard:disabled {{
                background-color: {INSTALL_ACCENT['disabled']};
                border-color: #23392F;
            }}
            QPushButton#installCard QLabel {{
                color: {INSTALL_ACCENT['text']};
                background: transparent;
            }}
        """)
        cards_lay.addWidget(self._install_btn)

        self._try_btn = make_card(
            find_asset("live-try.svg"), "media-playback-start", "", "", self._on_try, enabled=True,
            min_size=(220, 180), icon_size=56, tint=True,
        )
        cards_lay.addWidget(self._try_btn)

        root.addWidget(cards_widget)
        self._refresh_texts()
        self._start_intro_animation()

    def _start_intro_animation(self):
        """Actualiza la flotación del logo y el tono a 30 cuadros por segundo."""
        self._intro_clock.start()
        self._intro_timer = QTimer(self)
        self._intro_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._intro_timer.setInterval(33)
        self._intro_timer.timeout.connect(self._advance_intro_frame)
        self._intro_timer.start()
        self._advance_intro_frame()

    def _advance_intro_frame(self):
        elapsed = self._intro_clock.elapsed()
        self._banner_lbl.set_animation_time(elapsed)

        # Transición continua entre tonos oscuros, con un nuevo color cada
        # cinco segundos; el mismo reloj mantiene logo y fondo sincronizados.
        segment_ms = 5000
        color_position = (elapsed % (len(self._header_colors) * segment_ms)) / segment_ms
        index = int(color_position)
        amount = color_position - index
        start = self._header_colors[index]
        end = self._header_colors[(index + 1) % len(self._header_colors)]
        color = QColor(
            round(start.red() + (end.red() - start.red()) * amount),
            round(start.green() + (end.green() - start.green()) * amount),
            round(start.blue() + (end.blue() - start.blue()) * amount),
        )
        palette = self._header.palette()
        palette.setColor(QPalette.ColorRole.Window, color)
        self._header.setPalette(palette)

    def _refresh_texts(self):
        self.setWindowTitle(T("live_title"))
        self._subtitle_lbl.setText(T("live_subtitle"))

        self._lang_combo.blockSignals(True)
        idx = self._lang_combo.findData(get_language_pref())
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        self._lang_combo.blockSignals(False)

        install_label = self.install_label or T("live_install_label")
        set_card_text(self._install_btn, install_label, T("live_install_desc"))
        set_card_text(self._try_btn, T("live_try_label"), T("live_try_desc"))

    def _on_lang_changed(self):
        code = self._lang_combo.currentData()
        if code:
            set_language(code)
            self._refresh_texts()

    def _on_install(self):
        if self.installer_cmd:
            launch_app(self.installer_cmd)
        self.accept()

    def _on_try(self):
        self.on_try_callback()
        self.accept()
