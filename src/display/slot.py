from __future__ import annotations

from typing import Optional

import pygame

from src.signals.decoder import GaugeSignal, SignalState

# Color palette — all RGB tuples
_BG_NORMAL   = (18,  18,  18)
_BG_WARNING  = (45,  30,   0)
_BG_CRITICAL = (45,   0,   0)
_BG_MUTED    = (18,  18,  18)

_TEXT_LABEL    = (120, 120, 120)
_TEXT_NORMAL   = (220, 220, 220)
_TEXT_WARNING  = (255, 165,   0)  # amber
_TEXT_CRITICAL = (220,  50,  50)  # red
_TEXT_MUTED    = ( 70,  70,  70)

_DIVIDER = (40, 40, 40)

# Font sizes (pixels) — chosen for readability at 280 px tall
_FONT_LABEL = 26
_FONT_VALUE = 90
_FONT_UNIT  = 30


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

        pygame.draw.rect(surface, bg, self.rect)
        pygame.draw.line(surface, _DIVIDER, self.rect.topright, self.rect.bottomright, 1)

        cx = self.rect.centerx

        # Label row (top)
        label_surf = self._label_font.render(self.signal.label, True, _TEXT_LABEL)
        surface.blit(label_surf, label_surf.get_rect(centerx=cx, top=self.rect.top + 18))

        # Value row (center)
        if state == SignalState.WAITING:
            value_str, unit_str = "—", ""     # em dash
        elif state == SignalState.NO_SIGNAL:
            value_str, unit_str = "NO SIGNAL", ""
        elif state == SignalState.FAULT:
            value_str, unit_str = "FAULT", ""
        else:
            value_str = f"{value:.0f}" if value is not None else "—"
            unit_str = self.signal.unit

        value_surf = self._value_font.render(value_str, True, text_color)
        value_rect = value_surf.get_rect(centerx=cx, centery=self.rect.centery + 12)
        surface.blit(value_surf, value_rect)

        if unit_str:
            unit_surf = self._unit_font.render(unit_str, True, text_color)
            surface.blit(
                unit_surf,
                unit_surf.get_rect(left=value_rect.right + 6, centery=value_rect.centery),
            )
