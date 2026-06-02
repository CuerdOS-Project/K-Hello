#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — Punto de entrada de K-Hello (CuerdOS GNU/Linux)
"""

import sys
import os

# Añadir src/ al path para importar los módulos del proyecto
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from PySide6.QtCore import QSettings
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from translations import set_language
from core import (
    APP_ID, APP_NAME, APP_VERSION, PREFS_FILE,
    find_asset, detect_live_mode, parse_data_kn_live,
    is_first_run,
)
from qwindow import KHelloWindow, LiveModeWindow, FirstUseWindow


# =============================================================================
# Aplicación principal
# =============================================================================

class KHelloApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        # ID de aplicación: usado por Wayland (app_id), XFCE y otros WMs
        # para agrupar ventanas y mostrar el icono correcto en la barra de tareas
        self.setApplicationName(APP_ID)          # "k-hello" → Wayland app_id
        self.setDesktopFileName(APP_ID)          # enlaza con k-hello.desktop
        self.setApplicationDisplayName(APP_NAME)
        self.setApplicationVersion(APP_VERSION)
        self.setOrganizationName("CuerdOS")

        # Icono: primero desde el tema del sistema (usa APP_ID = "k-hello")
        app_icon = QIcon.fromTheme(APP_ID)
        if app_icon.isNull():
            svg_path = find_asset("k-hello.svg") or find_asset("cuerdos.svg")
            if svg_path:
                app_icon = QIcon(svg_path)
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)

        self.main_window_shown = False
        self.settings = QSettings(PREFS_FILE, QSettings.Format.IniFormat)

    def run(self):
        saved_lang = self.settings.value("language", "auto")
        set_language(saved_lang)

        is_live, installer_cmd = detect_live_mode()

        if is_live:
            live_cfg = parse_data_kn_live()
            install_label = live_cfg.get("install_label")

            live_win = LiveModeWindow(
                installer_cmd,
                self.show_main_window,
                install_label
            )
            live_win.finished.connect(self.on_live_finished)
            live_win.show()

        elif is_first_run():
            first_win = FirstUseWindow(self.show_main_window)
            first_win.finished.connect(self.on_first_run_finished)
            first_win.show()

        else:
            self.show_main_window()

        return self.exec()

    def show_main_window(self):
        self.main_window_shown = True
        self.window = KHelloWindow()
        self.window.show()

    def on_live_finished(self):
        if not self.main_window_shown:
            self.quit()

    def on_first_run_finished(self):
        if not self.main_window_shown:
            self.quit()


# =============================================================================
# Punto de entrada
# =============================================================================

if __name__ == "__main__":
    if "--live" in sys.argv:
        _FORCE_LIVE = True
        sys.argv.remove("--live")
        print("[K-Hello] Modo --live activado")

    app = KHelloApp(sys.argv)
    sys.exit(app.run())