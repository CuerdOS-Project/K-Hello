#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qwindow.py — Widgets y ventanas Qt para K-Hello (CuerdOS GNU/Linux)
"""

import os
import sys
import subprocess
import shutil
import getpass
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QSize, QSettings, QUrl, QPointF
from PySide6.QtGui import QIcon, QPixmap, QFont, QDesktopServices, QPainter, QColor, QPalette, QAction, QPolygonF
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QScrollArea, QFrame, QDialog,
    QRadioButton, QButtonGroup, QGridLayout,
    QMessageBox, QCheckBox, QSizePolicy,
    QComboBox, QMenu, QDialogButtonBox,
    QGraphicsOpacityEffect, QStyle,
)

from translations import T, set_language, get_language_pref, detect_system_locale, AVAILABLE_LANGUAGES
from about import AboutDialog
from core import (
    APP_ID, APP_VERSION, APP_NAME, APP_AUTHOR, APP_WEBSITE, APP_WIKI,
    APP_CHANGELOG, APP_NEWS, APP_DEBIAN_WIKI, APP_KOFI,
    BASE_DIR, PREFS_FILE,
    SOCIAL_LINKS, _DEFAULT_TOOLS,
    find_asset, open_url, launch_app,
    autostart_is_enabled, autostart_enable, autostart_disable,
    is_first_run, mark_first_run_done, set_widget_opacity,
    detect_live_mode, parse_data_kn_live, get_tools,
)

# =============================================================================
# Widget de fondo animado
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
        # Evita que Qt pinte el fondo antes de paintEvent → sin parpadeo
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

        # Relleno de fondo sólido primero (evita artefactos de repintado)
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
                    cx     = cx_f * w + x_base
                    peak_y = h - ph_f * h * 0.88
                    hw     = hw_f * w
                    painter.drawPolygon(QPolygonF([
                        QPointF(cx - hw, h),
                        QPointF(cx,      peak_y),
                        QPointF(cx + hw, h),
                    ]))

        painter.end()


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
# Diálogo de idioma
# =============================================================================

class LanguageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(T("lang_dialog_title"))
        self.setMinimumWidth(300)
        self.setModal(True)

        layout = QVBoxLayout(self)

        detected = detect_system_locale()
        detected_name = AVAILABLE_LANGUAGES.get(detected, detected.upper())
        auto_label = f"{T('lang_auto')} ({detected_name})"

        self.lang_group = QButtonGroup(self)
        current_pref = get_language_pref()

        self.auto_radio = QRadioButton(auto_label)
        self.auto_radio.setChecked(current_pref == "auto")
        self.lang_group.addButton(self.auto_radio)
        layout.addWidget(self.auto_radio)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(300)

        lang_widget = QWidget()
        lang_layout = QVBoxLayout(lang_widget)

        self.radios = {}
        for code, name in AVAILABLE_LANGUAGES.items():
            if code == "auto":
                continue
            radio = QRadioButton(name)
            radio.setChecked(current_pref == code)
            self.lang_group.addButton(radio)
            self.radios[code] = radio
            lang_layout.addWidget(radio)

        scroll.setWidget(lang_widget)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_selected_language(self) -> str:
        if self.auto_radio.isChecked():
            return "auto"
        for code, radio in self.radios.items():
            if radio.isChecked():
                return code
        return "auto"


# =============================================================================
# Ventana de modo Live
# =============================================================================

class LiveModeWindow(QDialog):
    """Diálogo compacto de modo live: selector de idioma + dos botones de acción."""

    def __init__(self, installer_cmd, on_try_callback, install_label=None):
        super().__init__()
        self.installer_cmd  = installer_cmd
        self.on_try_callback = on_try_callback
        self.install_label  = install_label

        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)
        self.setMinimumWidth(480)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle(T("live_title"))

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Cabecera con logo + título + selector de idioma
        header = QWidget()
        header.setProperty("liveHeader", True)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 14, 20, 14)
        h_lay.setSpacing(12)

        logo_path = find_asset("cuerdos.svg") or find_asset("k-hello.svg")
        if logo_path:
            logo_lbl = QLabel()
            logo_lbl.setPixmap(QPixmap(logo_path).scaled(
                36, 36, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            h_lay.addWidget(logo_lbl)

        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet("font-size: 17px; font-weight: bold;")
        h_lay.addWidget(self._title_lbl, 1)

        # Selector de idioma en la cabecera
        self._lang_combo = QComboBox()
        self._lang_combo.setMinimumWidth(130)
        for code, name in AVAILABLE_LANGUAGES.items():
            self._lang_combo.addItem(name, code)
        self._lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        _lang_icon_lbl = QLabel()
        _lang_qicon = QIcon.fromTheme("preferences-desktop-locale")
        if not _lang_qicon.isNull():
            _lang_icon_lbl.setPixmap(_lang_qicon.pixmap(16, 16))
        h_lay.addWidget(_lang_icon_lbl)
        h_lay.addWidget(self._lang_combo)

        root.addWidget(header)

        # Subtítulo
        self._subtitle_lbl = QLabel()
        self._subtitle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle_lbl.setContentsMargins(20, 10, 20, 4)
        root.addWidget(self._subtitle_lbl)

        # Tarjetas de acción
        cards_widget = QWidget()
        cards_lay = QHBoxLayout(cards_widget)
        cards_lay.setContentsMargins(24, 12, 24, 24)
        cards_lay.setSpacing(20)

        self._install_btn = self._make_card(
            find_asset("cuerdos.svg"),
            "system-software-install",
            "",
            "",
            self._on_install,
            enabled=self.installer_cmd is not None,
        )
        cards_lay.addWidget(self._install_btn)

        self._try_btn = self._make_card(
            None,
            "media-playback-start",
            "",
            "",
            self._on_try,
            enabled=True,
        )
        cards_lay.addWidget(self._try_btn)

        root.addWidget(cards_widget)
        self.adjustSize()
        self._refresh_texts()

    def _make_card(self, svg_path, theme_icon, title, desc, callback, enabled):
        btn = QPushButton()
        btn.setEnabled(enabled)
        btn.setProperty("liveCard", True)
        btn.setMinimumSize(180, 160)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.clicked.connect(callback)

        lay = QVBoxLayout(btn)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(8)

        # Icono
        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setObjectName("cardIcon")
        pix = None
        if svg_path and os.path.isfile(svg_path):
            pix = QPixmap(svg_path).scaled(
                52, 52, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
        if pix is None or pix.isNull():
            icon = QIcon.fromTheme(theme_icon)
            if not icon.isNull():
                pix = icon.pixmap(QSize(52, 52))
        if pix and not pix.isNull():
            icon_lbl.setPixmap(pix)
        lay.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("cardTitle")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setWordWrap(True)
        lay.addWidget(title_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setObjectName("cardDesc")
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setStyleSheet("font-size: 10px; color: gray;")
        lay.addWidget(desc_lbl)

        return btn

    def _refresh_texts(self):
        """Actualiza todos los textos traducibles sin reconstruir widgets."""
        self.setWindowTitle(T("live_title"))
        self._title_lbl.setText(T("live_title"))
        self._subtitle_lbl.setText(T("live_subtitle"))

        # Sincronizar combo sin disparar señal
        self._lang_combo.blockSignals(True)
        idx = self._lang_combo.findData(get_language_pref())
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        self._lang_combo.blockSignals(False)

        # Actualizar textos de tarjetas
        def _set_card_text(btn, title, desc):
            for child in btn.findChildren(QLabel):
                if child.objectName() == "cardTitle":
                    child.setText(title)
                elif child.objectName() == "cardDesc":
                    child.setText(desc)

        install_label = self.install_label or T("live_install_label")
        _set_card_text(self._install_btn, install_label, T("live_install_desc"))
        _set_card_text(self._try_btn,     T("live_try_label"), T("live_try_desc"))

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


# =============================================================================
# Ventana de primer uso
# =============================================================================

class FirstUseWindow(QDialog):
    def __init__(self, on_done_callback):
        super().__init__()
        self.on_done = on_done_callback

        self.setWindowTitle(APP_NAME)
        self.setFixedSize(660, 440)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)

        self.setup_ui()
        self.start_animation()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Panel izquierdo: sidebar con color de acento ───────────────────
        left_panel = QWidget()
        left_panel.setMinimumWidth(240)
        left_panel.setMaximumWidth(260)
        left_panel.setProperty("welcomeSidebar", True)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.setContentsMargins(24, 40, 24, 40)
        left_layout.setSpacing(16)

        computer_path = find_asset("computer.svg") or find_asset("cuerdos.svg")
        if computer_path:
            computer_label = QLabel()
            pixmap = QPixmap(computer_path)
            computer_label.setPixmap(pixmap.scaled(160, 160, Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation))
            computer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            left_layout.addWidget(computer_label)

        brand_label = QLabel(APP_NAME)
        brand_font = QFont()
        brand_font.setPixelSize(16)
        brand_font.setBold(True)
        brand_label.setFont(brand_font)
        brand_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_label.setStyleSheet("color: white; opacity: 0.9;")
        left_layout.addWidget(brand_label)

        layout.addWidget(left_panel)

        # ── Panel derecho: contenido ───────────────────────────────────────
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(36, 44, 36, 32)
        right_layout.setSpacing(10)

        self.welcome_title = QLabel(T("welcome_title"))
        wt_font = QFont()
        wt_font.setPixelSize(20)
        wt_font.setBold(True)
        self.welcome_title.setFont(wt_font)
        set_widget_opacity(self.welcome_title, 0)
        right_layout.addWidget(self.welcome_title)

        try:
            username = getpass.getuser()
            user_layout = QHBoxLayout()
            wave = QLabel()
            _wave_icon = QIcon.fromTheme("avatar-default")
            if not _wave_icon.isNull():
                wave.setPixmap(_wave_icon.pixmap(22, 22))
            else:
                wave.setText("→")
            user_name = QLabel(username)
            un_font = QFont()
            un_font.setPixelSize(17)
            un_font.setBold(True)
            user_name.setFont(un_font)
            user_layout.addWidget(wave)
            user_layout.addWidget(user_name)
            user_layout.addStretch()
            right_layout.addLayout(user_layout)
        except Exception:
            pass

        right_layout.addSpacing(12)

        self.thanks_label = QLabel(T("first_thanks"))
        self.thanks_label.setWordWrap(True)
        set_widget_opacity(self.thanks_label, 0)
        right_layout.addWidget(self.thanks_label)

        self.app_intro_label = QLabel(f"<b>{APP_NAME}</b> {T('first_app_intro')}")
        self.app_intro_label.setWordWrap(True)
        set_widget_opacity(self.app_intro_label, 0)
        right_layout.addWidget(self.app_intro_label)

        self.project_label = QLabel(T("first_project"))
        self.project_label.setWordWrap(True)
        set_widget_opacity(self.project_label, 0)
        right_layout.addWidget(self.project_label)

        self.board_label = QLabel(f"<i>{T('first_aboard')}</i>")
        self.board_label.setWordWrap(True)
        set_widget_opacity(self.board_label, 0)
        right_layout.addWidget(self.board_label)

        right_layout.addStretch()

        self.continue_btn = QPushButton(T("first_get_started"))
        self.continue_btn.clicked.connect(self.on_continue)
        set_widget_opacity(self.continue_btn, 0)
        btn_pal = self.continue_btn.palette()
        btn_pal.setColor(QPalette.ColorRole.Button, self.continue_btn.palette().highlight().color())
        btn_pal.setColor(QPalette.ColorRole.ButtonText, QColor("white"))
        self.continue_btn.setPalette(btn_pal)
        self.continue_btn.setAutoFillBackground(True)
        right_layout.addWidget(self.continue_btn, alignment=Qt.AlignmentFlag.AlignRight)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        close_btn = QPushButton(T("first_close"))
        close_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(close_btn)
        right_layout.addLayout(bottom_layout)

        layout.addWidget(right_panel)

    def start_animation(self):
        self.animation_step = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_step)
        self.animation_timer.start(50)

    def animate_step(self):
        self.animation_step += 1
        step = self.animation_step

        if 5 <= step <= 15:
            t = min(1.0, (step - 5) / 10)
            set_widget_opacity(self.welcome_title, t)
        if 10 <= step <= 20:
            t = min(1.0, (step - 10) / 10)
            set_widget_opacity(self.thanks_label, t)
        if 15 <= step <= 25:
            t = min(1.0, (step - 15) / 10)
            set_widget_opacity(self.app_intro_label, t)
        if 20 <= step <= 30:
            t = min(1.0, (step - 20) / 10)
            set_widget_opacity(self.project_label, t)
        if 25 <= step <= 35:
            t = min(1.0, (step - 25) / 10)
            set_widget_opacity(self.board_label, t)
        if 30 <= step <= 40:
            t = min(1.0, (step - 30) / 10)
            set_widget_opacity(self.continue_btn, t)

        if step >= 40:
            self.animation_timer.stop()

    def on_continue(self):
        mark_first_run_done()
        self.on_done()
        self.accept()


# =============================================================================
# Ventana principal
# =============================================================================

class KHelloWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(760, 500)
        self.resize(760, 500)

        # Icono de ventana (Xorg/XFCE lo leen de windowIcon; Wayland usa app_id vía QApplication)
        app_icon = QIcon.fromTheme(APP_ID)
        if app_icon.isNull():
            svg_path = find_asset("k-hello.svg") or find_asset("cuerdos.svg")
            if svg_path:
                app_icon = QIcon(svg_path)
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)

        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # PESTAÑAS CENTRADAS
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)

        # Centrar pestañas: usamos expansión uniforme vía QSS + tabBar alignment
        tab_bar = self.tab_widget.tabBar()
        tab_bar.setExpanding(False)   # no estirar individualmente; lo controlamos con QSS
        tab_bar.setDrawBase(False)

        self.tab_widget.addTab(self.create_home_tab(), T("tab_home"))
        self.tab_widget.addTab(self.create_tools_tab(), T("tab_tools"))
        self.tab_widget.addTab(self.create_newuser_tab(), T("tab_newuser"))
        self.tab_widget.addTab(self.create_other_tab(), T("tab_other"))
        self.tab_widget.addTab(self.create_support_tab(), T("tab_support"))

        # Espacio izquierdo para empujar las tabs al centro
        left_spacer = QWidget()
        left_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.tab_widget.setCornerWidget(left_spacer, Qt.Corner.TopLeftCorner)

        # Botón hamburguesa — se crea via helper para poder recrearlo en refresh_ui
        self._setup_corner_widgets()

        layout.addWidget(self.tab_widget, 1)

        # BARRA INFERIOR
        bottom_bar = self.create_bottom_bar()
        layout.addWidget(bottom_bar)

    def _setup_corner_widgets(self):
        left_spacer = QWidget()
        left_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.tab_widget.setCornerWidget(left_spacer, Qt.Corner.TopLeftCorner)

        self.menu_btn = QPushButton()
        _menu_icon = QIcon.fromTheme("open-menu-symbolic")
        if _menu_icon.isNull():
            _menu_icon = QIcon.fromTheme("application-menu")
        if _menu_icon.isNull():
            self.menu_btn.setText("≡")
        else:
            self.menu_btn.setIcon(_menu_icon)
        self.menu_btn.setFixedSize(36, 28)
        self.menu_btn.setProperty("menuBtn", True)
        self.menu_btn.setToolTip(T("tt_settings"))
        self.menu_btn.clicked.connect(self.show_settings_menu)
        self.tab_widget.setCornerWidget(self.menu_btn, Qt.Corner.TopRightCorner)

    def show_settings_menu(self):
        menu = QMenu(self)

        lang_icon = QIcon.fromTheme("preferences-desktop-locale")
        if lang_icon.isNull():
            lang_icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        lang_action = QAction(lang_icon, T("menu_language"), self)
        lang_action.triggered.connect(self.show_language_dialog)
        menu.addAction(lang_action)

        menu.addSeparator()

        about_icon = QIcon.fromTheme("help-about")
        if about_icon.isNull():
            about_icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        about_action = QAction(about_icon, T("menu_about"), self)
        about_action.triggered.connect(self.show_about_dialog)
        menu.addAction(about_action)

        menu.exec(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomRight()))

    def show_language_dialog(self):
        dialog = LanguageDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = dialog.get_selected_language()
            set_language(selected)
            try:
                from PySide6.QtCore import QSettings as _QS
                _s = _QS(PREFS_FILE, _QS.Format.IniFormat)
                _s.setValue("language", selected)
                _s.sync()
            except Exception:
                pass
            self.refresh_ui()

    def show_about_dialog(self):
        dlg = AboutDialog(self)
        dlg.exec()

    def create_home_tab(self) -> QWidget:
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Contenedor central con ancho máximo para agrupar elementos limpiamente al maximizar
        central_content = QWidget()
        central_content.setMaximumWidth(800)
        central_layout = QVBoxLayout(central_content)
        central_layout.setContentsMargins(32, 20, 32, 10)
        central_layout.setSpacing(24)

        # ── Cabecera de bienvenida (Estructura interna unificada sin widgets padres extra) ──
        header_block = QHBoxLayout()
        header_block.setSpacing(20)

        logo_path = find_asset("cuerdos.svg") or find_asset("k-hello.svg")
        if logo_path:
            logo_label = QLabel()
            pixmap = QPixmap(logo_path)
            logo_label.setPixmap(pixmap.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation))
            header_block.addWidget(logo_label)

        title_block = QVBoxLayout()
        title_block.setSpacing(4)

        title = QLabel(T("welcome_title"))
        title_font = QFont()
        title_font.setPixelSize(22)
        title_font.setBold(True)
        title.setFont(title_font)
        title_block.addWidget(title)

        try:
            username = getpass.getuser()
            user_layout = QHBoxLayout()
            user_layout.setSpacing(6)
            wave_lbl = QLabel()
            _wave_icon2 = QIcon.fromTheme("avatar-default")
            if not _wave_icon2.isNull():
                wave_lbl.setPixmap(_wave_icon2.pixmap(18, 18))
            else:
                wave_lbl.setText("→")
            user_name = QLabel(username)
            un_font = QFont()
            un_font.setPixelSize(16)
            un_font.setBold(True)
            user_name.setFont(un_font)
            user_layout.addWidget(wave_lbl)
            user_layout.addWidget(user_name)
            user_layout.addStretch()
            title_block.addLayout(user_layout)
        except Exception:
            pass

        subtitle = QLabel(T("welcome_subtitle"))
        sub_font = QFont()
        sub_font.setItalic(True)
        subtitle.setFont(sub_font)
        title_block.addWidget(subtitle)

        header_block.addLayout(title_block, 1)

        # Chips de info (hora del día + distro)
        chips_vbox = QVBoxLayout()
        chips_vbox.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        chips_vbox.setSpacing(6)

        hour = datetime.now().hour
        if hour < 6:
            tod_text = T("tod_night")
        elif hour < 12:
            tod_text = T("tod_morning")
        elif hour < 18:
            tod_text = T("tod_afternoon")
        else:
            tod_text = T("tod_evening")

        tod_chip = ChipLabel(tod_text)
        tod_chip.setContentsMargins(10, 4, 10, 4)
        tod_chip.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        chips_vbox.addWidget(tod_chip, alignment=Qt.AlignmentFlag.AlignRight)

        distro = self.get_distro_name()
        if distro:
            distro_chip = ChipLabel(distro)
            distro_chip.setContentsMargins(10, 4, 10, 4)
            distro_chip.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
            distro_chip.setWordWrap(True)
            distro_chip.setMaximumWidth(280)
            distro_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chips_vbox.addWidget(distro_chip, alignment=Qt.AlignmentFlag.AlignRight)

        header_block.addLayout(chips_vbox)
        central_layout.addLayout(header_block)

        # ── Sección de redes sociales ───────────────────────────────────────
        social_section = QWidget()
        social_layout = QVBoxLayout(social_section)
        social_layout.setContentsMargins(0, 10, 0, 0)
        social_layout.setSpacing(10)

        social_title = QLabel(T("social_title"))
        social_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        st_font = QFont()
        st_font.setPixelSize(11)
        social_title.setFont(st_font)
        st_pal = social_title.palette()
        st_pal.setColor(QPalette.ColorRole.WindowText, QColor("gray"))
        social_title.setPalette(st_pal)
        social_layout.addWidget(social_title)

        social_grid = QGridLayout()
        social_grid.setSpacing(8)
        social_grid.setAlignment(Qt.AlignmentFlag.AlignCenter)

        row, col = 0, 0
        for key, icon_file, url in SOCIAL_LINKS:
            icon_path = find_asset(icon_file)
            btn = QPushButton(T(key))
            if icon_path:
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(18, 18))
            btn.setProperty("social", True)
            btn.clicked.connect(lambda checked, u=url: open_url(u))
            social_grid.addWidget(btn, row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1

        social_layout.addLayout(social_grid)
        central_layout.addWidget(social_section)

        # Centrador horizontal para que el bloque no se rompa de extremo a extremo
        centering_hbox = QHBoxLayout()
        centering_hbox.addStretch(1)
        centering_hbox.addWidget(central_content)
        centering_hbox.addStretch(1)

        main_layout.addLayout(centering_hbox)

        # ── Montañas geométricas fijadas al borde inferior ─────────────────
        mountains = GeometricMountainsWidget()
        main_layout.addWidget(mountains, 1)

        return container

    def get_distro_name(self) -> str:
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
        return ""

    def create_tools_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        grid = QGridLayout()
        grid.setSpacing(20)
        grid.setAlignment(Qt.AlignmentFlag.AlignCenter)

        row, col = 0, 0
        for label_key, desc_key, icon_name, cmd in get_tools():
            card = self.create_tool_card(T(label_key), T(desc_key), icon_name, cmd)
            grid.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1

        layout.addLayout(grid)
        layout.addStretch()
        return widget

    def create_tool_card(self, title: str, desc: str, icon_name: str, cmd: list) -> QPushButton:
        btn = QPushButton()
        btn.setMinimumSize(160, 130)
        btn.setMaximumWidth(220)
        btn.clicked.connect(lambda: launch_app(cmd))
        btn.setProperty("toolCard", True)
        btn.setToolTip(desc)

        layout = QVBoxLayout(btn)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        icon = QIcon.fromTheme(icon_name)
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(QSize(40, 40)))
        else:
            fallback = QIcon.fromTheme("application-x-executable")
            if not fallback.isNull():
                icon_label.setPixmap(fallback.pixmap(QSize(40, 40)))
            else:
                icon_label.setText("?")
                icon_label.setStyleSheet("font-size: 20px; color: gray;")
        layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        return btn

    def create_newuser_tab(self) -> QWidget:
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
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        content_layout.addWidget(title)

        subtitle = QLabel(T("nu_subtitle"))
        subtitle.setWordWrap(True)
        content_layout.addWidget(subtitle)

        content_layout.addWidget(self.create_separator())

        # Primeros pasos
        content_layout.addWidget(self.create_section_header("go-first", T("nu_sec_firststeps")))
        first_steps = [
            (T("nu_fs_update"), T("nu_fs_update_d")),
            (T("nu_fs_store"), T("nu_fs_store_d")),
            (T("nu_fs_printer"), T("nu_fs_printer_d")),
            (T("nu_fs_datetime"), T("nu_fs_datetime_d")),
        ]
        content_layout.addWidget(self.create_info_list(first_steps))

        content_layout.addWidget(self.create_separator())

        # Aplicaciones
        content_layout.addWidget(self.create_section_header("system-software-install", T("nu_sec_apps")))
        apps = [
            (T("nu_app_browser"), T("nu_app_browser_d")),
            (T("nu_app_office"), T("nu_app_office_d")),
            (T("nu_app_media"), T("nu_app_media_d")),
            (T("nu_app_photos"), T("nu_app_photos_d")),
            (T("nu_app_email"), T("nu_app_email_d")),
            (T("nu_app_files"), T("nu_app_files_d")),
        ]
        content_layout.addWidget(self.create_info_list(apps))

        content_layout.addWidget(self.create_separator())

        # Seguridad
        content_layout.addWidget(self.create_section_header("security-high", T("nu_sec_safety")))
        safety = [
            (T("nu_sa_update"), T("nu_sa_update_d")),
            (T("nu_sa_backup"), T("nu_sa_backup_d")),
            (T("nu_sa_root"), T("nu_sa_root_d")),
            (T("nu_sa_passwords"), T("nu_sa_passwords_d")),
        ]
        content_layout.addWidget(self.create_info_list(safety))

        content_layout.addWidget(self.create_separator())

        # Ayuda
        content_layout.addWidget(self.create_section_header("help-contents", T("nu_sec_help")))
        help_links = [
            (T("nu_h_wiki"), T("nu_h_wiki_d"), APP_WIKI),
            (T("nu_h_debian"), T("nu_h_debian_d"), APP_DEBIAN_WIKI),
            (T("nu_h_forum"), T("nu_h_forum_d"), "https://t.me/+GibSWjFc89Q2ODU8"),
        ]
        for name, desc, url in help_links:
            content_layout.addWidget(self.create_link_row(name, desc, url))

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)
        return widget

    def create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        return sep

    def create_section_header(self, icon_name: str, text: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 4, 0, 4)
        icon_label = QLabel()
        _sh_icon = QIcon.fromTheme(icon_name)
        if not _sh_icon.isNull():
            icon_label.setPixmap(_sh_icon.pixmap(16, 16))
        title = QLabel(f"<b>{text}</b>")
        layout.addWidget(icon_label)
        layout.addWidget(title)
        layout.addStretch()
        return widget

    def create_info_list(self, items: list) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        for title, desc in items:
            card = self.create_info_card(title, desc)
            layout.addWidget(card)

        return widget

    def create_info_card(self, title: str, desc: str) -> QWidget:
        card = QWidget()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)

        icon_label = QLabel()
        _card_icon = QIcon.fromTheme("text-x-generic")
        if not _card_icon.isNull():
            icon_label.setPixmap(_card_icon.pixmap(20, 20))
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        title_label = QLabel(f"<b>{title}</b>")
        title_label.setWordWrap(True)
        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 11px; color: gray;")
        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)
        layout.addLayout(text_layout, 1)

        card.setProperty("infoCard", True)
        return card

    def create_link_row(self, name: str, desc: str, url: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 6, 8, 6)

        icon_label = QLabel()
        _link_icon = QIcon.fromTheme("emblem-web")
        if _link_icon.isNull():
            _link_icon = QIcon.fromTheme("internet-web-browser")
        if not _link_icon.isNull():
            icon_label.setPixmap(_link_icon.pixmap(20, 20))
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        name_label = QLabel(f"<b>{name}</b>")
        desc_label = QLabel(desc)
        desc_label.setStyleSheet("font-size: 11px; color: gray;")
        text_layout.addWidget(name_label)
        text_layout.addWidget(desc_label)
        layout.addLayout(text_layout, 1)

        open_btn = QPushButton(T("nu_btn_open"))
        open_btn.clicked.connect(lambda: open_url(url))
        open_btn.setProperty("linkBtn", True)
        layout.addWidget(open_btn)

        row.setProperty("linkRow", True)
        return row

    def create_other_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        title = QLabel(T("other_title"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        links = [
            (T("other_web"), APP_WEBSITE),
            (T("other_wiki"), APP_WIKI),
            (T("other_changelog"), APP_CHANGELOG),
            (T("other_debian_wiki"), APP_DEBIAN_WIKI),
        ]

        for label, url in links:
            row = self.create_other_link_row(label, url)
            layout.addWidget(row)

        layout.addStretch()
        return widget

    def create_support_tab(self) -> QWidget:
        """Pestaña de apoyo al proyecto via Ko-fi."""
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

        # Cabecera Ko-fi
        header_row = QHBoxLayout()
        header_row.setSpacing(16)

        kofi_icon_path = find_asset("kofi.svg")
        if kofi_icon_path:
            icon_lbl = QLabel()
            icon_lbl.setPixmap(QPixmap(kofi_icon_path).scaled(
                56, 56, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            header_row.addWidget(icon_lbl)
        else:
            _kofi_fb_icon = QIcon.fromTheme("emblem-favorite")
            if not _kofi_fb_icon.isNull():
                icon_lbl = QLabel()
                icon_lbl.setPixmap(_kofi_fb_icon.pixmap(56, 56))
                header_row.addWidget(icon_lbl)
            else:
                icon_lbl = QLabel()
                icon_lbl.setPixmap(
                    QApplication.style().standardIcon(
                        QStyle.StandardPixmap.SP_MessageBoxInformation
                    ).pixmap(48, 48)
                )
                header_row.addWidget(icon_lbl)

        title_block = QVBoxLayout()
        title_lbl = QLabel(T("kofi_title"))
        title_font = QFont()
        title_font.setPixelSize(22)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        title_block.addWidget(title_lbl)

        url_lbl = QLabel(f"<a href=\'{APP_KOFI}\' style=\'color:#29ABE0;\'>{APP_KOFI}</a>")
        url_lbl.setOpenExternalLinks(True)
        url_lbl.setStyleSheet("font-size: 12px;")
        title_block.addWidget(url_lbl)

        header_row.addLayout(title_block, 1)
        layout.addLayout(header_row)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep1)

        desc1 = QLabel(T("kofi_subtitle"))
        desc1.setWordWrap(True)
        desc1.setStyleSheet("font-size: 12px;")
        layout.addWidget(desc1)

        desc2 = QLabel(T("kofi_working"))
        desc2.setWordWrap(True)
        desc2.setStyleSheet("font-size: 12px;")
        layout.addWidget(desc2)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep2)

        dest_title = QLabel(f"<b>{T('kofi_dest_title')}</b>")
        dest_title.setStyleSheet("font-size: 13px;")
        layout.addWidget(dest_title)

        dest_items = [
            ("network-server",       "kofi_infra"),
            ("applications-science", "kofi_testing"),
            ("applications-system",  "kofi_tools"),
            ("system-software-update","kofi_ecosystem"),
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

            _card_icon = QIcon.fromTheme(icon_name)
            icon_lbl2 = QLabel()
            if not _card_icon.isNull():
                icon_lbl2.setPixmap(_card_icon.pixmap(22, 22))
            card_layout.addWidget(icon_lbl2)

            text_lbl = QLabel(f"<b>{T(key)}</b>")
            text_lbl.setWordWrap(True)
            text_lbl.setStyleSheet("font-size: 12px;")
            card_layout.addWidget(text_lbl, 1)

            dest_grid.addWidget(card, i // 2, i % 2)

        layout.addLayout(dest_grid)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.HLine)
        sep3.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep3)

        cta_lbl = QLabel(T("kofi_cta"))
        cta_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cta_lbl.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(cta_lbl)

        kofi_main_btn = QPushButton("\u2615  " + T("kofi_btn") + "  \u2192  " + APP_KOFI)
        kofi_main_btn.setProperty("kofiBtnMain", True)
        kofi_main_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        kofi_main_btn.setMinimumHeight(44)
        kofi_main_btn.clicked.connect(lambda: open_url(APP_KOFI))
        layout.addWidget(kofi_main_btn)

        nopaywall = QLabel("\U0001f49a  " + T("kofi_nopaywall"))
        nopaywall.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nopaywall.setStyleSheet("font-size: 11px; color: gray; font-style: italic;")
        layout.addWidget(nopaywall)

        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        return widget

    def create_other_link_row(self, label: str, url: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 8, 8, 8)

        label_widget = QLabel(label)
        label_widget.setStyleSheet("font-weight: bold;")
        layout.addWidget(label_widget)

        url_widget = QLabel(url)
        url_widget.setStyleSheet("color: #3498db; font-size: 11px;")
        layout.addWidget(url_widget, 1)

        open_btn = QPushButton(T("dirs_open"))
        _open_icon = QIcon.fromTheme("internet-web-browser")
        if not _open_icon.isNull():
            open_btn.setIcon(_open_icon)
        open_btn.clicked.connect(lambda: open_url(url))
        open_btn.setProperty("linkBtn", True)
        layout.addWidget(open_btn)

        row.setProperty("linkRow", True)
        return row

    def create_bottom_bar(self) -> QWidget:
        bar = QWidget()
        bar.setProperty("bottomBar", True)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 6, 12, 6)

        self.news_btn = QPushButton(T("btn_news"))
        _news_icon = QIcon.fromTheme("news")
        if _news_icon.isNull():
            _news_icon = QIcon.fromTheme("applications-internet")
        if not _news_icon.isNull():
            self.news_btn.setIcon(_news_icon)
        self.news_btn.setProperty("newsBtn", True)
        self.news_btn.clicked.connect(lambda: open_url(APP_NEWS))
        layout.addWidget(self.news_btn)

        # Botón Instalar con traducción o fallback correcto
        _, installer_cmd = detect_live_mode()
        if installer_cmd:
            install_text = T("btn_install") if T("btn_install") != "btn_install" else "Instalar"
            self.install_btn = QPushButton(install_text)
            _install_icon = QIcon.fromTheme("drive-optical")
            if _install_icon.isNull():
                _install_icon = QIcon.fromTheme("system-software-install")
            if not _install_icon.isNull():
                self.install_btn.setIcon(_install_icon)
            self.install_btn.setProperty("installBtn", True)
            self.install_btn.clicked.connect(lambda: launch_app(installer_cmd))
            layout.addWidget(self.install_btn)

        layout.addStretch()

        self.autostart_label = QLabel(T("autostart_label"))
        layout.addWidget(self.autostart_label)

        self.autostart_check = QCheckBox()
        self.autostart_check.setChecked(autostart_is_enabled())
        self.autostart_check.toggled.connect(self.on_autostart_toggled)
        layout.addWidget(self.autostart_check)

        layout.addStretch()

        self.close_btn = QPushButton(T("btn_close"))
        _close_icon = QIcon.fromTheme("window-close")
        if _close_icon.isNull():
            _close_icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton)
        if not _close_icon.isNull():
            self.close_btn.setIcon(_close_icon)
        self.close_btn.setProperty("closeBtn", True)
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)

        return bar

    def on_autostart_toggled(self, checked: bool):
        if checked:
            autostart_enable()
        else:
            autostart_disable()

    def refresh_ui(self):
        self.setWindowTitle(APP_NAME)
        self.menu_btn.setToolTip(T("tt_settings"))

        self.news_btn.setText(T("btn_news"))
        self.autostart_label.setText(T("autostart_label"))
        self.close_btn.setText(T("btn_close"))

        current_index = self.tab_widget.currentIndex()

        self.tab_widget.clear()
        self.tab_widget.addTab(self.create_home_tab(), T("tab_home"))
        self.tab_widget.addTab(self.create_tools_tab(), T("tab_tools"))
        self.tab_widget.addTab(self.create_newuser_tab(), T("tab_newuser"))
        self.tab_widget.addTab(self.create_other_tab(), T("tab_other"))
        self.tab_widget.addTab(self.create_support_tab(), T("tab_support"))

        self._setup_corner_widgets()
        self.tab_widget.setCurrentIndex(min(current_index, self.tab_widget.count() - 1))

    def apply_styles(self):
        qss_path = find_asset("style.qss") or os.path.join(BASE_DIR, "style.qss")
        base_qss = ""
        if os.path.isfile(qss_path):
            try:
                with open(qss_path, "r", encoding="utf-8") as f:
                    base_qss = f.read()
            except OSError:
                pass

        extra_qss = """
            QWidget[welcomeSidebar="true"] {
                background-color: palette(highlight);
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
            }
            QPushButton[menuBtn="true"] {
                background-color: transparent;
                border: none;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
                padding: 0px 8px;
                min-width: 32px;
                min-height: 24px;
                color: palette(button-text);
            }
            QPushButton[menuBtn="true"]:hover {
                background-color: rgba(128,128,128,0.15);
            }
            QWidget[liveHeader="true"] {
                background-color: palette(window);
                border-bottom: 1px solid palette(mid);
            }
            QPushButton[liveCard="true"] {
                background-color: rgba(0,0,0,0.04);
                border: 1px solid palette(mid);
                border-radius: 10px;
                padding: 12px;
            }
            QPushButton[liveCard="true"]:hover {
                background-color: rgba(52,152,219,0.1);
                border-color: palette(highlight);
            }
            QPushButton[liveCard="true"]:disabled {
                background-color: rgba(0,0,0,0.02);
                color: palette(disabled-text);
                border-color: palette(mid);
            }
            QPushButton[toolCard="true"] {
                background-color: rgba(0,0,0,0.05);
                border: 1px solid palette(mid);
                border-radius: 10px;
                padding: 12px;
            }
            QPushButton[toolCard="true"]:hover {
                background-color: rgba(52,152,219,0.1);
                border-color: #3498db;
            }
            QWidget[infoCard="true"], QWidget[linkRow="true"] {
                background-color: rgba(0,0,0,0.03);
                border-radius: 6px;
            }
            QPushButton[linkBtn="true"] {
                background-color: transparent;
                border: 1px solid #3498db;
                border-radius: 4px;
                padding: 4px 12px;
                color: #3498db;
            }
            QPushButton[linkBtn="true"]:hover {
                background-color: #3498db;
                color: white;
            }
            QLabel[chip="true"] {
                background-color: rgba(0,0,0,0.08);
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 11px;
                max-height: 40px;
            }
            QPushButton[social="true"] {
                background-color: transparent;
                border: 1px solid palette(mid);
                border-radius: 16px;
                padding: 6px 16px;
                min-width: 80px;
            }
            QPushButton[social="true"]:hover {
                background-color: palette(highlight);
                color: palette(highlighted-text);
                border-color: palette(highlight);
            }
            QWidget[bottomBar="true"] {
                background-color: palette(window);
                border-top: 1px solid palette(mid);
            }
            QPushButton[newsBtn="true"], QPushButton[closeBtn="true"] {
                background-color: transparent;
                border: 1px solid palette(mid);
                border-radius: 5px;
                padding: 5px 12px;
            }
            QPushButton[closeBtn="true"]:hover {
                background-color: #e74c3c;
                border-color: #e74c3c;
                color: white;
            }
            QPushButton[newsBtn="true"]:hover {
                background-color: #3498db;
                border-color: #3498db;
                color: white;
            }
            QPushButton[installBtn="true"] {
                background-color: #e74c3c;
                border: none;
                border-radius: 5px;
                padding: 5px 12px;
                color: white;
            }
            QPushButton[installBtn="true"]:hover {
                background-color: #c0392b;
            }
            QWidget[kofiCard="true"] {
                background-color: rgba(41, 171, 224, 0.08);
                border: 1px solid rgba(41, 171, 224, 0.35);
                border-radius: 10px;
            }
            QWidget[kofiDestCard="true"] {
                background-color: rgba(0, 0, 0, 0.04);
                border: 1px solid palette(mid);
                border-radius: 8px;
            }
            QWidget[kofiDestCard="true"]:hover {
                background-color: rgba(41, 171, 224, 0.10);
                border-color: rgba(41, 171, 224, 0.5);
            }
            QPushButton[kofiBtn="true"] {
                background-color: #29ABE0;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                color: white;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton[kofiBtn="true"]:hover {
                background-color: #1e8aba;
            }
            QPushButton[kofiBtnMain="true"] {
                background-color: #29ABE0;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                color: white;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton[kofiBtnMain="true"]:hover {
                background-color: #1e8aba;
            }
        """
        self.setStyleSheet(base_qss + extra_qss)