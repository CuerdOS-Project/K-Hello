#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
first_use_window.py — Tour de bienvenida de primer arranque de K-Hello.

Cuatro diapositivas navegables con botones circulares Atrás/Siguiente a los
lados de una imagen 1:1 central, y un título + subtítulo debajo.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PySide6.QtGui import QFont, QFontMetrics, QPalette, QPixmap
from PySide6.QtWidgets import (
    QDialog, QApplication, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QWidget,
)

from translations import T
from core import APP_NAME, find_asset, mark_first_run_done
from widgets import SquareImageLabel, CircleIconButton


class FirstUseWindow(QDialog):
    """Tour de bienvenida de primer arranque con cuatro diapositivas."""

    # La primera diapositiva es una portada de marca; el resto usa arte 1:1.
    # Cada elemento: (recurso visual, clave de título, clave de subtítulo)
    _SLIDES = [
        ("cuerdos-banner.webp", "tour_s1_title", "tour_s1_subtitle"),
        ("fmt2.webp", "tour_s2_title", "tour_s2_subtitle"),
        ("fmt3.webp", "tour_s_love_title", "tour_s_love_subtitle"),
        ("fmt4.webp", "tour_s3_title", "tour_s3_subtitle"),
    ]

    def __init__(self, on_done_callback):
        super().__init__()
        self.on_done = on_done_callback
        self._current_slide = 0

        self.setWindowTitle(APP_NAME)
        self.setFixedSize(900, 650)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )

        self._setup_ui()

    # ------------------------------------------------------------------
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 28)
        root.setSpacing(0)

        # Fila superior: opción clara para entrar directamente a la app.
        top_row = QHBoxLayout()
        top_row.addStretch(1)
        self._skip_btn = QPushButton(T("tour_skip"))
        self._skip_btn.setFlat(True)
        self._skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._skip_btn.clicked.connect(self._finish_tour)
        top_row.addWidget(self._skip_btn)
        root.addLayout(top_row)

        # La imagen ocupa una fila propia: queda centrada en la ventana,
        # independiente de los controles de navegación.
        nav_row = QHBoxLayout()
        nav_row.addStretch(1)

        self._visual_host = QWidget()
        self._visual_host.setFixedSize(520, 299)
        visual_grid = QGridLayout(self._visual_host)
        visual_grid.setContentsMargins(0, 0, 0, 0)
        visual_grid.setSpacing(0)

        self._banner_lbl = QLabel()
        self._banner_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._banner_lbl.setFixedSize(520, 299)
        self._banner_lbl.setStyleSheet("background: transparent; border: none;")
        banner_path = find_asset("cuerdos-banner.webp")
        self._banner_pixmap = QPixmap(banner_path) if banner_path else QPixmap()
        if not self._banner_pixmap.isNull():
            self._banner_lbl.setPixmap(self._banner_pixmap.scaled(
                500, 190,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            self._banner_lbl.setAccessibleName("CuerdOS")

        # 299 px mantiene el tamaño original de las ilustraciones del tour.
        self._image_lbl = SquareImageLabel(side_len=299)
        # Ambos recursos ocupan la misma celda. La cuadrícula los centra
        # explícitamente: el arte 1:1 queda centrado en los 520 px del host,
        # igual que el banner panorámico.
        visual_grid.addWidget(
            self._image_lbl, 0, 0, Qt.AlignmentFlag.AlignCenter
        )
        visual_grid.addWidget(
            self._banner_lbl, 0, 0, Qt.AlignmentFlag.AlignCenter
        )
        self._banner_lbl.hide()
        nav_row.addWidget(self._visual_host, 0, Qt.AlignmentFlag.AlignVCenter)
        nav_row.addStretch(1)
        root.addLayout(nav_row, 1)

        # Título + subtítulo de la diapositiva actual. Reservan siempre la
        # misma altura (2 líneas cada uno) para que la
        # fila visual central nunca se
        # desplace verticalmente al cambiar de diapositiva, aunque el
        # texto de una diapositiva concreta sea más corto o no tenga
        # subtítulo.
        self._title_lbl = QLabel()
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_lbl.setWordWrap(True)
        tf = QFont(); tf.setPixelSize(20); tf.setBold(True)
        self._title_lbl.setFont(tf)
        self._title_lbl.setMinimumHeight(QFontMetrics(tf).lineSpacing() * 2 + 4)
        root.addWidget(self._title_lbl)

        self._subtitle_lbl = QLabel()
        self._subtitle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle_lbl.setWordWrap(True)
        sf = QFont(); sf.setPixelSize(13)
        self._subtitle_lbl.setFont(sf)
        self._subtitle_lbl.setMinimumHeight(QFontMetrics(sf).lineSpacing() * 2 + 4)
        _sp = self._subtitle_lbl.palette()
        _sp.setColor(QPalette.ColorRole.WindowText, QApplication.palette().placeholderText().color())
        self._subtitle_lbl.setPalette(_sp)
        root.addWidget(self._subtitle_lbl)

        # La imagen y los textos entran suavemente en cada cambio de página.
        self._transition_group = None
        self._image_effect = self._make_fade_effect(self._visual_host)
        self._title_effect = self._make_fade_effect(self._title_lbl)
        self._subtitle_effect = self._make_fade_effect(self._subtitle_lbl)

        root.addSpacing(18)

        # Puntos indicadores de progreso.
        dots_row = QHBoxLayout()
        dots_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dots_row.setSpacing(10)
        self._dots: list[QLabel] = []
        for _ in self._SLIDES:
            dot = QLabel("●")
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._dots.append(dot)
            dots_row.addWidget(dot)
        self._step_lbl = QLabel()
        self._step_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        step_font = QFont(); step_font.setPixelSize(11)
        self._step_lbl.setFont(step_font)
        step_palette = self._step_lbl.palette()
        step_palette.setColor(
            QPalette.ColorRole.WindowText,
            QApplication.palette().placeholderText().color(),
        )
        self._step_lbl.setPalette(step_palette)
        self._back_btn = CircleIconButton(direction="left", diameter=48)
        self._back_btn.setAccessibleName(T("first_back"))
        self._back_btn.setToolTip(T("first_back"))
        self._back_btn.clicked.connect(self._on_back)

        self._next_btn = CircleIconButton(direction="right", diameter=48)
        self._next_btn.clicked.connect(self._on_continue)

        # Controles al pie del recorrido: ninguna flecha compite visualmente
        # con el banner o desplaza las ilustraciones del centro.
        footer = QHBoxLayout()
        footer.setSpacing(14)
        footer.addWidget(self._back_btn)
        footer.addStretch(1)
        footer.addLayout(dots_row)
        footer.addWidget(self._step_lbl)
        footer.addStretch(1)
        footer.addWidget(self._next_btn)
        root.addLayout(footer)

        self._refresh_slide()

    # ------------------------------------------------------------------
    # Navegación
    # ------------------------------------------------------------------

    def _make_fade_effect(self, widget):
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(1.0)
        widget.setGraphicsEffect(effect)
        return effect

    def _animate_transition(self):
        if self._transition_group:
            self._transition_group.stop()
        effects = (self._image_effect, self._title_effect, self._subtitle_effect)
        for effect in effects:
            effect.setOpacity(0.0)
        group = QParallelAnimationGroup(self)
        for effect in effects:
            animation = QPropertyAnimation(effect, b"opacity", group)
            animation.setDuration(280)
            animation.setStartValue(0.0)
            animation.setEndValue(1.0)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            group.addAnimation(animation)
        self._transition_group = group
        # No usar DeleteWhenStopped: conservamos la referencia para poder
        # detener limpiamente una transición si el usuario pulsa varias
        # veces Atrás/Siguiente antes de que termine.
        group.start()

    def _refresh_slide(self):
        image_name, title_key, subtitle_key = self._SLIDES[self._current_slide]

        is_brand_cover = image_name == "cuerdos-banner.webp" and not self._banner_pixmap.isNull()
        if is_brand_cover:
            self._image_lbl.hide()
            self._banner_lbl.show()
        else:
            self._image_lbl.set_image_path(
                find_asset("fmt1.webp") if image_name == "cuerdos-banner.webp"
                else find_asset(image_name)
            )
            self._banner_lbl.hide()
            self._image_lbl.show()
        self._title_lbl.setText(T(title_key))

        subtitle = T(subtitle_key) if subtitle_key else ""
        self._subtitle_lbl.setText(subtitle)

        hl = QApplication.palette().highlight().color()
        dim = QApplication.palette().placeholderText().color()
        for i, dot in enumerate(self._dots):
            pal = dot.palette()
            if i == self._current_slide:
                _f = dot.font(); _f.setPixelSize(18); dot.setFont(_f)
                pal.setColor(QPalette.ColorRole.WindowText, hl)
            else:
                _f = dot.font(); _f.setPixelSize(11); dot.setFont(_f)
                pal.setColor(QPalette.ColorRole.WindowText, dim)
            dot.setPalette(pal)

        self._step_lbl.setText(T("tour_step").format(
            current=self._current_slide + 1, total=len(self._SLIDES)
        ))

        self._back_btn.setEnabled(self._current_slide > 0)
        is_last = self._current_slide == len(self._SLIDES) - 1
        self._next_btn.setToolTip(T("first_get_started") if is_last else T("first_continue"))
        self._next_btn.setAccessibleName(
            T("first_get_started") if is_last else T("first_continue")
        )
        self._next_btn.set_highlighted(is_last)
        self._animate_transition()

    def _on_back(self):
        if self._current_slide > 0:
            self._current_slide -= 1
            self._refresh_slide()

    def _on_continue(self):
        if self._current_slide < len(self._SLIDES) - 1:
            self._current_slide += 1
            self._refresh_slide()
        else:
            self._finish_tour()

    def _finish_tour(self):
        """Finaliza el primer recorrido y abre Inicio, incluso al omitirlo."""
        mark_first_run_done()
        self.on_done()
        self.accept()

    # Mantener nombre público antiguo por compatibilidad
    def on_continue(self):
        self._on_continue()
