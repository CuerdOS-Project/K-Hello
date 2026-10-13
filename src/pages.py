#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pages.py — Construcción de las páginas de contenido de K-Hello.

Cada función build_*_page() recibe un objeto "window" (la ventana
principal) para conectar callbacks y devuelve un QWidget listo para
insertarse en el QStackedWidget central. La lógica de datos (qué
herramientas/enlaces mostrar) sigue viviendo en core.py / data.kn,
nunca hardcodeada aquí salvo las claves de traducción.
"""

from __future__ import annotations

import getpass
from datetime import datetime

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap, QPalette, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QApplication, QStyle,
)

from core import (
    APP_NAME, APP_WEBSITE, APP_WIKI, APP_CHANGELOG, APP_KOFI, APP_NEWS,
    SOCIAL_LINKS, find_asset, open_url, launch_app, get_tools,
    apply_font, dim_widget, highlight_widget, list_character_images,
)
from translations import T
from theme import HOME_CHARACTER_SIZE, HOME_LOGO_BOX
from widgets import (
    open_tool, HomeActionButton, LogoBox, CharacterCarousel, render_svg_pixmap,
)

# URL usada como canal de feedback/comunidad (el mismo Telegram que se usa
# como foro en la página de "Nuevo usuario").
FEEDBACK_URL = "https://t.me/CuerdOS_Feedback"


# =============================================================================
# Helpers compartidos (separadores, listas de info, enlaces)
# =============================================================================

def _separator() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setFrameShadow(QFrame.Shadow.Sunken)
    return sep


def _section_header(icon_name: str, text: str) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 4, 0, 4)
    icon_label = QLabel()
    icon = QIcon.fromTheme(icon_name)
    if not icon.isNull():
        icon_label.setPixmap(icon.pixmap(16, 16))
    title = QLabel(f"<b>{text}</b>")
    layout.addWidget(icon_label)
    layout.addWidget(title)
    layout.addStretch()
    return widget


def _info_card(title: str, desc: str, icon_name: str = "text-x-generic") -> QWidget:
    card = QWidget()
    layout = QHBoxLayout(card)
    layout.setContentsMargins(8, 6, 8, 6)

    icon_label = QLabel()
    icon = QIcon.fromTheme(icon_name) or QIcon.fromTheme("text-x-generic")
    if not icon.isNull():
        icon_label.setPixmap(icon.pixmap(20, 20))
    layout.addWidget(icon_label)

    text_layout = QVBoxLayout()
    title_label = QLabel(f"<b>{title}</b>")
    title_label.setWordWrap(True)
    desc_label = QLabel(desc)
    desc_label.setWordWrap(True)
    apply_font(desc_label, 11); dim_widget(desc_label)
    text_layout.addWidget(title_label)
    text_layout.addWidget(desc_label)
    layout.addLayout(text_layout, 1)

    card.setProperty("infoCard", True)
    return card


def _info_list(items: list) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(6)
    layout.setContentsMargins(0, 0, 0, 0)
    for item in items:
        icon_name = item[2] if len(item) > 2 else "text-x-generic"
        layout.addWidget(_info_card(item[0], item[1], icon_name))
    return widget


def _link_row(name: str, desc: str, url: str) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(8, 6, 8, 6)

    icon_label = QLabel()
    icon = QIcon.fromTheme("emblem-web") or QIcon.fromTheme("internet-web-browser")
    if not icon.isNull():
        icon_label.setPixmap(icon.pixmap(20, 20))
    layout.addWidget(icon_label)

    text_layout = QVBoxLayout()
    name_label = QLabel(f"<b>{name}</b>")
    desc_label = QLabel(desc)
    apply_font(desc_label, 11); dim_widget(desc_label)
    text_layout.addWidget(name_label)
    text_layout.addWidget(desc_label)
    layout.addLayout(text_layout, 1)

    open_btn = QPushButton(T("nu_btn_open"))
    open_btn.clicked.connect(lambda: open_url(url))
    open_btn.setProperty("linkBtn", True)
    layout.addWidget(open_btn)

    row.setProperty("linkRow", True)
    return row


# =============================================================================
# Página: Inicio (rediseño completo)
# =============================================================================
#
# Estructura (de arriba a abajo), calcada del diagrama de referencia:
#   - Alfalogo de la distro, siempre en la misma caja estándar (HOME_LOGO_BOX)
#   - Fila de tres columnas: botones izquierda / carrusel de personajes
#     (cuadrado estándar HOME_CHARACTER_SIZE) / botones derecha
#   - Texto descriptivo de la distro
#   - Franja decorativa de montañas al pie
#
# Los seis botones de acción usan la paleta fija de marca (morado, verde
# lima, naranja, verde oscuro, azul nocturno, rosa — ver theme.HOME_COLORS) con
# iconos simbólicos propios en assets/, salvo "Más software", que usa el
# icono de Yel-Soft tal y como se pidió.

def build_home_page(on_navigate=None) -> QWidget:
    container = QWidget()
    main_layout = QVBoxLayout(container)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)

    central_content = QWidget()
    central_content.setMaximumWidth(880)
    central_layout = QVBoxLayout(central_content)
    central_layout.setContentsMargins(32, 24, 32, 8)
    central_layout.setSpacing(22)

    # -- Alfalogo (logo + texto), caja estándar -----------------------------
    logo_row = QHBoxLayout()
    logo_row.addStretch(1)

    logo_path = find_asset("cuerdos-banner.webp") or find_asset("cuerdos.svg")
    logo_box = LogoBox(logo_path, HOME_LOGO_BOX)
    logo_row.addWidget(logo_box, alignment=Qt.AlignmentFlag.AlignCenter)

    logo_row.addStretch(1)
    central_layout.addLayout(logo_row)

    # -- Fila principal: botones / personajes / botones ----------------------
    main_row = QHBoxLayout()
    main_row.setSpacing(20)

    def _make_button(text_key, icon_file, color_key, action):
        btn = HomeActionButton(T(text_key), find_asset(icon_file), color_key)
        btn.clicked.connect(action)
        return btn

    def _side_column(buttons: list) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(12)
        col.addStretch(1)
        for btn in buttons:
            col.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        col.addStretch(1)
        return col

    left_buttons = [
        ("home_btn_news",      "news.svg",        "purple", lambda: open_url(APP_NEWS)),
        ("home_btn_changelog", "updates.svg",      "lime",   lambda: open_url(APP_CHANGELOG)),
        ("home_btn_official",  "official.svg",    "orange", lambda: open_url(APP_WEBSITE)),
    ]
    right_buttons = [
        ("home_btn_feedback",  "feedback.svg",    "mint",   lambda: open_url(FEEDBACK_URL)),
        ("home_btn_support",   "nav-support.svg", "navy",   lambda: on_navigate("support") if on_navigate else None),
        ("home_btn_moresoft",  "yel-store.svg",   "pink",   lambda: launch_app(["yel-soft"])),
    ]

    left_btn_widgets = [_make_button(*spec) for spec in left_buttons]
    right_btn_widgets = [_make_button(*spec) for spec in right_buttons]
    all_btn_widgets = left_btn_widgets + right_btn_widgets

    # Todos los botones comparten el mismo ancho (el del texto más largo
    # entre los seis), en vez de que cada uno se ajuste a su propio texto.
    uniform_width = max(btn.sizeHint().width() for btn in all_btn_widgets) + 8
    for btn in all_btn_widgets:
        btn.setFixedWidth(uniform_width)

    main_row.addLayout(_side_column(left_btn_widgets), 1)

    carousel_col = QVBoxLayout()
    character_images = list_character_images()
    carousel = CharacterCarousel(character_images, HOME_CHARACTER_SIZE)
    carousel_col.addWidget(carousel)
    main_row.addLayout(carousel_col, 0)

    main_row.addLayout(_side_column(right_btn_widgets), 1)

    central_layout.addLayout(main_row, 1)

    # -- Texto descriptivo de la distro (lema + saludo personalizado) -------
    hour = datetime.now().hour
    if hour < 6:
        tod_text = T("tod_night")
    elif hour < 12:
        tod_text = T("tod_morning")
    elif hour < 18:
        tod_text = T("tod_afternoon")
    else:
        tod_text = T("tod_evening")

    try:
        username = getpass.getuser()
    except Exception:
        username = ""

    slogan_line1 = T("home_slogan_line1")
    slogan_line2 = T("home_slogan_line2").format(user=f"<b>{username}</b>", tod=tod_text)
    slogan_line2 = slogan_line2.replace("K-Hello", "<b>K-Hello</b>")

    desc_label = QLabel(f"{slogan_line1}<br>{slogan_line2}")
    desc_label.setTextFormat(Qt.TextFormat.RichText)
    desc_label.setWordWrap(True)
    desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    apply_font(desc_label, 13)
    central_layout.addWidget(desc_label, 0)

    centering_hbox = QHBoxLayout()
    centering_hbox.addStretch(1)
    centering_hbox.addWidget(central_content)
    centering_hbox.addStretch(1)
    main_layout.addLayout(centering_hbox, 1)

    return container


# =============================================================================
# Página: Redes (redes sociales)
# =============================================================================

def build_social_page() -> QWidget:
    widget = QWidget()
    outer = QVBoxLayout(widget)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    content = QWidget()
    content.setMaximumWidth(720)
    layout = QVBoxLayout(content)
    layout.setContentsMargins(32, 32, 32, 32)
    layout.setSpacing(16)

    title = QLabel(T("social_page_title"))
    apply_font(title, 20, bold=True)
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title)

    subtitle = QLabel(T("social_title"))
    subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
    apply_font(subtitle, 12)
    dim_widget(subtitle)
    layout.addWidget(subtitle)

    layout.addWidget(_separator())

    social_grid = QGridLayout()
    social_grid.setSpacing(12)
    social_grid.setAlignment(Qt.AlignmentFlag.AlignCenter)

    row, col = 0, 0
    for key, icon_file, url in SOCIAL_LINKS:
        icon_path = find_asset(icon_file)
        btn = QPushButton("  " + T(key))
        btn.setMinimumHeight(42)
        btn.setMinimumWidth(160)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon_path:
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(20, 20))
        btn.setProperty("social", True)
        btn.clicked.connect(lambda checked, u=url: open_url(u))
        social_grid.addWidget(btn, row, col)
        col += 1
        if col >= 2:
            col = 0
            row += 1

    layout.addLayout(social_grid)
    layout.addStretch()

    centering = QHBoxLayout()
    centering.addStretch(1)
    centering.addWidget(content)
    centering.addStretch(1)
    outer.addLayout(centering, 1)

    return widget


# =============================================================================
# Página: Herramientas
# =============================================================================

def _tool_card(title: str, desc: str, icon_name: str, candidates: list) -> QPushButton:
    btn = QPushButton()
    btn.setFixedSize(220, 170)
    btn.clicked.connect(lambda: open_tool(title, candidates, btn.window()))
    btn.setProperty("toolCard", True)
    btn.setToolTip(desc)

    layout = QVBoxLayout(btn)
    layout.setContentsMargins(16, 24, 16, 20)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.setSpacing(14)

    icon = QIcon.fromTheme(icon_name)
    icon_label = QLabel()
    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_label.setFixedSize(48, 48)
    if not icon.isNull():
        icon_label.setPixmap(icon.pixmap(QSize(48, 48)))
    else:
        fallback = QIcon.fromTheme("application-x-executable")
        if not fallback.isNull():
            icon_label.setPixmap(fallback.pixmap(QSize(48, 48)))
        else:
            icon_label.setText("?")
            apply_font(icon_label, 22); dim_widget(icon_label)
    layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignHCenter)

    title_label = QLabel(title)
    apply_font(title_label, 13, bold=True)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_label.setWordWrap(True)
    title_label.setFixedWidth(180)
    layout.addWidget(title_label)

    return btn


def build_tools_page() -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(32, 24, 32, 24)

    grid = QGridLayout()
    grid.setHorizontalSpacing(24)
    grid.setVerticalSpacing(24)
    grid.setAlignment(Qt.AlignmentFlag.AlignCenter)

    row, col = 0, 0
    for label_key, desc_key, icon_name, candidates in get_tools():
        card = _tool_card(T(label_key), T(desc_key), icon_name, candidates)
        grid.addWidget(card, row, col)
        col += 1
        if col >= 3:
            col = 0
            row += 1

    layout.addStretch(1)
    layout.addLayout(grid)
    layout.addStretch(1)
    return widget


# =============================================================================
# Página: Nuevo usuario
# =============================================================================

def build_newuser_page() -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(24, 16, 24, 16)
    layout.setSpacing(12)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)

    content = QWidget()
    content_layout = QVBoxLayout(content)
    content_layout.setSpacing(16)

    title = QLabel(T("nu_title"))
    apply_font(title, 18, bold=True)
    content_layout.addWidget(title)

    subtitle = QLabel(T("nu_subtitle"))
    subtitle.setWordWrap(True)
    content_layout.addWidget(subtitle)

    content_layout.addWidget(_separator())

    content_layout.addWidget(_section_header("go-first", T("nu_sec_firststeps")))
    first_steps = [
        (T("nu_fs_update"),   T("nu_fs_update_d"),   "software-update-available"),
        (T("nu_fs_store"),    T("nu_fs_store_d"),    "system-software-install"),
        (T("nu_fs_printer"),  T("nu_fs_printer_d"),  "printer"),
        (T("nu_fs_datetime"), T("nu_fs_datetime_d"), "preferences-system"),
    ]
    content_layout.addWidget(_info_list(first_steps))
    content_layout.addWidget(_separator())

    content_layout.addWidget(_section_header("system-software-install", T("nu_sec_apps")))
    apps = [
        (T("nu_app_browser"), T("nu_app_browser_d"), "internet-web-browser"),
        (T("nu_app_office"),  T("nu_app_office_d"),  "libreoffice-writer"),
        (T("nu_app_media"),   T("nu_app_media_d"),   "applications-multimedia"),
        (T("nu_app_photos"),  T("nu_app_photos_d"),  "image-viewer"),
        (T("nu_app_email"),   T("nu_app_email_d"),   "internet-mail"),
        (T("nu_app_files"),   T("nu_app_files_d"),   "system-file-manager"),
    ]
    content_layout.addWidget(_info_list(apps))
    content_layout.addWidget(_separator())

    content_layout.addWidget(_section_header("security-high", T("nu_sec_safety")))
    safety = [
        (T("nu_sa_update"),    T("nu_sa_update_d"),    "software-update-available"),
        (T("nu_sa_backup"),    T("nu_sa_backup_d"),    "drive-harddisk"),
        (T("nu_sa_root"),      T("nu_sa_root_d"),      "dialog-warning"),
        (T("nu_sa_passwords"), T("nu_sa_passwords_d"), "dialog-password"),
    ]
    content_layout.addWidget(_info_list(safety))
    content_layout.addWidget(_separator())

    content_layout.addWidget(_section_header("help-contents", T("nu_sec_help")))
    help_links = [
        (T("other_web"),       T("nu_h_web_d"),       APP_WEBSITE),
        (T("nu_h_wiki"),       T("nu_h_wiki_d"),       APP_WIKI),
        (T("other_changelog"), T("nu_h_changelog_d"), APP_CHANGELOG),
        (T("nu_h_forum"),      T("nu_h_forum_d"),     FEEDBACK_URL),
    ]
    for name, desc, url in help_links:
        content_layout.addWidget(_link_row(name, desc, url))

    content_layout.addStretch()
    scroll.setWidget(content)
    layout.addWidget(scroll)
    return widget


# =============================================================================
# Página: Soporte (Ko-fi)
# =============================================================================

def build_support_page() -> QWidget:
    widget = QWidget()
    outer = QVBoxLayout(widget)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)

    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setContentsMargins(40, 32, 40, 32)
    layout.setSpacing(20)

    header_row = QHBoxLayout()
    header_row.setSpacing(16)

    kofi_icon_path = find_asset("kofi.svg")
    icon_lbl = QLabel()
    if kofi_icon_path:
        icon_lbl.setPixmap(render_svg_pixmap(kofi_icon_path, 56))
    else:
        fb_icon = QIcon.fromTheme("emblem-favorite")
        if not fb_icon.isNull():
            icon_lbl.setPixmap(fb_icon.pixmap(56, 56))
        else:
            icon_lbl.setPixmap(
                QApplication.style().standardIcon(
                    QStyle.StandardPixmap.SP_MessageBoxInformation
                ).pixmap(48, 48))
    header_row.addWidget(icon_lbl)

    title_block = QVBoxLayout()
    title_lbl = QLabel(T("kofi_title"))
    title_font = QFont()
    title_font.setPixelSize(22)
    title_font.setBold(True)
    title_lbl.setFont(title_font)
    title_block.addWidget(title_lbl)

    url_lbl = QLabel(f"<a href='{APP_KOFI}'>{APP_KOFI}</a>")
    url_lbl.setOpenExternalLinks(True)
    apply_font(url_lbl, 12)
    title_block.addWidget(url_lbl)

    header_row.addLayout(title_block, 1)
    layout.addLayout(header_row)
    layout.addWidget(_separator())

    desc1 = QLabel(T("kofi_subtitle"))
    desc1.setWordWrap(True)
    apply_font(desc1, 12)
    layout.addWidget(desc1)

    desc2 = QLabel(T("kofi_working"))
    desc2.setWordWrap(True)
    apply_font(desc2, 12)
    layout.addWidget(desc2)
    layout.addWidget(_separator())

    dest_title = QLabel(f"<b>{T('kofi_dest_title')}</b>")
    apply_font(dest_title, 13)
    layout.addWidget(dest_title)

    dest_items = [
        ("network-server",        "kofi_infra"),
        ("applications-science",  "kofi_testing"),
        ("applications-system",   "kofi_tools"),
        ("system-software-update", "kofi_ecosystem"),
    ]

    dest_grid = QGridLayout()
    dest_grid.setSpacing(12)
    dest_grid.setContentsMargins(0, 4, 0, 4)

    for i, (icon_name, key) in enumerate(dest_items):
        card = QWidget()
        card.setProperty("kofiDestCard", True)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        icon = QIcon.fromTheme(icon_name)
        icon_lbl2 = QLabel()
        if not icon.isNull():
            icon_lbl2.setPixmap(icon.pixmap(22, 22))
        card_layout.addWidget(icon_lbl2)

        text_lbl = QLabel(f"<b>{T(key)}</b>")
        text_lbl.setWordWrap(True)
        apply_font(text_lbl, 12)
        card_layout.addWidget(text_lbl, 1)

        dest_grid.addWidget(card, i // 2, i % 2)

    layout.addLayout(dest_grid)
    layout.addWidget(_separator())

    cta_lbl = QLabel(T("kofi_cta"))
    cta_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    apply_font(cta_lbl, 13, bold=True)
    layout.addWidget(cta_lbl)

    kofi_main_btn = QPushButton("\u2615  " + T("kofi_btn") + "  \u2192  " + APP_KOFI)
    kofi_main_btn.setProperty("kofiBtnMain", True)
    kofi_main_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    kofi_main_btn.setMinimumHeight(44)
    kofi_main_btn.clicked.connect(lambda: open_url(APP_KOFI))
    layout.addWidget(kofi_main_btn)

    nopaywall = QLabel("\U0001f49a  " + T("kofi_nopaywall"))
    nopaywall.setAlignment(Qt.AlignmentFlag.AlignCenter)
    apply_font(nopaywall, 11, italic=True); dim_widget(nopaywall)
    layout.addWidget(nopaywall)

    layout.addStretch()
    scroll.setWidget(content)
    outer.addWidget(scroll, 1)
    return widget
