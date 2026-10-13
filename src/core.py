#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core.py — Constantes, utilidades y detección de entorno para K-Hello
CuerdOS Welcome Application
"""

import os
import sys
import subprocess
import shutil

from PySide6.QtCore import QUrl
from PySide6.QtGui import QIcon, QDesktopServices, QFont, QPalette
from PySide6.QtWidgets import QMessageBox, QGraphicsOpacityEffect, QApplication

from translations import T, set_language, get_language, get_language_pref, is_auto_mode, detect_system_locale, AVAILABLE_LANGUAGES


# =============================================================================
# Constantes
# =============================================================================

APP_ID      = "k-hello"
APP_VERSION = "3.0"
APP_NAME    = "K-Hello"
APP_AUTHOR  = "CuerdOS"
APP_WEBSITE   = "https://cuerdos.es/"
APP_WIKI      = "https://cuerdos.es/wiki/"
APP_CHANGELOG = "https://cuerdos.github.io/changelogs.html"
APP_NEWS      = "https://t.me/CuerdOS_Noticias"
APP_KOFI      = "https://ko-fi.com/cuerdos"

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_KN_FILE = os.path.join(BASE_DIR, "data.kn")

# Preferencias
PREFS_DIR      = os.path.expanduser("~/.config/k-hello")
PREFS_FILE     = os.path.join(PREFS_DIR, "prefs")
FIRST_RUN_FLAG = os.path.join(PREFS_DIR, "first_run_done")
AUTOSTART_DIR  = os.path.expanduser("~/.config/autostart")
AUTOSTART_FILE = os.path.join(AUTOSTART_DIR, "k-hello.desktop")
AUTOSTART_SYSTEM_DIR = "/etc/xdg/autostart"

# Instaladores integrados — únicos disparadores válidos del modo live
_BUILTIN_INSTALLERS = [
    ("kron-installer", ["kron-installer"]),
    ("kron",           ["kron"]),
]

# Redes sociales — icon_file es el nombre del SVG en assets/
SOCIAL_LINKS = [
    ("social_bluesky",   "bluesky.svg",   "https://bsky.app/profile/cuerdoslinux.bsky.social"),
    ("social_github",    "github.svg",    "https://github.com/CuerdOS"),
    ("social_reddit",    "reddit.svg",    "https://www.reddit.com/r/CuerdOS/"),
    ("social_telegram",  "telegram.svg",  "https://t.me/+GibSWjFc89Q2ODU8"),
    ("social_facebook",  "facebook.svg",  "https://www.facebook.com/share/1GSYsPb5gQ/"),
    ("social_instagram", "ig.svg",        "https://www.instagram.com/cuerdos_gnulinux"),
    ("social_matrix",    "matrix.svg",    "https://matrix.to/#/%23cuerdos:matrix.org"),
    ("social_mastodon",  "mastodon.svg",  "https://mastodon.social/@cuerdos"),
]

# Herramientas por defecto con alternativas por entorno (KDE / GNOME / otros)
# Los iconos son nombres genéricos del tema del sistema (freedesktop icon
# naming spec), para que se vean bien en cualquier tema de iconos instalado.
_DEFAULT_TOOLS = [
    ("tool_update",   "tool_update",   "system-software-update",  [
        ["yel-soft", "--updates"],
        ["gnome-software", "--mode", "updates"],
        ["plasma-discover", "--mode", "Update"],
    ]),
    ("tool_info",     "tool_info",     "dialog-information",      [
        ["kcontrols", "--infocenter"],
        ["kinfocenter"],
        ["hardinfo"],
    ]),
    ("tool_store",    "tool_store",    "system-software-install", [
        ["yel-soft"],
        ["gnome-software"],
        ["plasma-discover"],
        ["synaptic"],
    ]),
    ("tool_browser",  "tool_browser",  "applications-internet",   [
        ["xdg-open", "https://cuerdos.github.io"],
    ]),
    ("tool_recovery", "tool_recovery", "drive-harddisk-system",   [
        ["pkexec", "timeshift-gtk"],
        ["timeshift-launcher"],
        ["timeshift"],
    ]),
    ("tool_control",  "tool_control_desc", "preferences-system",  [
        ["kcontrols"],
        ["xfce4-settings-manager"],
        ["gnome-control-center"],
        ["systemsettings"],
    ]),
]

# Herramientas que deben ocultarse por completo en ciertos entornos, porque
# no tiene sentido ofrecer un panel de control de escritorio (KDE/GNOME) en
# un compositor Wayland minimalista como Sway.
_TOOLS_HIDDEN_ON_SWAY = {"tool_control"}


# =============================================================================
# Herramientas
# =============================================================================

def is_sway_session() -> bool:
    """Detecta si la sesión actual corre bajo Sway (u otro compositor
    wlroots minimalista sin panel de control de escritorio propio)."""
    if os.environ.get("SWAYSOCK"):
        return True
    desktop = (os.environ.get("XDG_CURRENT_DESKTOP", "") + " " +
               os.environ.get("XDG_SESSION_DESKTOP", "") + " " +
               os.environ.get("DESKTOP_SESSION", "")).lower()
    return "sway" in desktop


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
                    icon  = parts[0] if parts else "application-x-executable"
                    cmds  = [[c] for c in parts[1:]] if len(parts) > 1 else []
                    if cmds:
                        result.append((key, key + "_desc", icon, cmds))
    except OSError:
        pass
    return result


def get_tools() -> list:
    """Devuelve la lista de herramientas activa, con TODOS sus candidatos
    (no un único comando ya resuelto), para que la tarjeta pueda mostrar un
    selector si hay más de una aplicación instalada. El panel de control
    (tool_control) se omite por completo en Sway, ya que ninguna de sus
    alternativas (KControls, systemsettings, GNOME Control Center) tiene
    sentido ahí."""
    kn_tools = parse_data_kn_tools()
    source   = kn_tools if kn_tools else _DEFAULT_TOOLS
    sway     = is_sway_session()
    result   = []
    for label_key, desc_key, icon_name, candidates in source:
        if sway and label_key in _TOOLS_HIDDEN_ON_SWAY:
            continue
        if candidates:
            result.append((label_key, desc_key, icon_name, candidates))
    return result


# Binarios que siempre deben ir primero en el selector cuando están
# instalados, por ser las apps "nativas" recomendadas de CuerdOS/Void.
_RECOMMENDED_BINARIES = {"yel-soft", "kcontrols"}

# Nombres amigables para mostrar en el selector de aplicaciones.
_TOOL_DISPLAY_NAMES = {
    "yel-soft":                "Yelena Software",
    "kcontrols":               "K-Controls",
    "gnome-software":          "GNOME Software",
    "plasma-discover":         "Discover",
    "synaptic":                "Synaptic",
    "kinfocenter":             "KInfoCenter",
    "hardinfo":                "HardInfo",
    "timeshift-gtk":           "Timeshift",
    "timeshift-launcher":      "Timeshift",
    "timeshift":               "Timeshift",
    "systemsettings":          "Ajustes del sistema (KDE)",
    "gnome-control-center":    "Configuración (GNOME)",
    "xfce4-settings-manager":  "Ajustes (Xfce)",
}

# Icono propio (SVG en assets/) para los binarios que no traen un icono de
# tema fiable o cuyo icono de marca queremos priorizar sobre el genérico
# del sistema.
_TOOL_ICON_ASSETS = {
    "yel-soft": "yel-store.svg",
}


def _binary_id(cmd: list) -> str:
    """Identificador \"real\" de un comando para mostrar nombre/icono: si el
    comando va envuelto en pkexec (p. ej. ['pkexec', 'timeshift-gtk']), el
    binario relevante es el segundo elemento, no 'pkexec'."""
    if not cmd:
        return ""
    if cmd[0] == "pkexec" and len(cmd) > 1:
        return cmd[1]
    return cmd[0]


def display_name_for(binary: str) -> str:
    return _TOOL_DISPLAY_NAMES.get(binary, binary)


def icon_for(binary: str) -> QIcon:
    """Icono para un binario concreto: prioriza el icono de tema del
    sistema (por si el paquete ya instala uno) y cae al SVG propio en
    assets/ cuando no hay icono de tema disponible."""
    theme_icon = get_system_icon(binary)
    if not theme_icon.isNull():
        return theme_icon
    asset_file = _TOOL_ICON_ASSETS.get(binary)
    if asset_file:
        path = find_asset(asset_file)
        if path:
            return QIcon(path)

    # Algunas apps registran su icono con nombres distintos según la
    # distribución/tema instalado; se prueban los alias habituales antes
    # de dejar la opción sin icono.
    _FALLBACK_NAMES = {
        "gnome-software":  ("org.gnome.Software", "gnome-software", "software",
                             "system-software-install"),
        "plasma-discover": ("plasma-discover", "plasmadiscover", "discover",
                             "system-software-install"),
        "kinfocenter":     ("kinfocenter", "system-info", "dialog-information"),
        "hardinfo":        ("hardinfo", "system-info", "dialog-information"),
        "timeshift-gtk":        ("timeshift", "drive-harddisk-system"),
        "timeshift-launcher":   ("timeshift", "drive-harddisk-system"),
        "timeshift":            ("timeshift", "drive-harddisk-system"),
        "systemsettings":            ("systemsettings", "preferences-system"),
        "gnome-control-center":      ("gnome-control-center", "preferences-system"),
        "xfce4-settings-manager":    ("xfce4-settings-manager", "preferences-system"),
        "kcontrols":                 ("kcontrols", "preferences-system"),
    }
    for fallback_name in _FALLBACK_NAMES.get(binary, ()):
        fallback_icon = get_system_icon(fallback_name)
        if not fallback_icon.isNull():
            return fallback_icon

    return QIcon()


def get_available_commands(candidates: list) -> list:
    """Filtra los candidatos y devuelve solo los que están realmente
    instalados (comprobado en el momento, no al construir la ventana).
    Los binarios recomendados (yel-soft, kcontrols) van siempre primero si
    están disponibles; el resto conserva su orden original.

    Si ningún binario de la lista está instalado, se prioriza igualmente
    el primero de la lista (comportamiento por defecto) en vez de dejar la
    tarjeta sin ninguna opción."""
    if not candidates:
        return []

    available = [c for c in candidates if shutil.which(_binary_id(c))]
    available.sort(key=lambda c: 0 if _binary_id(c) in _RECOMMENDED_BINARIES else 1)

    if not available:
        return [candidates[0]]

    return available


def launch_first_available(candidates: list) -> bool:
    """Lanza directamente la primera alternativa disponible (o la primera de
    la lista si ninguna fue detectada como instalada). Devuelve True si logró
    lanzar algo."""
    available = get_available_commands(candidates)
    for cmd in available:
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (FileNotFoundError, OSError):
            continue

    if available:
        QMessageBox.critical(None, "Error", f"No se encontró: {_binary_id(available[0])}")
    return False


# =============================================================================
# Utilidades Qt
# =============================================================================

def get_system_icon(icon_name: str) -> QIcon:
    icon = QIcon.fromTheme(icon_name)
    return QIcon() if icon.isNull() else icon


def find_asset(filename: str) -> str:
    """Busca un asset por nombre, también dentro de sus subcarpetas."""
    candidates = [
        os.path.join(ASSETS_DIR, filename),
        os.path.join(BASE_DIR, filename),
        os.path.join("/usr/share/k-hello", filename),
        os.path.join("/usr/share/pixmaps", filename),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    if os.path.isdir(ASSETS_DIR):
        for root, _dirs, files in os.walk(ASSETS_DIR):
            if filename in files:
                return os.path.join(root, filename)
    return ""


# Imágenes de Inicio: cada archivo representa una pareja de personajes.
# Se priorizan los nombres nuevos; los anteriores se mantienen como fallback
# para instalaciones que aún no hayan recibido el conjunto actualizado.
# Las imágenes `fmt*.webp` son ilustraciones del tour y nunca entran aquí.
_CHARACTER_PAIRS = [
    "nissa_monika.webp",
    "sun_alex.webp",
    "yelena_vera.webp",
    "yur_suri.webp",
]
_CHARACTER_PAIRS_LEGACY = [
    "yelena-and-suri.webp",
    "vera-and-yur.webp",
    "dana-and-jacky.webp",
    "sun-and-alex.webp",
]
_CHARACTER_FALLBACK = ["suri.webp", "vera.webp", "yur.webp"]


def list_character_images() -> list[str]:
    """Devuelve las parejas de personajes para el carrusel central de Inicio.
    Prioriza los nombres nuevos; usa el conjunto anterior y, en último caso,
    personajes individuales. Las ilustraciones del tour quedan separadas."""
    if not os.path.isdir(ASSETS_DIR):
        return []
    pairs = [path for filename in _CHARACTER_PAIRS
             if (path := find_asset(filename))]
    if pairs:
        return pairs
    legacy_pairs = [path for filename in _CHARACTER_PAIRS_LEGACY
                    if (path := find_asset(filename))]
    if legacy_pairs:
        return legacy_pairs
    return [path for filename in _CHARACTER_FALLBACK
            if (path := find_asset(filename))]


def open_url(url: str):
    QDesktopServices.openUrl(QUrl(url))


def launch_app(cmd: list[str]):
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        QMessageBox.critical(None, "Error", f"No se encontró: {cmd[0]}")


def set_widget_opacity(widget, opacity: float):
    effect = QGraphicsOpacityEffect()
    effect.setOpacity(opacity)
    widget.setGraphicsEffect(effect)


# =============================================================================
# Autostart
# =============================================================================

def _find_system_autostart_file():
    """
    Busca la entrada .desktop de autostart de K-Hello instalada a nivel
    de sistema en /etc/xdg/autostart. Primero prueba el nombre estándar
    y, si no existe, recorre el directorio buscando por Exec/nombre.
    """
    if not os.path.isdir(AUTOSTART_SYSTEM_DIR):
        return None

    candidate = os.path.join(AUTOSTART_SYSTEM_DIR, "k-hello.desktop")
    if os.path.isfile(candidate):
        return candidate

    try:
        for fname in os.listdir(AUTOSTART_SYSTEM_DIR):
            if not fname.endswith(".desktop"):
                continue
            fpath = os.path.join(AUTOSTART_SYSTEM_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            if "k-hello" in content.lower() or APP_ID in content:
                return fpath
    except OSError:
        pass

    return None


def _autostart_desktop_content(enabled: bool) -> str:
    return f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Exec=k-hello
Icon=k-hello
Comment=CuerdOS Welcome App
Categories=System;
X-GNOME-Autostart-enabled={"true" if enabled else "false"}
Hidden={"false" if enabled else "true"}
"""


def autostart_is_enabled() -> bool:
    """
    Comprueba si K-Hello está configurado para autoarrancar, teniendo en
    cuenta tanto la entrada de usuario (~/.config/autostart) como la de
    sistema (/etc/xdg/autostart). Según el estándar XDG, si existe un
    archivo de usuario con el mismo nombre, este tiene prioridad y puede
    ocultar (Hidden=true) la entrada de sistema.
    """
    if os.path.isfile(AUTOSTART_FILE):
        try:
            with open(AUTOSTART_FILE, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            content = ""
        if "Hidden=true" in content or "X-GNOME-Autostart-enabled=false" in content:
            return False
        return True

    # No hay override de usuario: el estado depende de si existe la
    # entrada de sistema en /etc/xdg/autostart.
    return _find_system_autostart_file() is not None


def autostart_enable():
    os.makedirs(AUTOSTART_DIR, exist_ok=True)

    if _find_system_autostart_file() is not None:
        # Ya autoarranca gracias a la entrada del sistema; basta con
        # eliminar cualquier override de usuario que la estuviera ocultando.
        if os.path.isfile(AUTOSTART_FILE):
            os.remove(AUTOSTART_FILE)
        return

    with open(AUTOSTART_FILE, "w", encoding="utf-8") as f:
        f.write(_autostart_desktop_content(enabled=True))


def autostart_disable():
    if _find_system_autostart_file() is not None:
        # No se puede borrar /etc/xdg/autostart sin privilegios de root,
        # así que se crea un override de usuario que la oculta (Hidden=true),
        # el mecanismo estándar de XDG para desactivar una entrada de sistema.
        with open(AUTOSTART_FILE, "w", encoding="utf-8") as f:
            f.write(_autostart_desktop_content(enabled=False))
        return

    if os.path.isfile(AUTOSTART_FILE):
        os.remove(AUTOSTART_FILE)


# =============================================================================
# Primer uso
# =============================================================================

def is_first_run() -> bool:
    return not os.path.isfile(FIRST_RUN_FLAG)


def mark_first_run_done():
    os.makedirs(PREFS_DIR, exist_ok=True)
    with open(FIRST_RUN_FLAG, "w") as f:
        f.write("done\n")


# =============================================================================
# Detección de modo live
# =============================================================================

_FORCE_LIVE = False


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
    """Detecta el modo live únicamente por la presencia de kron-installer/kron
    o por activación forzada vía --live."""
    global _FORCE_LIVE

    if _FORCE_LIVE or "--live" in sys.argv:
        live_cfg      = parse_data_kn_live()
        installer_cmd = live_cfg.get("installer_cmd") or find_builtin_installer()
        return True, installer_cmd

    installer = find_builtin_installer()
    if installer:
        return True, installer

    return False, None


def apply_font(widget, size_px: int, bold: bool = False, italic: bool = False):
    """Aplica tamaño, negrita e itálica a un widget sin usar QSS."""
    f = widget.font()
    f.setPixelSize(size_px)
    f.setBold(bold)
    f.setItalic(italic)
    widget.setFont(f)


def dim_widget(widget):
    """Hace que el texto del widget use el color de texto atenuado del sistema."""
    pal = widget.palette()
    pal.setColor(QPalette.ColorRole.WindowText,
                 QApplication.palette().placeholderText().color())
    widget.setPalette(pal)


def highlight_widget(widget):
    """Hace que el texto del widget use el color highlight del sistema."""
    pal = widget.palette()
    pal.setColor(QPalette.ColorRole.WindowText,
                 QApplication.palette().highlight().color())
    widget.setPalette(pal)
