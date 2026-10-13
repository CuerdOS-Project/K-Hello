#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main_window.py — Ventana principal de K-Hello (nuevo diseño con sidebar).

Mismo concepto que la versión anterior (4 secciones: Inicio, Herramientas,
Nuevo usuario, Soporte + botón de instalar + idioma + acerca de), pero con
una barra de navegación lateral en vez de pestañas superiores, y todo el
estilo centralizado en theme.py en lugar de QSS disperso por el código.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QSettings, QEvent, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QPushButton, QCheckBox, QLabel, QFrame, QGraphicsOpacityEffect,
)

from core import (
    APP_ID, PREFS_FILE,
    find_asset, detect_live_mode,
    autostart_is_enabled, autostart_enable, autostart_disable,
)
from translations import T, set_language
from theme import INSTALL_ACCENT
from sidebar import Sidebar
from pages import (
    build_home_page, build_social_page, build_tools_page,
    build_newuser_page, build_support_page,
)
from about import AboutDialog
from widgets import CharacterCarousel

# Factor de escalado del personaje de la página de Inicio cuando la
# ventana está maximizada (crece junto con el espacio disponible).
_MAXIMIZED_CHARACTER_SCALE = 1.35


def _fade_in(widget: QWidget, duration: int = 220):
    """Aplica una animación de desvanecimiento (opacidad 0 -> 1) a un
    widget recién mostrado, p. ej. al cambiar de pestaña."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _cleanup():
        widget.setGraphicsEffect(None)

    anim.finished.connect(_cleanup)
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    widget._fade_anim = anim  # mantiene viva la referencia hasta que termine

# Orden de las páginas: debe coincidir con sidebar.NAV_SECTIONS
_PAGE_BUILDERS = {
    "social": build_social_page,
    "tools": build_tools_page,
    "newuser": build_newuser_page,
    "support": build_support_page,
}
_PAGE_ORDER = ["home", "social", "tools", "newuser", "support"]


class KHelloWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(825, 610)
        self.resize(900, 610)

        app_icon = QIcon.fromTheme(APP_ID)
        if app_icon.isNull():
            svg_path = find_asset("k-hello.svg") or find_asset("cuerdos.svg")
            if svg_path:
                app_icon = QIcon(svg_path)
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)

        self._setup_ui()
        self.apply_styles()
        self._update_character_scale()

    # ------------------------------------------------------------------
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.sidebar = Sidebar(
            self.go_to_section, self.show_about_dialog, self._apply_language,
        )
        outer.addWidget(self.sidebar)

        _sep = QFrame()
        _sep.setFrameShape(QFrame.Shape.HLine)
        _sep.setFrameShadow(QFrame.Shadow.Sunken)
        outer.addWidget(_sep)

        self.stack = QStackedWidget()
        self._page_widgets: dict[str, QWidget] = {}
        for section_id in _PAGE_ORDER:
            page = self._build_page(section_id)
            self._page_widgets[section_id] = page
            self.stack.addWidget(page)
        outer.addWidget(self.stack, 1)

        outer.addWidget(self.create_bottom_bar())

        self.setWindowTitle("K-Hello")

    def go_to_section(self, section_id: str):
        if section_id in self._page_widgets:
            widget = self._page_widgets[section_id]
            self.stack.setCurrentWidget(widget)
            self.sidebar.set_active_section(section_id)
            _fade_in(widget)

    def _build_page(self, section_id: str) -> QWidget:
        if section_id == "home":
            return build_home_page(self.go_to_section)
        return _PAGE_BUILDERS[section_id]()

    # ------------------------------------------------------------------
    # Menú de ajustes / idioma / acerca de
    # ------------------------------------------------------------------

    def _apply_language(self, code: str):
        set_language(code)
        try:
            settings = QSettings(PREFS_FILE, QSettings.Format.IniFormat)
            settings.setValue("language", code)
            settings.sync()
        except Exception:
            pass
        self.refresh_ui()

    def show_about_dialog(self):
        dlg = AboutDialog(self)
        dlg.exec()

    # ------------------------------------------------------------------
    # Barra inferior: autoarranque, instalar
    # ------------------------------------------------------------------

    def create_bottom_bar(self) -> QWidget:
        bar = QWidget()
        bar.setProperty("bottomBar", True)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 8, 20, 8)

        self.autostart_check = QCheckBox()
        self.autostart_check.setChecked(autostart_is_enabled())
        self.autostart_check.toggled.connect(self.on_autostart_toggled)
        layout.addWidget(self.autostart_check)

        self.autostart_label = QLabel(T("autostart_label"))
        layout.addWidget(self.autostart_label)

        layout.addStretch()

        _, installer_cmd = detect_live_mode()
        self.install_btn = None
        if installer_cmd:
            from core import launch_app
            install_text = T("btn_install")
            self.install_btn = QPushButton(install_text)
            install_icon = QIcon.fromTheme("drive-optical") or QIcon.fromTheme("system-software-install")
            if not install_icon.isNull():
                self.install_btn.setIcon(install_icon)
            self.install_btn.setProperty("installBtn", True)
            self.install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # Mismo verde de acento que la tarjeta de instalar del modo
            # Live, para que la acción de instalar se identifique por su
            # color en cualquiera de las dos ventanas.
            self.install_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {INSTALL_ACCENT['base']};
                    color: {INSTALL_ACCENT['text']};
                    border: 1px solid {INSTALL_ACCENT['border']};
                    border-radius: 6px;
                    padding: 5px 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {INSTALL_ACCENT['hover']};
                }}
                QPushButton:pressed {{
                    background-color: {INSTALL_ACCENT['pressed']};
                }}
                QPushButton:disabled {{
                    background-color: {INSTALL_ACCENT['disabled']};
                    border-color: {INSTALL_ACCENT['disabled']};
                    color: {INSTALL_ACCENT['disabled']};
                }}
            """)
            self.install_btn.clicked.connect(lambda: launch_app(installer_cmd))
            layout.addWidget(self.install_btn)

        self.close_btn = QPushButton(T("btn_close"))
        close_icon = QIcon.fromTheme("window-close")
        if not close_icon.isNull():
            self.close_btn.setIcon(close_icon)
        self.close_btn.setProperty("closeBtn", True)
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)

        return bar

    def on_autostart_toggled(self, checked: bool):
        if checked:
            autostart_enable()
        else:
            autostart_disable()

    # ------------------------------------------------------------------
    def refresh_ui(self):
        """Reconstruye textos y páginas tras un cambio de idioma."""
        self.setWindowTitle("K-Hello")
        self.sidebar.refresh_texts()

        current_id = next(
            (sid for sid, w in self._page_widgets.items() if w is self.stack.currentWidget()),
            "home",
        )

        for section_id in _PAGE_ORDER:
            old_widget = self._page_widgets[section_id]
            new_widget = self._build_page(section_id)
            idx = self.stack.indexOf(old_widget)
            self.stack.insertWidget(idx, new_widget)
            self.stack.removeWidget(old_widget)
            old_widget.deleteLater()
            self._page_widgets[section_id] = new_widget

        self.go_to_section(current_id)
        self._update_character_scale()

        self.autostart_label.setText(T("autostart_label"))
        if self.install_btn:
            self.install_btn.setText(T("btn_install"))
        self.close_btn.setText(T("btn_close"))

    def apply_styles(self):
        pass  # Estilos nativos del sistema, sin QSS

    # ------------------------------------------------------------------
    # Escalado del personaje al maximizar la ventana
    # ------------------------------------------------------------------

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._update_character_scale()

    def _update_character_scale(self):
        home_page = self._page_widgets.get("home")
        if not home_page:
            return
        carousel = home_page.findChild(CharacterCarousel)
        if carousel:
            carousel.set_scale(
                _MAXIMIZED_CHARACTER_SCALE if self.isMaximized() else 1.0
            )
