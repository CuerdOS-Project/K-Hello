#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core.py — Constantes, utilidades y detección de entorno para K-Hello (CuerdOS GNU/Linux)
"""

import os
import sys
import subprocess
import shutil
import getpass
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QSize, QSettings, QUrl, QEasingCurve, QPropertyAnimation, QPointF
from PySide6.QtGui import QIcon, QPixmap, QFont, QDesktopServices, QPainter, QColor, QPalette, QAction, QLinearGradient, QPolygonF
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QScrollArea, QFrame, QDialog,
    QRadioButton, QButtonGroup, QGridLayout,
    QMessageBox, QCheckBox, QSizePolicy,
    QComboBox, QToolButton, QMenu, QStyle, QDialogButtonBox,
    QGraphicsOpacityEffect
)

# Importar traducciones
from translations import T, set_language, get_language, get_language_pref, is_auto_mode, detect_system_locale, AVAILABLE_LANGUAGES


# =============================================================================
# Constantes
# =============================================================================

APP_ID = "k-hello"
APP_VERSION = "2.0"
APP_NAME = "K-Hello"
APP_AUTHOR = "CuerdOS"
APP_WEBSITE = "https://cuerdos.github.io"
APP_WIKI = "https://wiki.cuerdos.org"
APP_CHANGELOG = "https://cuerdos.github.io/changelogs.html"
APP_NEWS = "https://cuerdos.github.io"
APP_DEBIAN_WIKI = "https://wiki.debian.org"
APP_KOFI = "https://ko-fi.com/cuerdos"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_KN_FILE = os.path.join(BASE_DIR, "data.kn")

# Preferencias
PREFS_DIR = os.path.expanduser("~/.config/k-hello")
PREFS_FILE = os.path.join(PREFS_DIR, "prefs")
FIRST_RUN_FLAG = os.path.join(PREFS_DIR, "first_run_done")
AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
AUTOSTART_FILE = os.path.join(AUTOSTART_DIR, "k-hello.desktop")

# Instaladores integrados
_BUILTIN_INSTALLERS = [
    ("calamares-install-cuerdos", ["calamares-install-cuerdos"]),
    ("kron", ["kron"]),
]

_LIVE_PACKAGES = ["live-boot", "live-config", "live-tools", "live-config-systemd"]
_LIVE_USERNAMES = ["live", "user", "cuerdos"]

# Redes sociales — icon_file es el nombre del SVG en assets/
SOCIAL_LINKS = [
    ("social_bluesky",   "bluesky.svg",   "https://bsky.app/profile/cuerdoslinux.bsky.social"),
    ("social_github",    "github.svg",    "https://github.com/CuerdOS"),
    ("social_telegram",  "telegram.svg",  "https://t.me/+GibSWjFc89Q2ODU8"),
    ("social_facebook",  "facebook.svg",  "https://www.facebook.com/share/1GSYsPb5gQ/"),
    ("social_instagram", "ig.svg",        "https://www.instagram.com/cuerdos_gnulinux"),
    ("social_matrix",    "matrix.svg",    "https://matrix.to/#/%23cuerdos:matrix.org"),
    ("social_mastodon",  "mastodon.svg",  "https://mastodon.social/@cuerdos"),
]

# Herramientas por defecto con alternativas por entorno (KDE/GNOME/otros)
_DEFAULT_TOOLS = [
    ("tool_update",   "tool_update",   "system-software-update",  [
        ["cuerdtoken"],
        ["plasma-discover", "--mode", "Update"],
        ["gnome-software", "--mode", "updates"],
        ["pkcon", "update"],
    ]),
    ("tool_info",     "tool_info",     "dialog-information",      [
        ["eclair"],
        ["kinfocenter"],
        ["hardinfo"],
    ]),
    ("tool_store",    "tool_store",    "system-software-install", [
        ["yel-store"],
        ["plasma-discover"],
        ["gnome-software"],
        ["synaptic"],
    ]),
    ("tool_browser",  "tool_browser",  "web-browser",             [
        ["xdg-open", "https://cuerdos.github.io"],
    ]),
    ("tool_recovery", "tool_recovery", "drive-harddisk-system",   [
        ["timeshift-launcher"],
        ["timeshift"],
    ]),
]


def _resolve_cmd(candidates: list) -> list | None:
    """Devuelve el primer comando cuyo binario esté disponible."""
    for cmd in candidates:
        if shutil.which(cmd[0]):
            return cmd
    return candidates[0] if candidates else None


def parse_data_kn_tools() -> list:
    """Lee la sección [tools] de data.kn."""
    result = []
    if not os.path.isfile(DATA_KN_FILE):
        return result
    try:
        with open(DATA_KN_FILE, "r", encoding="utf-8") as f:
            in_tools = False
            for line in f:
                line = line.strip()
                if line.startswith("[") and line.endswith("]"):
                    in_tools = line[1:-1].lower() == "tools"
                    continue
                if in_tools and "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    key, val = key.strip(), val.strip()
                    parts = [p.strip() for p in val.split("|")]
                    icon = parts[0] if parts else "application-x-executable"
                    cmds = [[c] for c in parts[1:]] if len(parts) > 1 else []
                    if cmds:
                        result.append((key, key + "_desc", icon, cmds))
    except OSError:
        pass
    return result


def get_tools() -> list:
    """Devuelve la lista de herramientas activa."""
    kn_tools = parse_data_kn_tools()
    source = kn_tools if kn_tools else _DEFAULT_TOOLS
    result = []
    for label_key, desc_key, icon_name, candidates in source:
        cmd = _resolve_cmd(candidates)
        if cmd:
            result.append((label_key, desc_key, icon_name, cmd))
    return result


# =============================================================================
# Utilidades
# =============================================================================

def get_system_icon(icon_name: str) -> QIcon:
    icon = QIcon.fromTheme(icon_name)
    if icon.isNull():
        return QIcon()
    return icon


def find_asset(filename: str) -> str:
    candidates = [
        os.path.join(ASSETS_DIR, filename),
        os.path.join(BASE_DIR, filename),
        os.path.join("/usr/share/k-hello", filename),
        os.path.join("/usr/share/pixmaps", filename),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return ""


def open_url(url: str):
    QDesktopServices.openUrl(QUrl(url))


def launch_app(cmd: list[str]):
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        QMessageBox.critical(None, "Error", f"No se encontró: {cmd[0]}")


def autostart_is_enabled() -> bool:
    return os.path.isfile(AUTOSTART_FILE)


def autostart_enable():
    os.makedirs(AUTOSTART_DIR, exist_ok=True)
    content = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Exec=k-hello
Icon=k-hello
Comment=CuerdOS Welcome App
Categories=System;
X-GNOME-Autostart-enabled=true
"""
    with open(AUTOSTART_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def autostart_disable():
    if os.path.isfile(AUTOSTART_FILE):
        os.remove(AUTOSTART_FILE)


def is_first_run() -> bool:
    return not os.path.isfile(FIRST_RUN_FLAG)


def mark_first_run_done():
    os.makedirs(PREFS_DIR, exist_ok=True)
    with open(FIRST_RUN_FLAG, "w") as f:
        f.write("done\n")


# =============================================================================
# Helper para opacidad
# =============================================================================

def set_widget_opacity(widget, opacity: float):
    effect = QGraphicsOpacityEffect()
    effect.setOpacity(opacity)
    widget.setGraphicsEffect(effect)


# =============================================================================
# Detección de modo live
# =============================================================================

_FORCE_LIVE = False


def check_package_installed(pkg: str) -> bool:
    try:
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${Status}", pkg],
            capture_output=True, text=True, timeout=2
        )
        return "install ok installed" in result.stdout
    except Exception:
        return False


def find_builtin_installer() -> list[str] | None:
    for binary, cmd in _BUILTIN_INSTALLERS:
        if shutil.which(binary):
            return cmd
    return None


def parse_data_kn_live() -> dict:
    result = {"installer_cmd": None, "install_label": None}
    if not os.path.isfile(DATA_KN_FILE):
        return result

    try:
        with open(DATA_KN_FILE, "r", encoding="utf-8") as f:
            in_live = False
            for line in f:
                line = line.strip()
                if line.startswith("[") and line.endswith("]"):
                    in_live = line[1:-1].lower() == "live"
                    continue
                if in_live and "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    key, val = key.strip(), val.strip()
                    if key == "installer":
                        result["installer_cmd"] = [val]
                    elif key == "installer_args":
                        if result["installer_cmd"]:
                            result["installer_cmd"].extend(val.split())
                    elif key == "install_label":
                        result["install_label"] = val
    except OSError:
        pass
    return result


def detect_live_mode() -> tuple[bool, list[str] | None]:
    global _FORCE_LIVE

    if _FORCE_LIVE or "--live" in sys.argv:
        live_cfg = parse_data_kn_live()
        installer_cmd = live_cfg.get("installer_cmd")
        if installer_cmd is None:
            installer_cmd = find_builtin_installer()
        return True, installer_cmd

    for pkg in _LIVE_PACKAGES:
        if check_package_installed(pkg):
            return True, find_builtin_installer()

    installer = find_builtin_installer()
    if installer:
        return True, installer

    try:
        if getpass.getuser().lower() in _LIVE_USERNAMES:
            return True, find_builtin_installer()
    except Exception:
        pass

    return False, None
