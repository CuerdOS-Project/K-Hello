#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sidebar.py — Barra de navegación superior de K-Hello.

Pestañas de sección (INICIO/REDES/HERRAMIENTAS/NUEVO USUARIO/APOYAR) en
una fila horizontal arriba de la ventana, con el botón de idioma (abre el
diálogo completo) y el botón "Acerca de" a la derecha, ambos solo-icono.
La clase se sigue llamando `Sidebar` por compatibilidad con el resto de
módulos (main_window.py), aunque ahora vive en la parte superior en vez
de en un lateral.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QButtonGroup,
    QSizePolicy, QFrame, QToolButton, QComboBox,
)

from core import find_asset
from translations import (
    T, AVAILABLE_LANGUAGES, get_language_pref, detect_system_locale,
)
from widgets import NavButton

# Secciones de navegación: (id, archivo_svg, clave_traducción)
# Orden acorde al diagrama de referencia: INICIO, REDES, HERRAMIENTAS,
# NUEVO USUARIO, APOYAR. Los iconos son símbolos propios en assets/ para
# no depender del tema de iconos del sistema.
NAV_SECTIONS = [
    ("home",    "nav-home.svg",    "tab_home"),
    ("social",  "nav-social.svg",  "tab_social"),
    ("tools",   "nav-tools.svg",   "tab_tools"),
    ("newuser", "nav-newuser.svg", "tab_newuser"),
    ("support", "nav-support.svg", "tab_support"),
]


class Sidebar(QWidget):
    """Barra superior con pestañas de navegación + idioma + acerca de."""

    def __init__(self, on_section_changed, on_settings, on_language_changed=None, parent=None):
        super().__init__(parent)
        self.on_section_changed = on_section_changed
        self.on_settings = on_settings
        self.on_language_changed = on_language_changed

        self.setProperty("sidebar", True)
        self.setFixedHeight(56)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(14, 8, 14, 8)
        root.setSpacing(10)

        # Pestañas de navegación: icono siempre, texto solo si está activa.
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        self._nav_buttons: dict[str, NavButton] = {}

        for section_id, icon_file, key in NAV_SECTIONS:
            btn = NavButton(T(key), find_asset(icon_file))
            btn.clicked.connect(lambda checked, sid=section_id: self._on_nav_clicked(sid))
            self._nav_group.addButton(btn)
            self._nav_buttons[section_id] = btn
            root.addWidget(btn)

        root.addStretch(1)

        # Selector de idioma: combo desplegable directo en la barra (en vez
        # de un botón que abre un diálogo aparte). "Auto" siempre está
        # presente como primera opción, junto al nombre del idioma que
        # detecta del sistema.
        self.lang_combo = QComboBox()
        self.lang_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_combo.setToolTip(T("lang_dialog_title"))
        self.lang_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._populate_lang_combo()
        self.lang_combo.currentIndexChanged.connect(self._on_lang_combo_changed)
        root.addWidget(self.lang_combo)

        # Línea divisora vertical
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(divider)

        # Ajustes / Acerca de (solo icono, sin texto)
        self.settings_btn = QToolButton()
        settings_icon = QIcon.fromTheme("help-about")
        if not settings_icon.isNull():
            self.settings_btn.setIcon(settings_icon)
            self.settings_btn.setIconSize(QSize(18, 18))
        else:
            self.settings_btn.setText(T("menu_about"))
        self.settings_btn.setToolTip(T("menu_about"))
        self.settings_btn.setProperty("sideIconBtn", True)
        self.settings_btn.setAutoRaise(True)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self.on_settings)
        root.addWidget(self.settings_btn)

        # Sección activa por defecto
        self.set_active_section(NAV_SECTIONS[0][0])

    # ------------------------------------------------------------------
    def _on_nav_clicked(self, section_id: str):
        self.on_section_changed(section_id)

    def set_active_section(self, section_id: str):
        btn = self._nav_buttons.get(section_id)
        if btn:
            btn.setChecked(True)

    def refresh_texts(self):
        """Actualiza textos traducibles sin reconstruir la barra."""
        for section_id, icon_file, key in NAV_SECTIONS:
            btn = self._nav_buttons[section_id]
            btn._label_text = T(key)
            btn._sync_state(btn.isChecked())
        self.settings_btn.setToolTip(T("menu_about"))
        self.lang_combo.setToolTip(T("lang_dialog_title"))
        self._populate_lang_combo()

    # ------------------------------------------------------------------
    # Selector de idioma (combo)
    # ------------------------------------------------------------------

    def _populate_lang_combo(self):
        """(Re)llena el combo con todos los idiomas disponibles. "Auto"
        siempre es la primera entrada, mostrando entre paréntesis el
        idioma que se detectaría del sistema."""
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()

        selected_index = 0
        current_pref = get_language_pref()
        detected = detect_system_locale()
        detected_name = AVAILABLE_LANGUAGES.get(detected, detected.upper())
        for i, (code, name) in enumerate(AVAILABLE_LANGUAGES.items()):
            label = f"{T('lang_auto')} ({detected_name})" if code == "auto" else name
            self.lang_combo.addItem(label, code)
            if code == current_pref:
                selected_index = i

        self.lang_combo.setCurrentIndex(selected_index)
        self.lang_combo.blockSignals(False)

    def _on_lang_combo_changed(self, index: int):
        code = self.lang_combo.itemData(index)
        if code and self.on_language_changed:
            self.on_language_changed(code)
