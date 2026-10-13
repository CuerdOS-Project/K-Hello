#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
theme.py — Métricas de layout para K-Hello.
Los estilos visuales vienen del tema nativo del sistema (QPalette).
"""

# Verde de marca fijo (no depende del tema claro/oscuro del sistema):
# se usa como fondo de la cabecera de la ventana Live para que el
# banner/logo de CuerdOS siempre resulte legible, sea cual sea el modo.
BRAND_GREEN = "#153E2C"

# Acento del botón "Instalar": mismo verde usado en la tarjeta de instalar
# del modo Live (live_window.py), para que la acción de instalar se
# reconozca por su color en cualquiera de las dos ventanas.
INSTALL_ACCENT = {
    "base":     "#1F9D6E",
    "hover":    "#24B67F",
    "pressed":  "#1A8760",
    "border":   "#167A54",
    "disabled": "#2A4A3D",
    "text":     "#F2FBF6",
}

METRIC = {
    "sidebar_width":   180,
    "radius_card":      12,
    "radius_btn":        8,
    "nav_btn_height":   44,
    "page_margin":      32,
}

# =============================================================================
# Paleta de la página de Inicio (rediseño)
# =============================================================================
# Colores fijos (no dependen del tema del sistema) para los botones de
# acción de la nueva página de Inicio. Cada botón usa uno de estos cinco
# colores; el color de icono/texto se elige automáticamente según el
# contraste (ver get_home_button_colors en widgets.py).

HOME_COLORS = {
    "purple": "#6A3FC0",   # morado
    "lime":   "#9ABF2E",   # verde lima (oscurecido)
    "orange": "#E6752E",   # naranja (oscurecido)
    "mint":   "#466755",   # verde oscuro (antes menta brillante)
    "navy":   "#16223A",   # azul nocturno
    "pink":   "#FD9593",   # rosa claro (Más software)
}

# Colores de icono/texto oscuros vs. claros usados sobre HOME_COLORS.
HOME_FG_DARK  = "#1B2233"
HOME_FG_LIGHT = "#FFFFFF"

# Fondos que son lo bastante claros como para necesitar texto/iconos oscuros.
# (vacío a propósito: todos los botones de Inicio usan icono/texto blanco,
# incluido el rosa, para mantener buen contraste sobre la paleta oscura).
HOME_LIGHT_BACKGROUNDS = set()

# Tamaños "estándar" de imagen para la página de Inicio: todas las imágenes
# de personajes comparten esta relación de aspecto (1:1.46, propia del arte
# de los personajes); el valor aquí actúa como tope máximo de escalado
# (el widget se adapta hacia abajo si hay menos espacio), y el logo de la
# distro se ajusta a esta otra caja manteniendo proporción.
HOME_CHARACTER_SIZE = (430, 628)
HOME_LOGO_BOX        = (240, 84)
