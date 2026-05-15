from __future__ import annotations

import os

import pygame

from src.display.slot import DisplaySlot
from src.signals.decoder import GaugeSignal

_WIDTH  = 1424
_HEIGHT = 280
_FPS    = 30
_BG     = (18, 18, 18)

# Three equal vertical bands per display-contract.md
_SLOT_RECTS = [
    pygame.Rect(  0, 0, 474, _HEIGHT),
    pygame.Rect(475, 0, 474, _HEIGHT),
    pygame.Rect(950, 0, 474, _HEIGHT),
]


class Renderer:
    """pygame-based renderer for the 1424×280 landscape gauge display.

    Pass windowed=True (--windowed flag) to open a desktop window on macOS for
    local development. Without it the renderer targets /dev/fb0 on the CM5.
    """

    def __init__(
        self,
        signals: dict[str, GaugeSignal],
        windowed: bool = False,
    ) -> None:
        self._signals = signals
        self._windowed = windowed
        self._slots: list[DisplaySlot] = []
        self._clock: pygame.time.Clock | None = None
        self._running = False

    def setup(self) -> None:
        pygame.init()
        pygame.display.set_caption("Tacoma Tow Gauge")

        if self._windowed:
            pygame.display.set_mode((_WIDTH, _HEIGHT))
        else:
            os.putenv("SDL_FBDEV", os.environ.get("SDL_FBDEV", "/dev/fb0"))
            os.putenv("SDL_VIDEODRIVER", os.environ.get("SDL_VIDEODRIVER", "fbcon"))
            pygame.display.set_mode((_WIDTH, _HEIGHT), pygame.FULLSCREEN | pygame.NOFRAME)

        self._clock = pygame.time.Clock()

        signal_list = list(self._signals.values())
        for i, rect in enumerate(_SLOT_RECTS):
            if i < len(signal_list):
                self._slots.append(DisplaySlot(rect, signal_list[i]))

    def run(self) -> None:
        surface = pygame.display.get_surface()
        self._running = True

        while self._running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self._running = False

            surface.fill(_BG)
            for slot in self._slots:
                slot.render(surface)

            pygame.display.flip()
            assert self._clock is not None
            self._clock.tick(_FPS)

    def stop(self) -> None:
        self._running = False
        pygame.quit()
