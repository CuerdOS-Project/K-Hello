#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
widgets.py — Componentes Qt reutilizables de K-Hello.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, QTimer, QSize, QPointF, QRectF, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap, QPolygonF, QIcon, QPalette, QPainterPath
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QHBoxLayout, QApplication,
    QDialog,
)

from core import get_available_commands, launch_first_available, display_name_for, icon_for, launch_app
from translations import T
from theme import HOME_COLORS, HOME_FG_DARK, HOME_FG_LIGHT, HOME_LIGHT_BACKGROUNDS, HOME_CHARACTER_SIZE


def _lerp_color(a: QColor, b: QColor, t: float) -> QColor:
    """Interpola linealmente entre dos QColor (t entre 0 y 1)."""
    t = max(0.0, min(1.0, t))
    return QColor(
        round(a.red()   + (b.red()   - a.red())   * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue()  + (b.blue()  - a.blue())  * t),
        round(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


# =============================================================================
# Fondo animado de montañas geométricas
# =============================================================================

class GeometricMountainsWidget(QWidget):
    """Fondo animado de montañas geométricas que se desplazan de izquierda a derecha."""

    _LAYERS = [
        (0.20, 0.07, [
            (0.00, 0.58, 0.17), (0.17, 0.82, 0.15), (0.33, 0.48, 0.16),
            (0.50, 0.92, 0.20), (0.65, 0.63, 0.14), (0.80, 0.77, 0.18),
            (0.95, 0.53, 0.13), (1.10, 0.87, 0.17), (1.25, 0.68, 0.15),
        ]),
        (0.50, 0.13, [
            (0.04, 0.52, 0.14), (0.21, 0.78, 0.17), (0.37, 0.43, 0.12),
            (0.53, 0.88, 0.19), (0.68, 0.58, 0.14), (0.83, 0.72, 0.16),
            (0.98, 0.47, 0.11), (1.13, 0.83, 0.18),
        ]),
        (0.90, 0.20, [
            (0.02, 0.62, 0.15), (0.20, 0.86, 0.21), (0.38, 0.48, 0.13),
            (0.56, 0.94, 0.23), (0.73, 0.57, 0.15), (0.89, 0.78, 0.19),
            (1.06, 0.43, 0.12), (1.22, 0.82, 0.20),
        ]),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)

        self._offset = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _tick(self):
        self._offset += 0.7
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            painter.end()
            return

        bg = self.palette().window().color()
        painter.fillRect(0, 0, w, h, bg)

        hl = self.palette().highlight().color()
        r, g, b = hl.red(), hl.green(), hl.blue()
        painter.setPen(Qt.PenStyle.NoPen)

        for speed, alpha, peaks in self._LAYERS:
            painter.setBrush(QColor(r, g, b, int(alpha * 255)))
            shift = (self._offset * speed) % w

            for tile in (-1, 0, 1):
                x_base = tile * w - shift
                for cx_f, ph_f, hw_f in peaks:
                    cx = cx_f * w + x_base
                    peak_y = h - ph_f * h * 0.88
                    hw = hw_f * w
                    painter.drawPolygon(QPolygonF([
                        QPointF(cx - hw, h),
                        QPointF(cx, peak_y),
                        QPointF(cx + hw, h),
                    ]))

        painter.end()


# =============================================================================
# Fondo estático abstracto para primer arranque
# =============================================================================

class StaticSceneWidget(QWidget):
    """Fondo estático con círculos superpuestos en el color highlight del sistema."""

    # (centro_x, centro_y, radio_x, radio_y, alpha) — todo en ratio relativo al widget
    _SHAPES = [
        (0.10, 1.00, 0.80, 0.80, 0.18),
        (0.85, 0.10, 0.60, 0.60, 0.12),
        (0.45, 0.55, 0.50, 0.50, 0.22),
        (-0.05, 0.35, 0.42, 0.42, 0.14),
        (0.92, 0.80, 0.38, 0.38, 0.16),
        (0.60, -0.05, 0.30, 0.30, 0.10),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            painter.end()
            return

        bg = self.palette().window().color()
        painter.fillRect(0, 0, w, h, bg)

        hl = self.palette().highlight().color()
        r, g, b = hl.red(), hl.green(), hl.blue()
        base = min(w, h)
        painter.setPen(Qt.PenStyle.NoPen)

        for cx_f, cy_f, rx_f, ry_f, alpha in self._SHAPES:
            cx = int(cx_f * w)
            cy = int(cy_f * h)
            rx = int(rx_f * base)
            ry = int(ry_f * base)
            painter.setBrush(QColor(r, g, b, int(alpha * 255)))
            painter.drawEllipse(cx - rx, cy - ry, rx * 2, ry * 2)

        painter.end()


# =============================================================================
# Chip / etiqueta tipo pastilla
# =============================================================================

class ChipLabel(QLabel):
    """Etiqueta tipo chip con fondo redondeado pintado sin CSS."""

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.palette().highlight().color()
        c.setAlpha(45)
        painter.setBrush(c)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)
        painter.end()
        super().paintEvent(event)


# =============================================================================
# Imagen que se reescala manteniendo proporción
# =============================================================================

class ScalingImageLabel(QLabel):
    """QLabel que conserva el pixmap original y lo reescala dinámicamente
    al cambiar de tamaño, ocupando un porcentaje fijo del ancho disponible
    (manteniendo la proporción de aspecto)."""

    def __init__(self, scale_ratio: float = 0.7, parent=None):
        super().__init__(parent)
        self._raw_pixmap: QPixmap | None = None
        self._scale_ratio = scale_ratio
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setMinimumSize(1, 1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_source_pixmap(self, pixmap: QPixmap):
        self._raw_pixmap = pixmap
        self._refresh_pixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_pixmap()

    def _refresh_pixmap(self):
        if not self._raw_pixmap or self._raw_pixmap.isNull():
            return
        target_w = max(1, int(self.width() * self._scale_ratio))
        target_h = max(1, int(self.height() * self._scale_ratio))
        scaled = self._raw_pixmap.scaled(
            target_w, target_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)


# =============================================================================
# Botón de navegación de la barra lateral
# =============================================================================

class NavButton(QPushButton):
    """Botón checkable de la barra de navegación: icono simbólico (SVG)
    siempre visible, con texto solo cuando está activo/marcado."""

    def __init__(self, text: str, icon_path: str | None, parent=None):
        super().__init__(parent)
        self._label_text = text
        self._icon_path = icon_path
        self.setCheckable(True)
        self.setFlat(True)
        self.setMinimumHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(self._sync_state)
        self._sync_state(False)

    def _sync_state(self, checked: bool):
        # Texto: solo visible cuando la pestaña está activa.
        self.setText(self._label_text if checked else "")

        # Icono: se retiñe según el color de texto que corresponda al
        # estado (resaltado si está activo, normal si no).
        pal = self.palette()
        role = QPalette.ColorRole.ButtonText
        src = QApplication.palette()
        color = src.highlightedText().color() if checked else src.buttonText().color()
        pal.setColor(role, color)
        self.setPalette(pal)

        if self._icon_path:
            icon = tinted_icon(self._icon_path, color, size=18)
            if not icon.isNull():
                self.setIcon(icon)
                self.setIconSize(QSize(18, 18))

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)

        if self.isChecked():
            painter.setBrush(self.palette().highlight())
            painter.setPen(Qt.PenStyle.NoPen)
        elif self.underMouse():
            painter.setBrush(self.palette().midlight())
            pen = painter.pen()
            pen.setColor(self.palette().mid().color())
            pen.setWidth(1)
            painter.setPen(pen)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            pen = painter.pen()
            pen.setColor(self.palette().mid().color())
            pen.setWidth(1)
            painter.setPen(pen)

        painter.drawRoundedRect(r, 7, 7)
        painter.end()
        super().paintEvent(event)


def make_card(
    svg_path: str | None,
    theme_icon: str,
    title: str,
    desc: str,
    callback,
    enabled: bool = True,
    min_size: tuple[int, int] = (180, 160),
    icon_size: int = 52,
    property_name: str = "liveCard",
    tint: bool = False,
    tint_color: QColor | None = None,
) -> QPushButton:
    """Tarjeta genérica reutilizable: icono + título + descripción.

    Si ``tint`` es True, ``svg_path`` se trata como un icono simbólico
    monocromo (igual que los de la barra lateral) y se retiñe con el
    color de texto actual de la paleta, de forma que se adapta solo
    al pasar de tema claro a oscuro (o viceversa). Pasa ``tint_color``
    para forzar un color de retinte concreto (p. ej. blanco sobre una
    tarjeta con fondo de acento propio) en lugar del de la paleta."""
    import os

    btn = QPushButton()
    btn.setEnabled(enabled)
    btn.setProperty(property_name, True)
    btn.setMinimumSize(*min_size)
    btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    btn.clicked.connect(callback)

    lay = QVBoxLayout(btn)
    lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.setSpacing(8)

    icon_lbl = QLabel()
    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_lbl.setObjectName("cardIcon")
    pix = None
    if svg_path and os.path.isfile(svg_path):
        if tint:
            color = tint_color or QApplication.palette().windowText().color()
            icon = tinted_icon(svg_path, color, size=icon_size)
            if not icon.isNull():
                pix = icon.pixmap(QSize(icon_size, icon_size))
        else:
            pix = render_svg_pixmap(svg_path, icon_size)
    if pix is None or pix.isNull():
        icon = QIcon.fromTheme(theme_icon)
        if not icon.isNull():
            pix = icon.pixmap(QSize(icon_size, icon_size))
    if pix and not pix.isNull():
        icon_lbl.setPixmap(pix)
    lay.addWidget(icon_lbl)

    title_lbl = QLabel(title)
    title_lbl.setObjectName("cardTitle")
    _f = title_lbl.font(); _f.setPixelSize(15); _f.setBold(True); title_lbl.setFont(_f)
    title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_lbl.setWordWrap(True)
    lay.addWidget(title_lbl)

    desc_lbl = QLabel(desc)
    desc_lbl.setObjectName("cardDesc")
    desc_lbl.setWordWrap(True)
    desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    _f2 = desc_lbl.font(); _f2.setPixelSize(10); desc_lbl.setFont(_f2)
    _p = desc_lbl.palette()
    _p.setColor(QPalette.ColorRole.WindowText, QApplication.palette().placeholderText().color())
    desc_lbl.setPalette(_p)
    lay.addWidget(desc_lbl)

    return btn


def set_card_text(btn: QPushButton, title: str, desc: str):
    """Actualiza el texto de una tarjeta creada con make_card() sin reconstruirla."""
    for child in btn.findChildren(QLabel):
        if child.objectName() == "cardTitle":
            child.setText(title)
        elif child.objectName() == "cardDesc":
            child.setText(desc)


# =============================================================================
# Selector de aplicación para las tarjetas de "Herramientas"
# =============================================================================

class ToolPickerDialog(QDialog):
    """Miniventana que se muestra al pulsar una tarjeta de herramienta cuando
    hay más de una aplicación disponible para esa acción. Las opciones
    recomendadas (yel-soft / kcontrols) siempre aparecen primero porque
    `available` ya llega ordenado así desde get_available_commands()."""

    def __init__(self, title: str, available: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        hint = QLabel(T("tool_picker_hint"))
        hint.setWordWrap(True)
        pal = hint.palette()
        pal.setColor(QPalette.ColorRole.WindowText, QApplication.palette().placeholderText().color())
        hint.setPalette(pal)
        layout.addWidget(hint)

        from core import _binary_id
        for cmd in available:
            binary = _binary_id(cmd)
            btn = QPushButton(display_name_for(binary))
            btn.setMinimumHeight(36)
            icon = icon_for(binary)
            if not icon.isNull():
                btn.setIcon(icon)
                btn.setIconSize(QSize(20, 20))
            btn.clicked.connect(lambda checked=False, c=cmd: self._launch_and_close(c))
            layout.addWidget(btn)

        cancel_btn = QPushButton(T("tool_picker_cancel"))
        cancel_btn.clicked.connect(self.reject)
        layout.addSpacing(4)
        layout.addWidget(cancel_btn)

    def _launch_and_close(self, cmd):
        launch_app(cmd)
        self.accept()


# =============================================================================
# Nueva página de Inicio — botones de color, logo e imágenes de personajes
# =============================================================================

def home_button_colors(color_key: str) -> tuple[QColor, QColor]:
    """Devuelve (color_fondo, color_frente) para un botón de la página de
    Inicio: el color de frente (icono/texto) se elige automáticamente
    según lo claro/oscuro que sea el fondo, para mantener el contraste."""
    bg_hex = HOME_COLORS.get(color_key, HOME_COLORS["navy"])
    bg = QColor(bg_hex)
    fg = QColor(HOME_FG_DARK if color_key in HOME_LIGHT_BACKGROUNDS else HOME_FG_LIGHT)
    return bg, fg


def _display_dpr() -> float:
    """Devuelve el devicePixelRatio de la pantalla principal, o 1.0 si no
    hay ninguna disponible todavía (p. ej. durante los tests)."""
    screen = QApplication.primaryScreen()
    return screen.devicePixelRatio() if screen else 1.0


def render_svg_pixmap(svg_path: str, size: int, dpr: float | None = None) -> QPixmap:
    """Renderiza un SVG vectorialmente al tamaño físico de destino (tamaño
    lógico x devicePixelRatio) usando QSvgRenderer.

    Cargar un SVG con ``QPixmap(svg_path)`` lo rasteriza una sola vez a su
    tamaño intrínseco (normalmente pequeño, p. ej. 24x24, el viewBox del
    archivo) y cualquier reescalado posterior amplía ese resultado ya
    pixelado, dando iconos borrosos. Renderizando directamente al tamaño
    final -y a la resolución física de la pantalla en HiDPI- el icono
    sale nítido a cualquier tamaño."""
    if not svg_path or not os.path.isfile(svg_path):
        return QPixmap()
    renderer = QSvgRenderer(svg_path)
    if not renderer.isValid():
        return QPixmap()
    dpr = dpr if dpr is not None else _display_dpr()
    side = max(1, round(size * dpr))
    pixmap = QPixmap(side, side)
    pixmap.setDevicePixelRatio(dpr)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap


def tinted_icon(svg_path: str, color: QColor, size: int = 22) -> QIcon:
    """Carga un SVG monocromo (dibujado en negro) y lo retiñe del color
    indicado, para que un mismo icono simbólico sirva sobre cualquiera de
    los cinco colores de la paleta de la página de Inicio."""
    if not svg_path or not os.path.isfile(svg_path):
        return QIcon()
    src = render_svg_pixmap(svg_path, size)
    if src.isNull():
        return QIcon()
    tinted = QPixmap(src.size())
    tinted.setDevicePixelRatio(src.devicePixelRatio())
    tinted.fill(Qt.GlobalColor.transparent)
    painter = QPainter(tinted)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.drawPixmap(0, 0, src)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), color)
    painter.end()
    return QIcon(tinted)


class HomeActionButton(QPushButton):
    """Botón de acción de color plano con icono simbólico + etiqueta,
    usado en las columnas izquierda/derecha de la nueva página de Inicio.
    El color no depende del tema del sistema (paleta fija de la marca)."""

    def __init__(self, text: str, svg_icon_path: str, color_key: str, parent=None):
        super().__init__(text, parent)
        self._bg, self._fg = home_button_colors(color_key)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(56)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        icon = tinted_icon(svg_icon_path, self._fg, 22)
        if not icon.isNull():
            self.setIcon(icon)
            self.setIconSize(QSize(22, 22))

        f = self.font()
        f.setPixelSize(13)
        f.setBold(True)
        self.setFont(f)

        pal = self.palette()
        pal.setColor(QPalette.ColorRole.ButtonText, self._fg)
        self.setPalette(pal)

        self._hover = False
        # Animación suave del realce al pasar/quitar el ratón (en vez del
        # cambio instantáneo de color anterior).
        self._hover_progress = 0.0
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(150)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.valueChanged.connect(self._on_hover_value)

    def sizeHint(self) -> QSize:
        # Con QSizePolicy.Fixed en vertical, el layout usa sizeHint() tal
        # cual (ignora setMinimumHeight), así que hay que fijar aquí la
        # altura real deseada del botón para que no se comprima.
        hint = super().sizeHint()
        return QSize(max(hint.width(), 160), 56)

    def _on_hover_value(self, value):
        self._hover_progress = value
        self.update()

    def _animate_hover(self, target: float):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def enterEvent(self, event):
        self._hover = True
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._animate_hover(0.0)
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)

        color = QColor(self._bg)
        if self._hover_progress > 0.0:
            lighter = QColor(self._bg).lighter(112)
            color = _lerp_color(color, lighter, self._hover_progress)
        if not self.isEnabled():
            color.setAlpha(120)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(r, 12, 12)
        painter.end()
        super().paintEvent(event)


class LogoBox(QLabel):
    """Muestra el logo/alfalogo de la distro siempre en la misma caja
    estándar (theme.HOME_LOGO_BOX), centrado y manteniendo proporción,
    sin importar la resolución real del archivo de origen."""

    def __init__(self, image_path: str, box_size: tuple[int, int], parent=None):
        super().__init__(parent)
        w, h = box_size
        self.setFixedSize(w, h)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if image_path and os.path.isfile(image_path):
            pix = QPixmap(image_path)
            if not pix.isNull():
                scaled = pix.scaled(
                    w, h, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
                self.setPixmap(scaled)


class CharacterCarousel(QWidget):
    """Espacio reservado para las ilustraciones de personajes de la
    distro: todas comparten la misma relación de aspecto estándar
    (theme.HOME_CHARACTER_SIZE, 1:1.46) pero el widget se adapta al
    espacio disponible en el layout en vez de imponer un tamaño fijo en
    píxeles, y van rotando automáticamente entre las composiciones por
    parejas disponibles."""

    def __init__(self, image_paths: list[str], size=HOME_CHARACTER_SIZE, parent=None):
        super().__init__(parent)
        self._paths = [p for p in image_paths if os.path.isfile(p)]
        base_w, base_h = size if isinstance(size, (tuple, list)) else (size, size)
        self._base_w, self._base_h = base_w, base_h
        self._ratio = base_h / base_w if base_w else 1.0
        self._index = 0
        self._scale = 1.0

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        min_w = max(90, base_w // 2)
        self.setMinimumSize(min_w, round(min_w * self._ratio))
        self.setMaximumSize(base_w, base_h)

        self._pixmap: QPixmap | None = None
        self._old_pixmap: QPixmap | None = None
        self._fade_progress = 1.0
        self._fade_anim = QVariantAnimation(self)
        self._fade_anim.setDuration(500)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_anim.valueChanged.connect(self._on_fade_value)
        self._load_current()

        if len(self._paths) > 1:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._next)
            self._timer.start(4000)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return round(width * self._ratio)

    def set_scale(self, factor: float):
        """Reescala el tamaño máximo/mínimo del carrusel (p. ej. al
        maximizar la ventana), manteniendo la proporción 1:1.46."""
        factor = max(0.5, factor)
        if abs(factor - self._scale) < 0.001:
            return
        self._scale = factor
        max_w = round(self._base_w * factor)
        max_h = round(self._base_h * factor)
        min_w = max(90, max_w // 2)
        self.setMinimumSize(min_w, round(min_w * self._ratio))
        self.setMaximumSize(max_w, max_h)
        self.updateGeometry()

    def _load_current(self):
        if not self._paths:
            self._pixmap = None
            return
        pix = QPixmap(self._paths[self._index])
        self._pixmap = None if pix.isNull() else pix
        self.update()

    def _rounded(self, pix: QPixmap, radius: int = 20) -> QPixmap:
        # pix puede venir con devicePixelRatio > 1 (ver paintEvent): hay
        # que propagarlo al pixmap redondeado para no perder nitidez ni
        # introducir dientes de sierra al reescalar en pantallas HiDPI.
        dpr = pix.devicePixelRatio() or 1.0
        rounded = QPixmap(pix.size())
        rounded.setDevicePixelRatio(dpr)
        rounded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = pix.width() / dpr
        h = pix.height() / dpr
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pix)
        painter.end()
        return rounded

    def _on_fade_value(self, value):
        self._fade_progress = value
        self.update()

    def _scaled_rounded(self, pixmap: QPixmap, dpr: float) -> QPixmap:
        # Escala en resolución física (tamaño lógico * devicePixelRatio)
        # en vez de en píxeles lógicos: si no, en pantallas HiDPI el
        # sistema reescala de nuevo el resultado ya rasterizado y
        # aparecen los "dientes de sierra" en los bordes del personaje.
        target = self.size() * dpr
        scaled = pixmap.scaled(
            target, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        scaled.setDevicePixelRatio(dpr)
        return self._rounded(scaled)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        dpr = self.devicePixelRatioF() or 1.0

        # Imagen saliente: se desvanece mientras la nueva aparece encima.
        if self._old_pixmap and self._fade_progress < 1.0:
            old_rounded = self._scaled_rounded(self._old_pixmap, dpr)
            x = (self.width() - old_rounded.width() / dpr) / 2
            y = (self.height() - old_rounded.height() / dpr) / 2
            painter.setOpacity(1.0 - self._fade_progress)
            painter.drawPixmap(QPointF(x, y), old_rounded)

        if self._pixmap:
            rounded = self._scaled_rounded(self._pixmap, dpr)
            x = (self.width() - rounded.width() / dpr) / 2
            y = (self.height() - rounded.height() / dpr) / 2
            painter.setOpacity(self._fade_progress if self._old_pixmap else 1.0)
            painter.drawPixmap(QPointF(x, y), rounded)

        painter.end()

    def _next(self):
        self._old_pixmap = self._pixmap
        self._index = (self._index + 1) % len(self._paths)
        self._load_current()
        self._fade_progress = 0.0
        self._fade_anim.stop()
        self._fade_anim.start()


def _square_pixmap(pixmap: QPixmap, side_len: int, radius: int) -> QPixmap:
    """Recorta y escala un QPixmap a un cuadrado perfecto de ``side_len``
    píxeles lógicos con esquinas redondeadas de ``radius``, admite
    pixmaps HiDPI (devicePixelRatio > 1)."""
    dpr = pixmap.devicePixelRatio() or 1.0
    side = round(side_len * dpr)
    scaled = pixmap.scaled(
        side, side, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation)
    # Recorta el centro si el resultado no es cuadrado tras respetar proporción
    if scaled.width() != side or scaled.height() != side:
        x = max(0, (scaled.width() - side) // 2)
        y = max(0, (scaled.height() - side) // 2)
        scaled = scaled.copy(x, y, side, side)

    out = QPixmap(side, side)
    out.setDevicePixelRatio(dpr)
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, side_len, side_len), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(QRectF(0, 0, side_len, side_len), scaled, QRectF(scaled.rect()))
    painter.end()
    return out


class SquareImageLabel(QLabel):
    """Imagen cuadrada (1:1) con esquinas ligeramente redondeadas, usada
    como ilustración central del tour de bienvenida (sin borde propio,
    para que solo se vea la ilustración)."""

    def __init__(self, side_len: int = 220, radius: int = 24, parent=None):
        super().__init__(parent)
        self._side_len = side_len
        self._radius = radius
        self.setFixedSize(side_len, side_len)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_image_path(self, path: str | None):
        if path and os.path.isfile(path):
            src = QPixmap(path)
            if not src.isNull():
                self.setPixmap(_square_pixmap(src, self._side_len, self._radius))
                return
        self.setPixmap(QPixmap())


class CircleIconButton(QPushButton):
    """Botón circular con una flecha dibujada (sin depender de iconos
    de tema), usado para navegar Atrás/Siguiente en el tour de
    bienvenida. Colores siempre tomados de la paleta activa, así que
    se adapta solo a claro/oscuro."""

    def __init__(self, direction: str = "right", diameter: int = 56, parent=None):
        super().__init__(parent)
        self._direction = direction
        self._diameter = diameter
        self.setFixedSize(diameter, diameter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self._hover = False
        self._highlighted = False

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def set_highlighted(self, value: bool):
        """Marca el botón como la acción principal (p. ej. Siguiente en la
        última diapositiva del tour), pintándolo con el color de resalte
        de la paleta activa en vez del color de botón neutro."""
        if self._highlighted != value:
            self._highlighted = value
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)

        if not self.isEnabled():
            painter.setBrush(self.palette().window().color())
        elif self._highlighted:
            hl = self.palette().highlight().color()
            painter.setBrush(hl.lighter(112) if self._hover else hl)
        elif self._hover:
            painter.setBrush(self.palette().midlight())
        else:
            painter.setBrush(self.palette().button().color())

        if self._highlighted and self.isEnabled():
            pen = QPen(self.palette().highlight().color().darker(120))
        else:
            pen = QPen(self.palette().mid().color())
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawEllipse(r)

        if self._highlighted and self.isEnabled():
            fg = self.palette().highlightedText().color()
        else:
            fg = self.palette().buttonText().color()
        if not self.isEnabled():
            fg.setAlpha(110)
        pen = QPen(fg)
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        cx, cy = r.center().x(), r.center().y()
        arm = self._diameter * 0.16
        if self._direction == "left":
            tip = QPointF(cx - arm * 0.7, cy)
            top = QPointF(cx + arm * 0.7, cy - arm)
            bot = QPointF(cx + arm * 0.7, cy + arm)
        else:
            tip = QPointF(cx + arm * 0.7, cy)
            top = QPointF(cx - arm * 0.7, cy - arm)
            bot = QPointF(cx - arm * 0.7, cy + arm)
        painter.drawLine(top, tip)
        painter.drawLine(tip, bot)

        painter.end()


def open_tool(title: str, candidates: list, parent=None):
    """Punto de entrada usado por las tarjetas de herramientas: comprueba qué
    apps están instaladas en ese momento. Si hay más de una detectada, deja
    elegir con una miniventana (con las recomendadas primero); si solo hay
    una, la abre directamente; si ninguna está instalada, prioriza igual la
    primera de la lista configurada."""
    available = get_available_commands(candidates)
    if len(available) <= 1:
        launch_first_available(candidates)
        return
    dlg = ToolPickerDialog(title, available, parent)
    dlg.exec()
