#!/usr/bin/env python3
"""Native 640x480 performance interface for the Pocketcosm Pd engine."""

from __future__ import annotations

import math
import os
import socket
import sys
import time
from dataclasses import dataclass

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_MOUSE_TOUCH_EVENTS", "0")
os.environ.setdefault("SDL_TOUCH_MOUSE_EVENTS", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "x11")

import pygame


WIDTH, HEIGHT = 640, 480
PD_HOST, PD_PORT = "127.0.0.1", 9001
UI_PORT = 9002

BG = (12, 14, 18)
PANEL = (25, 29, 36)
PANEL_2 = (34, 39, 48)
LINE = (65, 73, 86)
TEXT = (235, 239, 244)
MUTED = (145, 154, 169)
CYAN = (74, 205, 224)
GREEN = (79, 219, 145)
RED = (245, 82, 96)
ORANGE = (244, 157, 65)
YELLOW = (245, 205, 79)
PURPLE = (157, 125, 232)
PINK = (238, 103, 167)

MODES = ("CLOUD", "GLITCH", "ARP", "REVERSE")

# Each engine (mode) exposes three variants. Selecting a variant applies a
# curated parameter macro for that engine — the Microcosm's "effect + variation"
# model. 4 banks x 3 = 12 selectable effect characters.
VARIANT_NAMES = (
    ("DRIFT", "SHIMMER", "DENSE"),
    ("STUTTER", "SCATTER", "CHOP"),
    ("UP", "OCTAVES", "WIDE"),
    ("SWELL", "LONG", "WARP"),
)

VARIANTS = (
    (  # CLOUD
        {"grain": 320, "texture": 0.70, "density": 0.40, "feedback": 0.70, "space": 0.45, "tone": 100, "pitch": 0, "pitchmix": 0.0},
        {"grain": 120, "texture": 0.55, "density": 0.75, "feedback": 0.80, "space": 0.60, "tone": 112, "pitch": 12, "pitchmix": 0.4},
        {"grain": 600, "texture": 0.85, "density": 0.95, "feedback": 0.85, "space": 0.50, "tone": 96, "pitch": 0, "pitchmix": 0.0},
    ),
    (  # GLITCH
        {"grain": 90, "density": 0.60, "bpm": 120, "texture": 0.40, "feedback": 0.60, "space": 0.30, "tone": 105},
        {"grain": 60, "density": 0.85, "bpm": 140, "texture": 0.80, "feedback": 0.70, "space": 0.45, "tone": 100},
        {"grain": 200, "density": 0.40, "bpm": 100, "texture": 0.50, "feedback": 0.50, "space": 0.35, "tone": 92},
    ),
    (  # ARP
        {"grain": 180, "bpm": 120, "density": 0.60, "tone": 105, "pitch": 0, "feedback": 0.60, "space": 0.50},
        {"grain": 150, "bpm": 128, "density": 0.70, "tone": 110, "pitch": 12, "pitchmix": 0.3, "feedback": 0.65, "space": 0.55},
        {"grain": 240, "bpm": 96, "density": 0.50, "tone": 100, "pitch": -12, "feedback": 0.70, "space": 0.60},
    ),
    (  # REVERSE
        {"grain": 300, "delay": 600, "texture": 0.60, "feedback": 0.70, "space": 0.55, "tone": 100},
        {"grain": 700, "delay": 1200, "texture": 0.70, "feedback": 0.80, "space": 0.60, "tone": 96},
        {"grain": 400, "delay": 800, "texture": 0.50, "feedback": 0.75, "space": 0.50, "tone": 104, "pitch": -12, "pitchmix": 0.4},
    ),
)


DEFAULTS = {
    "demo": 1.0,
    "freeze": 0.0,
    "bypass": 0.0,
    "mode": 0.0,
    "grain": 220.0,
    "delay": 480.0,
    "bpm": 100.0,
    "pitch": 0.0,
    "pitchmix": 0.0,
    "texture": 0.55,
    "density": 0.5,
    "onset": 0.5,
    "tone": 100.0,
    "feedback": 0.72,
    "space": 0.35,
    "mix": 0.75,
    "loop_record": 0.0,
    "loop_play": 0.0,
    "loop_reverse": 0.0,
    "loop_route": 0.0,
    "loop_ms": 1000.0,
    "loop_phase": 0.0,
    "undo_valid": 0.0,
    "overdub_active": 0.0,
    "preset_slot": 0.0,
    "inmeter": -100.0,
    "outmeter": -100.0,
    "clip": 0.0,
}


@dataclass(frozen=True)
class SliderSpec:
    key: str
    label: str
    low: float
    high: float
    color: tuple[int, int, int]
    unit: str = "%"
    curve: str = "linear"


PERFORM_SLIDERS = (
    SliderSpec("delay", "MEMORY", 20, 6000, PURPLE, "ms", "log"),
    SliderSpec("feedback", "FEEDBACK", 0, 0.97, ORANGE),
    SliderSpec("space", "SPACE", 0, 1, PURPLE),
    SliderSpec("mix", "DRY / WET", 0, 1, GREEN),
)

EDIT_SLIDERS = (
    SliderSpec("grain", "GRAIN", 40, 1000, CYAN, "ms", "log"),
    SliderSpec("bpm", "TEMPO", 40, 200, YELLOW, "bpm"),
    SliderSpec("pitch", "PITCH", -24, 24, CYAN, "st"),
    SliderSpec("pitchmix", "PITCH MIX", 0, 1, (82, 145, 244)),
    SliderSpec("tone", "TONE", 50, 120, CYAN, "midi"),
    SliderSpec("onset", "ONSET", 0, 1, PINK),
    SliderSpec("texture", "TEXTURE", 0, 1, PINK),
    SliderSpec("density", "DENSITY", 0, 1, PINK),
)


class PocketcosmUI:
    def __init__(self) -> None:
        pygame.init()
        pygame.event.set_allowed(
            [
                pygame.QUIT,
                pygame.KEYDOWN,
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEBUTTONUP,
                pygame.MOUSEMOTION,
            ]
        )
        flags = pygame.FULLSCREEN | pygame.NOFRAME
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        pygame.display.set_caption("Pocketcosm")
        print(
            f"Pocketcosm UI: SDL driver={pygame.display.get_driver()} "
            f"size={self.screen.get_size()}",
            flush=True,
        )
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()
        self.font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        self.bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        self.mono_path = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
        self.fonts = {
            12: pygame.font.Font(self.font_path, 12),
            14: pygame.font.Font(self.font_path, 14),
            16: pygame.font.Font(self.font_path, 16),
            18: pygame.font.Font(self.bold_path, 18),
            22: pygame.font.Font(self.bold_path, 22),
            28: pygame.font.Font(self.bold_path, 28),
            38: pygame.font.Font(self.bold_path, 38),
        }
        self.state = dict(DEFAULTS)
        self.page = 0
        self.preset_bank = 0
        self.variant = 0
        self.running = True
        self.drag: tuple[str, pygame.Rect, SliderSpec | None] | None = None
        self.press_target: str | None = None
        self.press_started = 0.0
        self.clear_progress = 0.0
        self.last_rx = 0.0
        self.last_sync = 0.0
        self.hit_until = 0.0
        self.notice = ""
        self.notice_until = 0.0
        self.tap_times: list[float] = []
        self.loop_epoch = time.monotonic()
        self.record_epoch = time.monotonic()
        self.previous = dict(self.state)

        self.tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.rx.bind(("127.0.0.1", UI_PORT))
        self.rx.setblocking(False)

    def text(
        self,
        value: str,
        pos: tuple[int, int],
        size: int = 14,
        color: tuple[int, int, int] = TEXT,
        anchor: str = "topleft",
    ) -> pygame.Rect:
        surface = self.fonts[size].render(value, True, color)
        rect = surface.get_rect()
        setattr(rect, anchor, pos)
        self.screen.blit(surface, rect)
        return rect

    @staticmethod
    def rounded(
        surface: pygame.Surface,
        rect: pygame.Rect,
        color: tuple[int, int, int],
        radius: int = 9,
        width: int = 0,
    ) -> None:
        pygame.draw.rect(surface, color, rect, width, border_radius=radius)

    def send(self, message: str) -> None:
        try:
            self.tx.sendto((message + ";\n").encode("ascii"), (PD_HOST, PD_PORT))
        except OSError:
            pass

    def set_value(self, key: str, value: float) -> None:
        value = float(value)
        self.state[key] = value
        self.send(f"set {key} {value:.6g}")
        self.note_transition(key, value)

    def action(self, key: str) -> None:
        self.send(f"action {key}")

    def toggle(self, key: str) -> None:
        self.set_value(key, 0 if self.state.get(key, 0) >= 0.5 else 1)

    def sync(self) -> None:
        self.send("sync")
        self.last_sync = time.monotonic()

    def receive(self) -> None:
        while True:
            try:
                packet = self.rx.recv(4096).decode("utf-8", "ignore")
            except BlockingIOError:
                break
            except OSError:
                break
            self.last_rx = time.monotonic()
            for raw in packet.replace("\n", ";").split(";"):
                parts = raw.strip().split()
                if len(parts) < 2:
                    continue
                key = parts[0]
                try:
                    value = float(parts[1])
                except ValueError:
                    continue
                if key == "hit":
                    self.hit_until = time.monotonic() + 0.14
                else:
                    self.state[key] = value
                    self.note_transition(key, value)

    def note_transition(self, key: str, value: float) -> None:
        old = self.previous.get(key, value)
        if key == "loop_play" and value >= 0.5 and old < 0.5:
            self.loop_epoch = time.monotonic()
        if key == "loop_record" and value >= 0.5 and old < 0.5:
            self.record_epoch = time.monotonic()
        self.previous[key] = value

    @staticmethod
    def normalized(spec: SliderSpec, value: float) -> float:
        value = max(spec.low, min(spec.high, value))
        if spec.curve == "log":
            return math.log(value / spec.low) / math.log(spec.high / spec.low)
        return (value - spec.low) / (spec.high - spec.low)

    @staticmethod
    def denormalized(spec: SliderSpec, amount: float) -> float:
        amount = max(0.0, min(1.0, amount))
        if spec.curve == "log":
            return spec.low * ((spec.high / spec.low) ** amount)
        return spec.low + amount * (spec.high - spec.low)

    def value_text(self, spec: SliderSpec) -> str:
        value = self.state[spec.key]
        if spec.unit == "%":
            return f"{round(value * 100):d}%"
        if spec.unit in ("ms", "bpm", "midi"):
            return f"{round(value):d} {spec.unit}"
        if spec.unit == "st":
            return f"{value:+.0f} st"
        return f"{value:.2f}"

    def button(
        self,
        rect: pygame.Rect,
        label: str,
        active: bool = False,
        color: tuple[int, int, int] = CYAN,
        sublabel: str | None = None,
        disabled: bool = False,
    ) -> None:
        fill = color if active and not disabled else PANEL_2
        border = color if not disabled else LINE
        self.rounded(self.screen, rect, fill, 10)
        self.rounded(self.screen, rect, border, 10, 2)
        label_color = BG if active and not disabled else (MUTED if disabled else TEXT)
        self.text(label, rect.center, 16, label_color, "center")
        if sublabel:
            self.text(sublabel, (rect.centerx, rect.bottom - 8), 12, label_color, "midbottom")

    def slider(self, rect: pygame.Rect, spec: SliderSpec) -> None:
        value = self.state[spec.key]
        amount = self.normalized(spec, value)
        self.rounded(self.screen, rect, PANEL, 9)
        fill = rect.copy()
        fill.width = max(8, round(rect.width * amount))
        self.rounded(self.screen, fill, spec.color, 9)
        self.text(spec.label, (rect.x + 12, rect.y + 8), 12, TEXT)
        self.text(self.value_text(spec), (rect.right - 10, rect.y + 7), 14, TEXT, "topright")

    def header(self) -> None:
        pygame.draw.rect(self.screen, PANEL, (0, 0, WIDTH, 50))
        self.text("POCKETCOSM", (16, 25), 22, TEXT, "midleft")
        mode = MODES[int(self.state["mode"]) % 4]
        self.text(mode, (310, 17), 14, CYAN, "midleft")
        self.text(f'{round(self.state["bpm"]):d} BPM', (310, 34), 12, MUTED, "midleft")

        connected = time.monotonic() - self.last_rx < 2.0
        pygame.draw.circle(self.screen, GREEN if connected else RED, (405, 25), 5)
        self.draw_meter(pygame.Rect(425, 12, 76, 11), self.state["inmeter"], GREEN, "IN")
        self.draw_meter(pygame.Rect(425, 29, 76, 11), self.state["outmeter"], CYAN, "OUT")
        clip = self.state["clip"] >= 0.5
        self.text("CLIP", (508, 25), 12, RED if clip else MUTED, "midleft")
        if time.monotonic() < self.hit_until:
            pygame.draw.circle(self.screen, PINK, (555, 25), 8)
        else:
            pygame.draw.circle(self.screen, LINE, (555, 25), 6, 2)

        exit_rect = pygame.Rect(578, 6, 50, 38)
        self.button(exit_rect, "EXIT", False, RED)

    def draw_meter(
        self,
        rect: pygame.Rect,
        db: float,
        color: tuple[int, int, int],
        label: str,
    ) -> None:
        self.text(label, (rect.x - 5, rect.centery), 12, MUTED, "midright")
        self.rounded(self.screen, rect, (8, 10, 13), 4)
        amount = max(0.0, min(1.0, (db + 60.0) / 60.0))
        if amount:
            fill = rect.copy()
            fill.width = max(3, round(rect.width * amount))
            self.rounded(self.screen, fill, RED if db > -1 else color, 4)

    def apply_variant(self, mode: int, variant: int) -> None:
        self.set_value("mode", mode)
        for key, value in VARIANTS[mode][variant].items():
            self.set_value(key, value)
        self.variant = variant

    def mode_row(self) -> None:
        gap = 6
        width = (608 - gap * 3) // 4
        for index, label in enumerate(MODES):
            rect = pygame.Rect(16 + index * (width + gap), 58, width, 34)
            self.button(rect, label, int(self.state["mode"]) == index, CYAN)
        mode = int(self.state["mode"]) % 4
        w3 = (608 - gap * 2) // 3
        for i, label in enumerate(VARIANT_NAMES[mode]):
            rect = pygame.Rect(16 + i * (w3 + gap), 96, w3, 20)
            self.button(rect, label, int(self.variant) == i, PURPLE)

    def xy_specs(self) -> tuple[SliderSpec, SliderSpec]:
        mode = int(self.state["mode"]) % 4
        if mode == 1:
            return (
                SliderSpec("grain", "SLICE", 40, 350, CYAN, "ms", "log"),
                SliderSpec("density", "DENSITY", 0, 1, PINK),
            )
        if mode == 2:
            return (
                SliderSpec("tone", "TONE", 50, 120, CYAN, "midi"),
                SliderSpec("density", "INTENSITY", 0, 1, PINK),
            )
        if mode == 3:
            return (
                SliderSpec("grain", "FRAGMENT", 120, 1000, CYAN, "ms", "log"),
                SliderSpec("delay", "MEMORY", 20, 6000, PURPLE, "ms", "log"),
            )
        return (
            SliderSpec("texture", "TEXTURE", 0, 1, PINK),
            SliderSpec("density", "DENSITY", 0, 1, PINK),
        )

    def perform_page(self) -> None:
        self.mode_row()
        pad = pygame.Rect(16, 122, 378, 204)
        self.rounded(self.screen, pad, PANEL, 12)
        self.rounded(self.screen, pad, LINE, 12, 2)
        for step in range(1, 4):
            x = pad.x + pad.width * step // 4
            y = pad.y + pad.height * step // 4
            pygame.draw.line(self.screen, (42, 48, 58), (x, pad.y + 1), (x, pad.bottom - 1))
            pygame.draw.line(self.screen, (42, 48, 58), (pad.x + 1, y), (pad.right - 1, y))
        x_spec, y_spec = self.xy_specs()
        px = pad.x + int(self.normalized(x_spec, self.state[x_spec.key]) * pad.width)
        py = pad.bottom - int(self.normalized(y_spec, self.state[y_spec.key]) * pad.height)
        pygame.draw.line(self.screen, (70, 79, 92), (px, pad.y), (px, pad.bottom))
        pygame.draw.line(self.screen, (70, 79, 92), (pad.x, py), (pad.right, py))
        pygame.draw.circle(self.screen, PINK, (px, py), 15)
        pygame.draw.circle(self.screen, TEXT, (px, py), 15, 2)
        self.text(f"{x_spec.label}  →", (pad.x + 12, pad.bottom - 10), 12, MUTED, "bottomleft")
        self.text(y_spec.label, (pad.x + 10, pad.y + 10), 12, MUTED)

        for row, spec in enumerate(PERFORM_SLIDERS):
            self.slider(pygame.Rect(408, 110 + row * 57, 216, 46), spec)

        actions = (
            ("freeze", "FREEZE", CYAN),
            ("loop_record", "CAPTURE", RED),
            ("bypass", "BYPASS", YELLOW),
        )
        for index, (key, label, color) in enumerate(actions):
            rect = pygame.Rect(16 + index * 204, 348, 192, 62)
            self.button(rect, label, self.state[key] >= 0.5, color)

    def loop_phase(self) -> float:
        duration = max(0.1, self.state["loop_ms"] / 1000.0)
        if self.state["loop_record"] >= 0.5:
            return min(1.0, (time.monotonic() - self.record_epoch) / 60.0)
        if self.state["loop_play"] < 0.5:
            return 0.0
        return max(0.0, min(1.0, self.state["loop_phase"]))

    def loop_page(self) -> None:
        duration = (
            time.monotonic() - self.record_epoch
            if self.state["loop_record"] >= 0.5
            else self.state["loop_ms"] / 1000.0
        )
        self.text("PHRASE LOOP", (16, 68), 18)
        self.text(f"{duration:05.1f} SEC", (624, 69), 16, MUTED, "topright")
        progress = pygame.Rect(16, 96, 608, 12)
        self.rounded(self.screen, progress, PANEL_2, 6)
        fill = progress.copy()
        fill.width = max(6, round(progress.width * self.loop_phase()))
        self.rounded(self.screen, fill, RED if self.state["loop_record"] else GREEN, 6)

        record_rect = pygame.Rect(16, 124, 292, 126)
        recording = self.state["loop_record"] >= 0.5
        self.button(
            record_rect,
            "STOP" if recording else "RECORD",
            recording,
            RED,
            "MAX 60 SECONDS",
        )
        play_rect = pygame.Rect(320, 124, 146, 126)
        self.button(play_rect, "PLAY", self.state["loop_play"] >= 0.5, GREEN)
        dub_rect = pygame.Rect(478, 124, 146, 126)
        self.button(
            dub_rect,
            "OVERDUB",
            self.state["overdub_active"] >= 0.5,
            ORANGE,
        )

        controls = (
            ("undo", "UNDO", CYAN),
            ("reverse", "REVERSE", PURPLE),
            ("route", "POST FX" if self.state["loop_route"] else "PRE FX", CYAN),
            ("clear", "HOLD CLEAR", YELLOW),
        )
        for index, (key, label, color) in enumerate(controls):
            rect = pygame.Rect(16 + index * 152, 266, 140, 72)
            active = (
                key == "reverse" and self.state["loop_reverse"] >= 0.5
            ) or (key == "route" and self.state["loop_route"] >= 0.5)
            disabled = key == "undo" and self.state["undo_valid"] < 0.5
            self.button(rect, label, active, color, disabled=disabled)
            if key == "clear" and self.clear_progress > 0:
                bar = pygame.Rect(rect.x + 6, rect.bottom - 9, rect.width - 12, 4)
                pygame.draw.rect(self.screen, LINE, bar)
                bar.width = round(bar.width * self.clear_progress)
                pygame.draw.rect(self.screen, YELLOW, bar)

        source = "POST-EFFECTS" if self.state["loop_route"] else "DRY INPUT"
        status = "RECORDING"
        color = RED
        if self.state["overdub_active"] >= 0.5:
            status, color = "OVERDUBBING", ORANGE
        elif self.state["loop_play"] >= 0.5:
            status, color = "PLAYING", GREEN
        elif self.state["loop_ms"] > 1050:
            status, color = "READY", CYAN
        else:
            status, color = "EMPTY", MUTED
        self.text(status, (16, 370), 22, color)
        self.text(f"RECORD SOURCE  {source}", (624, 374), 14, MUTED, "topright")

    def edit_page(self) -> None:
        self.text("PRESETS", (16, 52), 12, MUTED)
        bank = self.preset_bank
        self.button(
            pygame.Rect(16, 64, 40, 36),
            "A/B",
            False,
            PURPLE,
            sublabel="9-16" if bank else "1-8",
        )
        for index in range(8):
            slot = bank * 8 + index
            rect = pygame.Rect(64 + index * 47, 64, 43, 36)
            self.button(rect, str(slot + 1), int(self.state["preset_slot"]) == slot, GREEN)
        self.button(pygame.Rect(440, 64, 88, 36), "LOAD", False, GREEN)
        self.button(pygame.Rect(534, 64, 90, 36), "SAVE", False, ORANGE)

        for index, spec in enumerate(EDIT_SLIDERS):
            col = index % 2
            row = index // 2
            rect = pygame.Rect(16 + col * 308, 116 + row * 67, 296, 52)
            self.slider(rect, spec)

        demo_rect = pygame.Rect(16, 382, 190, 36)
        self.button(demo_rect, "DEMO INPUT", self.state["demo"] >= 0.5, GREEN)
        self.text(
            "USB INPUT IS SELECTED AUTOMATICALLY AT START",
            (624, 403),
            12,
            MUTED,
            "midright",
        )

    def navigation(self) -> None:
        pygame.draw.rect(self.screen, PANEL, (0, 424, WIDTH, 56))
        labels = ("PERFORM", "LOOP", "EDIT")
        for index, label in enumerate(labels):
            rect = pygame.Rect(index * 213, 424, 214, 56)
            active = index == self.page
            if active:
                pygame.draw.rect(self.screen, CYAN, (rect.x, rect.y, rect.width, 4))
            self.text(label, rect.center, 16, TEXT if active else MUTED, "center")

    def draw(self) -> None:
        self.screen.fill(BG)
        self.header()
        if self.page == 0:
            self.perform_page()
        elif self.page == 1:
            self.loop_page()
        else:
            self.edit_page()
        self.navigation()
        if time.monotonic() < self.notice_until:
            notice_rect = pygame.Rect(208, 390, 224, 28)
            self.rounded(self.screen, notice_rect, PANEL_2, 8)
            self.text(self.notice, notice_rect.center, 12, TEXT, "center")
        pygame.display.flip()

    def slider_at(self, pos: tuple[int, int]) -> tuple[pygame.Rect, SliderSpec] | None:
        if self.page == 0:
            for row, spec in enumerate(PERFORM_SLIDERS):
                rect = pygame.Rect(408, 110 + row * 57, 216, 46)
                if rect.collidepoint(pos):
                    return rect, spec
        elif self.page == 2:
            for index, spec in enumerate(EDIT_SLIDERS):
                col, row = index % 2, index // 2
                rect = pygame.Rect(16 + col * 308, 116 + row * 67, 296, 52)
                if rect.collidepoint(pos):
                    return rect, spec
        return None

    def update_slider(self, pos: tuple[int, int], rect: pygame.Rect, spec: SliderSpec) -> None:
        amount = (pos[0] - rect.x) / rect.width
        value = self.denormalized(spec, amount)
        if spec.key in ("bpm", "pitch", "tone"):
            value = round(value)
        self.set_value(spec.key, value)

    def update_xy(self, pos: tuple[int, int]) -> None:
        rect = pygame.Rect(16, 122, 378, 204)
        x_amount = max(0, min(1, (pos[0] - rect.x) / rect.width))
        y_amount = max(0, min(1, 1 - (pos[1] - rect.y) / rect.height))
        x_spec, y_spec = self.xy_specs()
        x_value = self.denormalized(x_spec, x_amount)
        y_value = self.denormalized(y_spec, y_amount)
        if x_spec.key in ("bpm", "pitch", "tone"):
            x_value = round(x_value)
        if y_spec.key in ("bpm", "pitch", "tone"):
            y_value = round(y_value)
        self.set_value(x_spec.key, x_value)
        self.set_value(y_spec.key, y_value)

    def pointer_down(self, pos: tuple[int, int]) -> None:
        now = time.monotonic()
        if pygame.Rect(572, 0, 68, 50).collidepoint(pos):
            self.running = False
            return

        if pos[1] >= 424:
            self.page = min(2, pos[0] // 213)
            return

        if self.page == 0:
            if 58 <= pos[1] <= 92 and 16 <= pos[0] <= 624:
                index = min(3, (pos[0] - 16) // 153)
                self.set_value("mode", index)
                return
            if 96 <= pos[1] <= 116 and 16 <= pos[0] <= 624:
                w3 = (608 - 12) // 3
                i = min(2, (pos[0] - 16) // (w3 + 6))
                self.apply_variant(int(self.state["mode"]), i)
                return
            if pygame.Rect(16, 122, 378, 204).collidepoint(pos):
                self.drag = ("xy", pygame.Rect(16, 122, 378, 204), None)
                self.update_xy(pos)
                return
            slider = self.slider_at(pos)
            if slider:
                rect, spec = slider
                self.drag = ("slider", rect, spec)
                self.update_slider(pos, rect, spec)
                return
            for index, key in enumerate(("freeze", "loop_record", "bypass")):
                if pygame.Rect(16 + index * 204, 348, 192, 62).collidepoint(pos):
                    self.toggle(key)
                    return

        elif self.page == 1:
            if pygame.Rect(16, 124, 292, 126).collidepoint(pos):
                self.toggle("loop_record")
            elif pygame.Rect(320, 124, 146, 126).collidepoint(pos):
                self.toggle("loop_play")
            elif pygame.Rect(478, 124, 146, 126).collidepoint(pos):
                self.action("overdub")
            else:
                rects = [pygame.Rect(16 + i * 152, 266, 140, 72) for i in range(4)]
                if rects[0].collidepoint(pos) and self.state["undo_valid"] >= 0.5:
                    self.action("undo")
                elif rects[1].collidepoint(pos):
                    self.toggle("loop_reverse")
                elif rects[2].collidepoint(pos):
                    self.toggle("loop_route")
                elif rects[3].collidepoint(pos):
                    self.press_target = "clear"
                    self.press_started = now

        else:
            if pygame.Rect(16, 64, 40, 36).collidepoint(pos):
                self.preset_bank ^= 1
                return
            for index in range(8):
                if pygame.Rect(64 + index * 47, 64, 43, 36).collidepoint(pos):
                    self.set_value("preset_slot", self.preset_bank * 8 + index)
                    return
            if pygame.Rect(440, 64, 88, 36).collidepoint(pos):
                self.action("preset_recall")
                self.notice = f"PRESET {int(self.state['preset_slot']) + 1} LOADED"
                self.notice_until = time.monotonic() + 1.2
                return
            if pygame.Rect(534, 64, 90, 36).collidepoint(pos):
                self.action("preset_save")
                self.notice = f"PRESET {int(self.state['preset_slot']) + 1} SAVED"
                self.notice_until = time.monotonic() + 1.2
                return
            slider = self.slider_at(pos)
            if slider:
                rect, spec = slider
                self.drag = ("slider", rect, spec)
                self.update_slider(pos, rect, spec)
                return
            if pygame.Rect(16, 382, 190, 36).collidepoint(pos):
                self.toggle("demo")

    def pointer_move(self, pos: tuple[int, int]) -> None:
        if not self.drag:
            return
        kind, rect, spec = self.drag
        if kind == "xy":
            self.update_xy(pos)
        elif spec:
            self.update_slider(pos, rect, spec)

    def pointer_up(self) -> None:
        self.drag = None
        self.press_target = None
        self.clear_progress = 0.0

    def keydown(self, key: int) -> None:
        if key == pygame.K_F10:
            self.running = False
        elif key == pygame.K_ESCAPE:
            self.page = 0
        elif key == pygame.K_TAB:
            self.page = (self.page + 1) % 3
        elif key == pygame.K_SPACE:
            self.toggle("freeze")
        elif key == pygame.K_1:
            self.toggle("demo")
        elif key in (pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
            self.set_value("mode", key - pygame.K_2)
        elif key == pygame.K_r:
            self.toggle("loop_record")
        elif key == pygame.K_o:
            self.action("overdub")
        elif key == pygame.K_p:
            self.toggle("loop_play")
        elif key == pygame.K_u:
            self.action("undo")
        elif key == pygame.K_y:
            self.toggle("loop_reverse")
        elif key == pygame.K_l:
            self.toggle("loop_route")
        elif key == pygame.K_BACKSPACE:
            self.action("clear")
        elif key in (pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9):
            slot = key - pygame.K_6
            self.set_value("preset_slot", slot)
            self.action("preset_recall")
        elif key == pygame.K_0:
            self.action("preset_save")
        elif key in (pygame.K_q, pygame.K_w):
            self.set_value("grain", 100 if key == pygame.K_q else 420)
        elif key in (pygame.K_a, pygame.K_s):
            self.set_value("mix", 0.35 if key == pygame.K_a else 0.85)
        elif key in (pygame.K_z, pygame.K_x):
            self.set_value("feedback", 0.55 if key == pygame.K_z else 0.9)
        elif key in (pygame.K_c, pygame.K_v):
            self.set_value("space", 0.2 if key == pygame.K_c else 0.75)
        elif key in (pygame.K_f, pygame.K_g):
            self.set_value("tone", 80 if key == pygame.K_f else 110)
        elif key in (pygame.K_b, pygame.K_n):
            self.set_value("pitch", -12 if key == pygame.K_b else 12)
            self.set_value("pitchmix", 0.35)
        elif key in (pygame.K_d, pygame.K_e):
            self.set_value("density", 0.3 if key == pygame.K_d else 0.9)
        elif key in (pygame.K_i, pygame.K_k):
            self.set_value("onset", 0.3 if key == pygame.K_i else 0.85)
        elif key == pygame.K_t:
            now = time.monotonic()
            self.tap_times = [stamp for stamp in self.tap_times if now - stamp < 3.0]
            self.tap_times.append(now)
            if len(self.tap_times) >= 2:
                intervals = [
                    b - a for a, b in zip(self.tap_times[:-1], self.tap_times[1:])
                ]
                bpm = max(40, min(200, 60 / (sum(intervals) / len(intervals))))
                self.set_value("bpm", round(bpm))

    def process_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.keydown(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pygame.mouse.set_visible(True)
                self.pointer_down(event.pos)
            elif event.type == pygame.MOUSEMOTION and self.drag:
                self.pointer_move(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.pointer_up()

    def update(self) -> None:
        now = time.monotonic()
        if self.press_target == "clear":
            self.clear_progress = min(1.0, (now - self.press_started) / 1.2)
            if self.clear_progress >= 1.0:
                self.action("clear")
                self.state["loop_record"] = 0.0
                self.state["loop_play"] = 0.0
                self.state["overdub_active"] = 0.0
                self.state["loop_ms"] = 1000.0
                self.state["loop_phase"] = 0.0
                self.state["undo_valid"] = 0.0
                self.press_target = None
                self.clear_progress = 0.0
        if now - self.last_sync > 2.0:
            self.sync()

    def run(self) -> int:
        self.sync()
        try:
            while self.running:
                self.receive()
                self.process_events()
                self.update()
                self.draw()
                self.clock.tick(20)
        finally:
            self.rx.close()
            self.tx.close()
            pygame.quit()
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(PocketcosmUI().run())
    except KeyboardInterrupt:
        raise SystemExit(0)
