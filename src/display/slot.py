from __future__ import annotations

import os
from typing import Optional

import pygame

_FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts")
_BITTYPIX  = os.path.join(_FONTS_DIR, "Bittypix Monospace.otf")

from src.signals.decoder import GaugeSignal, SignalState

# Color palette — all RGB tuples
_BG_NORMAL   = ( 18,  18,  18)
_BG_WARNING  = ( 90,  55,   0)  # dark amber — clearly distinct from normal
_BG_CRITICAL = (110,   0,   0)  # dark red  — clearly distinct from normal
_BG_MUTED    = ( 18,  18,  18)

_TEXT_LABEL    = (120, 120, 120)
_TEXT_NORMAL   = (220, 220, 220)
_TEXT_WARNING  = (255, 180,   0)  # bright amber
_TEXT_CRITICAL = (255,  60,  60)  # bright red
_TEXT_MUTED    = ( 70,  70,  70)

_DIVIDER = (40, 40, 40)

# Font sizes (pixels) — chosen for readability at 280 px tall
_FONT_LABEL = 24
_FONT_VALUE = 64
_FONT_UNIT  = 26

# Vertical layout constants
_PAD_TOP    = 14   # pixels from slot top to label top
_LABEL_GAP  = 10   # pixels between label bottom and value area top
_PAD_BOTTOM = 14   # pixels reserved at slot bottom


class DisplaySlot:
    """Renders one GaugeSignal into a fixed rectangular region of the pygame surface.

    Fonts are initialised lazily on first render so this class can be constructed
    before pygame.init() has been called.
    """

    def __init__(self, rect: pygame.Rect, signal: GaugeSignal) -> None:
        self.rect = rect
        self.signal = signal
        self._label_font: Optional[pygame.font.Font] = None
        self._value_font: Optional[pygame.font.Font] = None
        self._unit_font:  Optional[pygame.font.Font] = None

    def _ensure_fonts(self) -> None:
        if self._label_font is None:
            if os.path.exists(_BITTYPIX):
                self._label_font = pygame.font.Font(_BITTYPIX, _FONT_LABEL)
                self._value_font = pygame.font.Font(_BITTYPIX, _FONT_VALUE)
                self._unit_font  = pygame.font.Font(_BITTYPIX, _FONT_UNIT)
            else:
                self._label_font = pygame.font.SysFont("monospace", _FONT_LABEL, bold=False)
                self._value_font = pygame.font.SysFont("monospace", _FONT_VALUE, bold=True)
                self._unit_font  = pygame.font.SysFont("monospace", _FONT_UNIT,  bold=False)

    def render(self, surface: pygame.Surface) -> None:
        self._ensure_fonts()
        assert self._label_font and self._value_font and self._unit_font

        value, state = self.signal.snapshot()

        # Choose background and text colors from state
        if state == SignalState.WARNING:
            bg, text_color = _BG_WARNING, _TEXT_WARNING
        elif state == SignalState.CRITICAL:
            bg, text_color = _BG_CRITICAL, _TEXT_CRITICAL
        elif state in (SignalState.WAITING, SignalState.NO_SIGNAL, SignalState.FAULT):
            bg, text_color = _BG_MUTED, _TEXT_MUTED
        else:  # NORMAL
            bg, text_color = _BG_NORMAL, _TEXT_NORMAL

        cx = self.rect.centerx

        # Label row — pinned near the top
        label_surf = self._label_font.render(self.signal.label, True, _TEXT_LABEL)
        label_rect = label_surf.get_rect(centerx=cx, top=self.rect.top + _PAD_TOP)

        # Value area — everything below the label down to the bottom padding
        value_area_top    = label_rect.bottom + _LABEL_GAP
        value_area_bottom = self.rect.bottom - _PAD_BOTTOM
        value_area_cy     = (value_area_top + value_area_bottom) // 2

        # Value row (center of value area)
        if state == SignalState.WAITING:
            value_str, unit_str = "—", ""     # em dash
        elif state == SignalState.NO_SIGNAL:
            value_str, unit_str = "NO SIG", ""
        elif state == SignalState.FAULT:
            value_str, unit_str = "FAULT", ""
        else:
            value_str = f"{value:.0f}" if value is not None else "—"
            unit_str = self.signal.unit

        # Clip all drawing to this slot so nothing bleeds into adjacent slots
        surface.set_clip(self.rect)

        pygame.draw.rect(surface, bg, self.rect)
        pygame.draw.line(surface, _DIVIDER, self.rect.topright, self.rect.bottomright, 1)

        surface.blit(label_surf, label_rect)

        value_surf = self._value_font.render(value_str, True, text_color)
        value_rect = value_surf.get_rect(centerx=cx, centery=value_area_cy)
        surface.blit(value_surf, value_rect)

        if unit_str:
            unit_surf = self._unit_font.render(unit_str, True, text_color)
            surface.blit(
                unit_surf,
                unit_surf.get_rect(left=value_rect.right + 4, centery=value_rect.centery),
            )

        surface.set_clip(None)
