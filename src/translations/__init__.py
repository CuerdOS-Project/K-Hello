#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translations/__init__.py — Módulo de internacionalización para K-Hello
CuerdOS Welcome Application

Arquitectura:
  - Cada idioma vive en su propio archivo  translations/<lang>.json
  - Este módulo los carga en tiempo de ejecución y expone la misma
    API pública que el antiguo translations.py monolítico:
      T(key)               → traducción activa con fallback a inglés
      set_language(code)   → cambia el idioma globalmente
      get_language()       → código activo (nunca "auto")
      get_language_pref()  → "auto" o código explícito
      is_auto_mode()       → True si se usa la locale del sistema
      detect_system_locale()
      AVAILABLE_LANGUAGES  → dict para la UI de selección
"""

import json
import locale
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

_TRANSLATIONS_DIR = Path(__file__).parent   # src/translations/

# ---------------------------------------------------------------------------
# Idiomas disponibles para la UI de selección
# "auto" es el modo automático — detecta la locale del sistema
# ---------------------------------------------------------------------------

AVAILABLE_LANGUAGES: dict[str, str] = {
    "auto":      "Auto",
    "es":        "Español",
    "en":        "English",
    "pt":        "Português",
    "fr":        "Français",
    "it":        "Italiano",
    "de":        "Deutsch",
    "eu":        "Euskera",
    "ca":        "Català",
    "gl":        "Galego",
    "ja":        "日本語",
    "ja_formal": "日本語（丁寧）",
    "ko":        "한국어",
    "ko_formal": "한국어 (공식)",
    "tr":        "Türkçe",
    "pl":        "Polski",
    "ru":        "Русский",
}

# ---------------------------------------------------------------------------
# Caché de traducciones cargadas
# ---------------------------------------------------------------------------

_cache: dict[str, dict[str, str]] = {}


def _load(lang_code: str) -> dict[str, str]:
    """Carga y cachea el JSON del idioma indicado."""
    if lang_code in _cache:
        return _cache[lang_code]

    path = _TRANSLATIONS_DIR / f"{lang_code}.json"
    if not path.is_file():
        return {}

    with open(path, encoding="utf-8") as f:
        data: dict[str, str] = json.load(f)

    _cache[lang_code] = data
    return data


# Precarga el inglés (fallback) al importar el módulo
_load("en")

# ---------------------------------------------------------------------------
# Estado global (mutable por la app)
# ---------------------------------------------------------------------------

_active_lang: str = "en"
_auto_mode:   bool = False


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def detect_system_locale() -> str:
    """
    Detecta el idioma del sistema operativo y lo mapea al código
    soportado por K-Hello. Devuelve 'en' si no hay coincidencia.

    Prioriza QLocale.system() (la propia Qt, que consulta el idioma del
    entorno de escritorio de forma fiable) porque las variables de
    entorno LANG/LANGUAGE no siempre llegan al proceso cuando la app se
    lanza desde un launcher gráfico o una entrada de autoarranque (a
    diferencia de una terminal, donde sí se heredan). Solo si QLocale no
    está disponible o no aporta un idioma soportado, recurre a las
    variables de entorno y, en último caso, a locale.getlocale().
    """
    # 1) Qt: consulta el idioma configurado en el sistema/escritorio.
    try:
        from PySide6.QtCore import QLocale
        code = QLocale.system().name()[:2].lower()
        if code and (_TRANSLATIONS_DIR / f"{code}.json").is_file():
            return code
    except Exception:
        pass

    # 2) Variables de entorno típicas de Linux (por si Qt no da resultado).
    try:
        lang_env = (
            os.environ.get("LANGUAGE", "").split(":")[0]
            or os.environ.get("LC_ALL")
            or os.environ.get("LC_MESSAGES")
            or os.environ.get("LANG")
            or ""
        )
        code = lang_env[:2].lower()
        if code and (_TRANSLATIONS_DIR / f"{code}.json").is_file():
            return code
    except Exception:
        pass

    # 3) Último recurso: locale del proceso Python (normalmente poco
    # fiable si no se llamó antes a setlocale(), pero no cuesta probar).
    try:
        code = (locale.getlocale()[0] or "")[:2].lower()
        if code and (_TRANSLATIONS_DIR / f"{code}.json").is_file():
            return code
    except Exception:
        pass

    return "en"


def set_language(lang_code: str) -> None:
    """
    Establece el idioma activo globalmente.
      - "auto"          → activa modo automático (usa la locale del sistema)
      - código ISO 639-1 → idioma explícito
      - código no válido → cae en inglés
    """
    global _active_lang, _auto_mode
    if lang_code == "auto":
        _auto_mode   = True
        _active_lang = detect_system_locale()
    else:
        _auto_mode   = False
        json_path    = _TRANSLATIONS_DIR / f"{lang_code}.json"
        _active_lang = lang_code if json_path.is_file() else "en"

    _load(_active_lang)   # asegura que esté en caché


def get_language() -> str:
    """Devuelve el código del idioma actualmente activo (nunca 'auto')."""
    return _active_lang


def get_language_pref() -> str:
    """
    Devuelve la preferencia guardada del usuario:
      - "auto" si el modo automático está activo
      - el código de idioma en caso contrario
    """
    return "auto" if _auto_mode else _active_lang


def is_auto_mode() -> bool:
    """True si el modo de detección automática de idioma está activo."""
    return _auto_mode


def T(key: str) -> str:
    """
    Función de traducción principal (alias corto, al estilo gettext).

    Uso:
        from translations import T
        label = QLabel(T("welcome_title"))

    Estrategia de fallback:
        1. Idioma activo       → clave buscada
        2. Inglés (fallback)   → clave buscada
        3. Sin fallback        → devuelve la clave misma (para depuración)
    """
    lang_dict = _load(_active_lang)
    if key in lang_dict:
        return lang_dict[key]

    fallback = _load("en")
    if key in fallback:
        return fallback[key]

    # Última salida: devolver la clave tal cual (facilita detectar traducciones faltantes)
    return key


def get_translation(key: str, lang_code: str | None = None) -> str:
    """
    Versión extendida que permite especificar el idioma explícitamente
    sin cambiar el idioma global.

    Parámetros:
        key       — clave de traducción
        lang_code — código ISO 639-1 opcional; si es None usa el idioma activo
    """
    if lang_code is None:
        return T(key)

    lang_dict = _load(lang_code)
    if key in lang_dict:
        return lang_dict[key]

    return _load("en").get(key, key)
