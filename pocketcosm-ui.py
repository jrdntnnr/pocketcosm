#!/usr/bin/env python3
"""Native 640x480 performance interface for the Pocketcosm Pd engine.

Visual design: 1970s Cold-War / missile-control instrument panel on the
Hologram Electronics palette (cream bakelite faceplate, backlit annunciator
lamp buttons, phosphor radar scope, amber LED readouts). See
design_handoff_pocketcosm for the full spec. The networking/state protocol to
the Pd engine (UDP set/action/sync) is unchanged.
"""

from __future__ import annotations

import math
import os
import socket
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_MOUSE_TOUCH_EVENTS", "0")
os.environ.setdefault("SDL_TOUCH_MOUSE_EVENTS", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "x11")

import pygame


WIDTH, HEIGHT = 640, 480
PD_HOST, PD_PORT = "127.0.0.1", 9001
UI_PORT = 9002
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

# ----- Palette (vivid, per design tokens) -------------------------------------
RED = (232, 76, 43)
ORANGE = (245, 154, 46)
GOLD = (242, 199, 62)
GREEN = (95, 184, 90)
TEAL = (43, 179, 164)
BLUE = (62, 134, 200)
PURPLE = (140, 99, 192)

INK = (42, 37, 32)
FACE = (241, 230, 198)
HEADER_TOP = (243, 231, 194)
HEADER_BOT = (236, 221, 180)
BAR_BORDER = (207, 186, 138)
LED_AMBER = (242, 176, 67)
LED_BG = (34, 26, 17)
MUTED = (138, 124, 90)
SECONDARY = (94, 82, 56)
PHOSPHOR = (150, 205, 120)
TRACK_TOP = (214, 199, 164)
TRACK_BOT = (230, 219, 191)

MODES = ("CLOUD", "GLITCH", "ARP", "REVERSE", "MULTI", "MICRO")
MODE_FULL = ("CLOUD", "GLITCH", "ARP", "REVERSE", "MULTI DELAY", "MICRO LOOP")
MODE_COLOR = (TEAL, PURPLE, ORANGE, RED, BLUE, GREEN)

# Per-engine variants (sub-modes). Selecting a variant applies a parameter
# macro for that engine. Names match the design handoff.
VARIANT_NAMES = (
    ("DRIFT", "SHIMMER", "DENSE"),
    ("STUTTER", "SCATTER", "CHOP"),
    ("UP", "DOWN", "RANDOM"),
    ("TAPE", "SWELL", "WARP"),
    ("DUAL", "PING", "SWARM"),
    ("REPEAT", "STAB", "STRETCH"),
)
VARIANTS = (
    (
        {"grain": 320, "texture": 0.70, "density": 0.40, "feedback": 0.70, "space": 0.45, "tone": 100, "pitch": 0, "pitchmix": 0.0},
        {"grain": 120, "texture": 0.55, "density": 0.75, "feedback": 0.80, "space": 0.60, "tone": 112, "pitch": 12, "pitchmix": 0.4},
        {"grain": 600, "texture": 0.85, "density": 0.95, "feedback": 0.85, "space": 0.50, "tone": 96, "pitch": 0, "pitchmix": 0.0},
    ),
    (
        {"grain": 90, "density": 0.60, "bpm": 120, "texture": 0.40, "feedback": 0.60, "space": 0.30, "tone": 105},
        {"grain": 60, "density": 0.85, "bpm": 140, "texture": 0.80, "feedback": 0.70, "space": 0.45, "tone": 100},
        {"grain": 200, "density": 0.40, "bpm": 100, "texture": 0.50, "feedback": 0.50, "space": 0.35, "tone": 92},
    ),
    (
        {"grain": 180, "bpm": 120, "density": 0.60, "tone": 105, "pitch": 0, "feedback": 0.60, "space": 0.50},
        {"grain": 150, "bpm": 128, "density": 0.70, "tone": 110, "pitch": -12, "feedback": 0.65, "space": 0.55},
        {"grain": 240, "bpm": 96, "density": 0.55, "tone": 100, "pitch": 0, "feedback": 0.70, "space": 0.60},
    ),
    (
        {"grain": 300, "delay": 600, "texture": 0.60, "feedback": 0.70, "space": 0.55, "tone": 100},
        {"grain": 700, "delay": 1200, "texture": 0.70, "feedback": 0.80, "space": 0.60, "tone": 96},
        {"grain": 400, "delay": 800, "texture": 0.50, "feedback": 0.75, "space": 0.50, "tone": 104, "pitch": -12, "pitchmix": 0.4},
    ),
    (  # MULTI DELAY
        {"bpm": 120, "feedback": 0.45, "space": 0.30, "mix": 0.60, "tone": 105},
        {"bpm": 120, "feedback": 0.65, "space": 0.45, "mix": 0.70, "tone": 100},
        {"bpm": 140, "feedback": 0.80, "space": 0.60, "mix": 0.80, "tone": 96},
    ),
    (  # MICRO LOOP
        {"grain": 160, "feedback": 0.40, "space": 0.30, "mix": 0.70, "tone": 105},
        {"grain": 70, "feedback": 0.30, "space": 0.20, "mix": 0.75, "tone": 110},
        {"grain": 400, "feedback": 0.50, "space": 0.50, "mix": 0.70, "tone": 96},
    ),
)

# XY pad mapping per engine: (param_key, low, high, label, curve)
XY_SPECS = (
    (("texture", 0, 1, "TEXTURE →", "lin"), ("density", 0, 1, "DENSITY", "lin")),
    (("grain", 40, 350, "SLICE →", "log"), ("density", 0, 1, "DENSITY", "lin")),
    (("bpm", 40, 200, "RATE →", "lin"), ("density", 0, 1, "RANGE", "lin")),
    (("grain", 120, 1000, "SPEED →", "log"), ("delay", 20, 1000, "DEPTH", "log")),
    (("bpm", 40, 200, "RATE →", "lin"), ("feedback", 0, 0.97, "REPEATS", "lin")),
    (("grain", 40, 500, "SIZE →", "log"), ("feedback", 0, 0.97, "REPEATS", "lin")),
)

# Fader specs: (key, label, low, high, color, unit, curve)
PERFORM_SLIDERS = (
    ("delay", "MEMORY", 20, 1000, BLUE, "ms", "log"),
    ("feedback", "FEEDBACK", 0, 0.97, ORANGE, "%", "lin"),
    ("space", "SPACE", 0, 1, PURPLE, "%", "lin"),
    ("mix", "DRY / WET", 0, 1, GREEN, "%", "lin"),
)
EDIT_SLIDERS = (
    ("grain", "GRAIN", 40, 1000, TEAL, "ms", "log"),
    ("bpm", "TEMPO", 40, 200, GOLD, "bpm", "lin"),
    ("pitch", "PITCH", -24, 24, BLUE, "st", "lin"),
    ("pitchmix", "PITCH MIX", 0, 1, BLUE, "%", "lin"),
    ("tone", "TONE", 50, 120, GREEN, "midi", "lin"),
    ("onset", "ONSET", 0, 1, RED, "%", "lin"),
    ("texture", "TEXTURE", 0, 1, ORANGE, "%", "lin"),
    ("density", "DENSITY", 0, 1, PURPLE, "%", "lin"),
)


# Tempo subdivisions for synced engines (label, beat fraction).
SUBDIVISIONS = (("1/4", 1.0), ("1/8", 0.5), ("1/8T", 1.0 / 3.0), ("1/16", 0.25), ("1/8D", 0.75))


DEFAULTS = {
    "demo": 1.0, "freeze": 0.0, "bypass": 0.0, "mode": 0.0, "subdivision": 0.5,
    "grain": 220.0, "delay": 480.0, "bpm": 100.0, "pitch": 0.0, "pitchmix": 0.0,
    "texture": 0.55, "density": 0.5, "onset": 0.5, "tone": 100.0,
    "feedback": 0.72, "space": 0.35, "mix": 0.75,
    "loop_record": 0.0, "loop_play": 0.0, "loop_reverse": 0.0, "loop_route": 0.0,
    "loop_halfspeed": 0.0, "loop_ms": 1000.0, "loop_phase": 0.0,
    "undo_valid": 0.0, "overdub_active": 0.0, "preset_slot": 0.0,
    "inmeter": -100.0, "outmeter": -100.0, "clip": 0.0,
}


def shade(c, amt):
    """Blend color c toward white (amt>0) or black (amt<0) by |amt|."""
    f = 255 if amt > 0 else 0
    p = abs(amt)
    return tuple(round(ch + (f - ch) * p) for ch in c)


def _interp(stops, t):
    t = max(0.0, min(1.0, t))
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        if t <= p1:
            span = (p1 - p0) or 1e-9
            k = (t - p0) / span
            return tuple(round(c0[j] + (c1[j] - c0[j]) * k) for j in range(3))
    return stops[-1][1]


class PocketcosmUI:
    def __init__(self) -> None:
        pygame.init()
        pygame.event.set_allowed([
            pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION,
        ])
        flags = pygame.FULLSCREEN | pygame.NOFRAME
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        pygame.display.set_caption("Pocketcosm")
        print(f"Pocketcosm UI: SDL driver={pygame.display.get_driver()} "
              f"size={self.screen.get_size()}", flush=True)
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()

        self._fonts: dict = {}
        self._grad: dict = {}
        self._lens: dict = {}

        self.state = dict(DEFAULTS)
        self.page = 0
        self.preset_bank = 0
        self.sub = [1, 0, 0, 0, 0, 0]  # remembered variant per engine
        self.subdiv = 1  # tempo subdivision index
        self.running = True
        self.drag = None
        self.press_target = None
        self.press_started = 0.0
        self.clear_progress = 0.0
        self.last_rx = 0.0
        self.last_sync = 0.0
        self.flash_until = {}
        self.tap_times: list[float] = []
        self.previous = dict(self.state)

        self.tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.rx.bind(("127.0.0.1", UI_PORT))
        self.rx.setblocking(False)

        self.faceplate = self._build_faceplate()
        self.overlay = self._build_overlay()

    # ----- fonts --------------------------------------------------------------
    def f(self, kind: str, size: int) -> pygame.font.Font:
        key = (kind, size)
        font = self._fonts.get(key)
        if font is None:
            names = {
                "display": "PaytoneOne-Regular.ttf",
                "body": "SairaSemiCondensed-SemiBold.ttf",
                "bold": "SairaSemiCondensed-Bold.ttf",
                "mono": "ShareTechMono-Regular.ttf",
            }
            try:
                font = pygame.font.Font(os.path.join(FONT_DIR, names[kind]), size)
            except Exception:
                font = pygame.font.Font(None, size)
            self._fonts[key] = font
        return font

    def text(self, value, pos, kind, size, color, anchor="topleft", shadow=None):
        if shadow:
            s = self.f(kind, size).render(value, True, shadow)
            r = s.get_rect(); setattr(r, anchor, (pos[0], pos[1] + 1))
            self.screen.blit(s, r)
        surf = self.f(kind, size).render(value, True, color)
        rect = surf.get_rect(); setattr(rect, anchor, pos)
        self.screen.blit(surf, rect)
        return rect

    # ----- gradient + surface caches -----------------------------------------
    def vgrad(self, w, h, stops):
        key = (w, h, tuple(stops))
        surf = self._grad.get(key)
        if surf is None:
            surf = pygame.Surface((w, h))
            for y in range(h):
                t = y / (h - 1) if h > 1 else 0.0
                pygame.draw.line(surf, _interp(stops, t), (0, y), (w, y))
            self._grad[key] = surf
        return surf

    def hgrad(self, w, h, stops):
        key = ("h", w, h, tuple(stops))
        surf = self._grad.get(key)
        if surf is None:
            surf = pygame.Surface((w, h))
            for x in range(w):
                t = x / (w - 1) if w > 1 else 0.0
                pygame.draw.line(surf, _interp(stops, t), (x, 0), (x, h))
            self._grad[key] = surf
        return surf

    def rounded_grad(self, w, h, stops, radius):
        """A rounded-rect-masked vertical gradient surface (cached)."""
        key = ("rg", w, h, tuple(stops), radius)
        surf = self._lens.get(key)
        if surf is None:
            base = self.vgrad(w, h, stops).convert_alpha()
            mask = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
            base.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surf = base
            self._lens[key] = surf
        return surf

    # ----- static layers ------------------------------------------------------
    def _build_faceplate(self):
        surf = pygame.Surface((WIDTH, HEIGHT))
        surf.fill(FACE)
        scan = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for y in range(0, HEIGHT, 4):
            pygame.draw.rect(scan, (120, 95, 55, 9), (0, y, WIDTH, 2))
        surf.blit(scan, (0, 0))
        return surf

    def _build_overlay(self):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        # subtle halftone dots
        dots = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for y in range(0, HEIGHT, 5):
            for x in range(0, WIDTH, 5):
                dots.set_at((x, y), (0, 0, 0, 8))
        ov.blit(dots, (0, 0))
        # bezel rings
        pygame.draw.rect(ov, (230, 210, 154), (0, 0, WIDTH, HEIGHT), 3, border_radius=2)
        pygame.draw.rect(ov, (213, 189, 137), (3, 3, WIDTH - 6, HEIGHT - 6), 2, border_radius=2)
        # corner screws
        for (cx, cy) in ((15, 15), (WIDTH - 15, 15), (15, HEIGHT - 15), (WIDTH - 15, HEIGHT - 15)):
            for i, col in enumerate(((142, 124, 84), (183, 161, 118), (240, 230, 207))):
                pygame.draw.circle(ov, col, (cx, cy), 6 - i * 2)
            pygame.draw.line(ov, (55, 40, 22), (cx - 4, cy - 4), (cx + 4, cy + 4), 2)
        return ov

    # ----- networking ---------------------------------------------------------
    def send(self, message):
        try:
            self.tx.sendto((message + ";\n").encode("ascii"), (PD_HOST, PD_PORT))
        except OSError:
            pass

    def set_value(self, key, value):
        value = float(value)
        self.state[key] = value
        self.send(f"set {key} {value:.6g}")
        self.previous[key] = value

    def action(self, key):
        self.send(f"action {key}")

    def toggle(self, key):
        self.set_value(key, 0 if self.state.get(key, 0) >= 0.5 else 1)

    def flash(self, key):
        self.flash_until[key] = time.monotonic() + 0.35

    def is_flash(self, key):
        return time.monotonic() < self.flash_until.get(key, 0.0)

    def sync(self):
        self.send("sync")
        self.last_sync = time.monotonic()

    def receive(self):
        while True:
            try:
                packet = self.rx.recv(4096).decode("utf-8", "ignore")
            except (BlockingIOError, OSError):
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
                if key != "hit":
                    self.state[key] = value
                    self.previous[key] = value

    def apply_variant(self, mode, variant):
        self.set_value("mode", mode)
        for key, value in VARIANTS[mode][variant].items():
            self.set_value(key, value)
        self.sub[mode] = variant

    # ----- value helpers ------------------------------------------------------
    @staticmethod
    def normalized(low, high, value, curve):
        value = max(min(low, high), min(max(low, high), value))
        if curve == "log":
            return math.log(value / low) / math.log(high / low)
        return (value - low) / (high - low)

    @staticmethod
    def denormalized(low, high, amount, curve):
        amount = max(0.0, min(1.0, amount))
        if curve == "log":
            return low * ((high / low) ** amount)
        return low + amount * (high - low)

    def fmt(self, value, low, high, unit, curve):
        if unit == "%":
            return f"{round(self.normalized(low, high, value, curve) * 100)}%"
        if unit in ("ms", "bpm", "midi"):
            return f"{round(value)} {unit}"
        if unit == "st":
            return f"{value:+.0f} st"
        return f"{value:.2f}"

    # ============ DRAWING PRIMITIVES =========================================
    def collar(self, rect, radius):
        pygame.draw.rect(self.screen, (43, 41, 36), rect.inflate(9, 9), border_radius=radius + 4)
        pygame.draw.rect(self.screen, (135, 127, 106), rect.inflate(6, 6), border_radius=radius + 3)
        pygame.draw.rect(self.screen, (29, 27, 22), rect.inflate(3, 3), border_radius=radius + 1)

    def glow(self, rect, color, radius, intensity=1.0):
        for spread, alpha in ((20, 38), (10, 70)):
            g = pygame.Surface((rect.width + spread * 2, rect.height + spread * 2), pygame.SRCALPHA)
            pygame.draw.rect(g, (*color, int(alpha * intensity)), g.get_rect(), border_radius=radius + spread)
            self.screen.blit(g, (rect.x - spread, rect.y - spread))

    def lamp(self, rect, color, state, label, size, radius=6, sublabel=None, pulse=False):
        """state: 'on' | 'off' | 'dead'."""
        w, h = rect.size
        if state == "on":
            pf = (0.7 + 0.3 * (0.5 + 0.5 * math.sin(time.monotonic() * 5.7))) if pulse else 1.0
            self.glow(rect, color, radius, pf)
        self.collar(rect, radius)
        if state == "on":
            stops = [(0.0, shade(color, 0.60)), (0.5, color), (1.0, shade(color, -0.32))]
            legend = (255, 250, 240)
            lshadow = None
        elif state == "dead":
            stops = [(0.0, (59, 57, 51)), (0.68, (33, 31, 27)), (1.0, (21, 19, 15))]
            legend = (111, 106, 94)
            lshadow = (0, 0, 0)
        else:
            stops = [(0.0, shade(color, -0.44)), (0.66, shade(color, -0.62)), (1.0, shade(color, -0.78))]
            legend = shade(color, 0.42)
            lshadow = (0, 0, 0)
        self.screen.blit(self.rounded_grad(w, h, stops, radius), rect.topleft)
        pygame.draw.rect(self.screen, (22, 20, 15), rect, 2, border_radius=radius)
        cx, cy = rect.center
        if sublabel:
            self.text(label, (cx, cy - 6), "bold", size, legend, "center", lshadow)
            self.text(sublabel, (cx, cy + 9), "mono", 9, legend, "center")
        else:
            self.text(label, (cx, cy), "bold", size, legend, "center", lshadow)

    def fader(self, rect, color, value, low, high, label, unit, curve):
        w, h = rect.size
        # track
        self.screen.blit(self.rounded_grad(w, h, [(0.0, TRACK_TOP), (1.0, TRACK_BOT)], 6), rect.topleft)
        pygame.draw.rect(self.screen, (43, 41, 36), rect.inflate(3, 3), 2, border_radius=8)
        pygame.draw.rect(self.screen, (191, 173, 131), rect, 1, border_radius=6)
        amount = self.normalized(low, high, value, curve)
        fillw = max(3, round(w * amount))
        fill_full = self.rounded_grad(w, h, [(0.0, shade(color, 0.30)), (0.58, color), (1.0, shade(color, -0.16))], 5)
        self.screen.blit(fill_full, rect.topleft, area=pygame.Rect(0, 0, fillw, h))
        # handle
        hx = rect.x + fillw
        hr = pygame.Rect(0, 0, 13, h - 6); hr.center = (hx, rect.centery)
        self.screen.blit(self.hgrad(13, hr.height, [(0.0, (154, 147, 132)), (0.45, (207, 201, 187)), (1.0, (125, 118, 106))]), hr.topleft)
        pygame.draw.rect(self.screen, (29, 27, 22), hr, 1, border_radius=2)
        # label chip + value LED
        chip = self.f("bold", 12 if h < 44 else 13).render(label, True, INK)
        cr = chip.get_rect(midleft=(rect.x + 9, rect.centery))
        bg = cr.inflate(12, 6)
        s = pygame.Surface(bg.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (250, 243, 225, 225), s.get_rect(), border_radius=4)
        self.screen.blit(s, bg.topleft)
        self.screen.blit(chip, cr)
        self.led(self.fmt(value, low, high, unit, curve), (rect.right - 8, rect.centery), 13, "midright")

    def led(self, value, pos, size, anchor="midright"):
        surf = self.f("mono", size).render(value, True, LED_AMBER)
        r = surf.get_rect(); setattr(r, anchor, pos)
        bg = r.inflate(14, 6)
        pygame.draw.rect(self.screen, LED_BG, bg, border_radius=3)
        glow = self.f("mono", size).render(value, True, (120, 88, 33))
        gr = glow.get_rect(center=r.center)
        self.screen.blit(glow, gr.move(0, 1))
        self.screen.blit(surf, r)
        return bg

    def scope(self, rect, color, fx, fy, xlabel, ylabel):
        self.collar(rect, 8)
        scr = pygame.Surface(rect.size)
        scr.blit(self.vgrad(rect.width, rect.height, [(0.0, (45, 55, 39)), (0.8, (22, 27, 18)), (1.0, (16, 20, 13))]), (0, 0))
        for i in range(1, 4):
            x = rect.width * i // 4
            y = rect.height * i // 4
            pygame.draw.line(scr, (126, 196, 108), (x, 0), (x, rect.height), 1)
            pygame.draw.line(scr, (126, 196, 108), (0, y), (rect.width, y), 1)
        self.screen.blit(scr, rect.topleft)
        pygame.draw.rect(self.screen, (22, 20, 15), rect, 2, border_radius=8)
        self.text(ylabel, (rect.x + 11, rect.y + 9), "bold", 11, PHOSPHOR)
        self.text(xlabel, (rect.x + 11, rect.bottom - 9), "bold", 11, PHOSPHOR, "bottomleft")
        px = rect.x + int(fx * rect.width)
        py = rect.y + int((1 - fy) * rect.height)
        gl = pygame.Surface((48, 48), pygame.SRCALPHA)
        pygame.draw.circle(gl, (*color, 90), (24, 24), 18)
        pygame.draw.circle(gl, (*color, 60), (24, 24), 24)
        self.screen.blit(gl, (px - 24, py - 24))
        for i in range(8, 0, -1):
            t = i / 8
            col = _interp([(0.0, shade(color, 0.62)), (0.55, color), (1.0, shade(color, -0.30))], 1 - t)
            pygame.draw.circle(self.screen, col, (px - int(15 * 0.1), py - int(15 * 0.15)), int(15 * t))
        pygame.draw.circle(self.screen, (255, 255, 255), (px, py), 15, 2)

    # ============ HEADER / FOOTER ============================================
    def header(self):
        pygame.draw.rect(self.screen, HEADER_TOP, (0, 0, WIDTH, 56))
        self.screen.blit(self.vgrad(WIDTH, 56, [(0.0, HEADER_TOP), (1.0, HEADER_BOT)]), (0, 0))
        pygame.draw.line(self.screen, BAR_BORDER, (0, 55), (WIDTH, 55), 2)
        # logo: nested half-rings
        lx, ly = 40, 40
        for rad, col, th in ((15, (201, 72, 47), 3), (11, (219, 133, 55), 3), (7, (92, 147, 82), 3)):
            pygame.draw.arc(self.screen, col, pygame.Rect(lx - rad, ly - rad, rad * 2, rad * 2), 0.05, math.pi - 0.05, th)
        pygame.draw.rect(self.screen, (61, 110, 158), (lx - 3, ly - 4, 6, 4), border_radius=2)
        self.text("POCKETCOSM", (66, 28), "display", 18, (42, 34, 24), "midleft", (255, 255, 255))
        # right cluster (laid out right-to-left, non-overlapping)
        mode = int(self.state["mode"]) % 6
        self.text(MODE_FULL[mode], (410, 18), "display", 13, MODE_COLOR[mode], "midright")
        self.led(f"{round(self.state['bpm'])} BPM", (410, 39), 11, "midright")
        # meters
        self.meter(pygame.Rect(440, 17, 58, 8), self.state["inmeter"], (124, 192, 120), (79, 135, 72))
        self.meter(pygame.Rect(440, 31, 58, 8), self.state["outmeter"], (82, 192, 180), (39, 137, 127))
        self.text("IN", (436, 21), "bold", 9, (125, 111, 79), "midright")
        self.text("OUT", (436, 35), "bold", 9, (125, 111, 79), "midright")
        # CLIP
        clip = self.state["clip"] >= 0.5
        self.text("CLIP", (528, 28), "bold", 9, (125, 111, 79), "midright")
        cc = RED if clip else (194, 174, 130)
        pygame.draw.circle(self.screen, cc, (539, 28), 5)
        # EXIT lamp (red, unlit guard)
        ex = pygame.Rect(560, 13, 50, 30)
        self.exit_rect = ex
        self.collar(ex, 6)
        self.screen.blit(self.rounded_grad(ex.width, ex.height,
            [(0.0, (126, 38, 26)), (0.68, (81, 24, 16)), (1.0, (53, 13, 6))], 6), ex.topleft)
        pygame.draw.rect(self.screen, (22, 20, 15), ex, 2, border_radius=6)
        self.text("EXIT", ex.center, "bold", 14, (240, 183, 168), "center", (0, 0, 0))

    def meter(self, rect, db, top, bot):
        pygame.draw.rect(self.screen, (182, 162, 118), rect, border_radius=4)
        amount = max(0.0, min(1.0, (db + 60.0) / 60.0))
        if amount > 0:
            fw = max(2, round(rect.width * amount))
            self.screen.blit(self.rounded_grad(fw, rect.height, [(0.0, top), (1.0, bot)], 4), rect.topleft)

    def footer(self):
        y = HEIGHT - 50
        self.screen.blit(self.vgrad(WIDTH, 50, [(0.0, HEADER_BOT), (1.0, HEADER_TOP)]), (0, y))
        pygame.draw.line(self.screen, BAR_BORDER, (0, y), (WIDTH, y), 2)
        labels = ("PERFORM", "LOOP", "EDIT")
        for i, label in enumerate(labels):
            cx = WIDTH * (2 * i + 1) // 6
            active = i == self.page
            led_x = cx - self.f("display", 16).size(label)[0] // 2 - 14
            if active:
                gl = pygame.Surface((22, 22), pygame.SRCALPHA)
                pygame.draw.circle(gl, (*TEAL, 110), (11, 11), 9)
                self.screen.blit(gl, (led_x - 11, y + 25 - 11))
                pygame.draw.circle(self.screen, TEAL, (led_x, y + 25), 4)
                self.text(label, (cx + 6, y + 25), "display", 16, (42, 37, 32), "center")
            else:
                pygame.draw.circle(self.screen, (154, 138, 100), (led_x, y + 25), 4)
                self.text(label, (cx + 6, y + 25), "display", 16, MUTED, "center")

    # ============ LAYOUTS ====================================================
    def perform_layout(self):
        L = {}
        gap = 8
        bw = (604 - gap * 5) // 6
        L["tabs"] = [pygame.Rect(18 + i * (bw + gap), 69, bw, 38) for i in range(6)]
        sw = (604 - 13 * 2) // 3
        L["subs"] = [pygame.Rect(18 + i * (sw + 13), 119, sw, 28) for i in range(3)]
        L["pad"] = pygame.Rect(18, 159, 326, 196)
        fx = 360
        L["faders"] = [pygame.Rect(fx, 161 + i * 51, 622 - fx, 39) for i in range(4)]
        aw = (604 - 14 * 2) // 3
        L["actions"] = [pygame.Rect(18 + i * (aw + 14), 367, aw, 50) for i in range(3)]
        return L

    def loop_layout(self):
        L = {}
        L["progress"] = pygame.Rect(18, 107, 604, 13)
        L["record"] = pygame.Rect(18, 134, 287, 144)
        L["play"] = pygame.Rect(320, 134, 143, 144)
        L["over"] = pygame.Rect(478, 134, 144, 144)
        mw = (604 - 13 * 5) // 6
        L["mods"] = [pygame.Rect(18 + i * (mw + 13), 292, mw, 58) for i in range(6)]
        return L

    def edit_layout(self):
        L = {}
        flexes = [1.15] + [1.0] * 8 + [1.8, 1.8]
        total = sum(flexes)
        avail = 604 - 9 * (len(flexes) - 1)
        x = 18
        L["presets"] = []
        for fl in flexes:
            w = round(avail * fl / total)
            L["presets"].append(pygame.Rect(x, 88, w, 40))
            x += w + 9
        colw = (604 - 18) // 2
        L["params"] = []
        for i in range(8):
            col, row = i % 2, i // 2
            L["params"].append(pygame.Rect(18 + col * (colw + 18), 145 + row * 59, colw, 46))
        L["demo"] = pygame.Rect(18, 381, 150, 36)
        L["subdiv"] = pygame.Rect(196, 381, 104, 36)
        return L

    # ============ PAGES ======================================================
    def perform_page(self):
        L = self.perform_layout()
        mode = int(self.state["mode"]) % 6
        color = MODE_COLOR[mode]
        for i, r in enumerate(L["tabs"]):
            self.lamp(r, MODE_COLOR[i], "on" if mode == i else "off", MODES[i], 13)
        for i, r in enumerate(L["subs"]):
            on = self.sub[mode] == i
            self.lamp(r, color, "on" if on else "off", VARIANT_NAMES[mode][i], 12, radius=5)
        # XY pad
        xs, ys = XY_SPECS[mode]
        fx = self.normalized(xs[1], xs[2], self.state[xs[0]], xs[4])
        fy = self.normalized(ys[1], ys[2], self.state[ys[0]], ys[4])
        self.scope(L["pad"], color, fx, fy, xs[3], ys[3])
        for r, (k, label, lo, hi, c, unit, curve) in zip(L["faders"], PERFORM_SLIDERS):
            self.fader(r, c, self.state[k], lo, hi, label, unit, curve)
        # actions
        rec = self.state["loop_record"] >= 0.5
        self.lamp(L["actions"][0], TEAL, "on" if self.state["freeze"] >= 0.5 else "off", "FREEZE", 16, radius=7)
        self.lamp(L["actions"][1], RED, "on" if (rec or self.is_flash("capture")) else "off", "CAPTURE", 16, radius=7)
        self.lamp(L["actions"][2], GOLD, "on" if self.state["bypass"] >= 0.5 else "off", "BYPASS", 16, radius=7)

    def loop_phase(self):
        if self.state["loop_record"] >= 0.5:
            return max(0.0, min(1.0, self.state["loop_ms"] / 60000.0))
        if self.state["loop_play"] < 0.5:
            return 0.0
        return max(0.0, min(1.0, self.state["loop_phase"]))

    def loop_page(self):
        L = self.loop_layout()
        rec = self.state["loop_record"] >= 0.5
        playing = self.state["loop_play"] >= 0.5 and not rec
        self.text("PHRASE LOOP", (18, 82), "display", 20, (42, 34, 24), "midleft", (255, 255, 255))
        secs = self.state["loop_ms"] / 1000.0
        self.led(f"{secs:05.1f} SEC", (622, 82), 16, "midright")
        # progress
        pr = L["progress"]
        pygame.draw.rect(self.screen, (199, 180, 136), pr, border_radius=4)
        pygame.draw.rect(self.screen, (43, 41, 36), pr.inflate(3, 3), 2, border_radius=5)
        frac = self.loop_phase()
        if frac > 0:
            c = RED if rec else GREEN
            fw = max(4, round(pr.width * frac))
            self.screen.blit(self.rounded_grad(fw, pr.height, [(0.0, shade(c, 0.30)), (0.58, c), (1.0, shade(c, -0.16))], 4), pr.topleft)
        # transport
        self.lamp(L["record"], RED, "on" if rec else "off", "STOP" if rec else "RECORD", 24, radius=9, sublabel="MAX 60 SECONDS", pulse=rec)
        self.lamp(L["play"], GREEN, "on" if playing else "off", "PLAY", 21, radius=9)
        self.lamp(L["over"], ORANGE, "on" if self.state["overdub_active"] >= 0.5 else "off", "OVERDUB", 17, radius=9)
        # mods
        undo_dead = self.state["undo_valid"] < 0.5
        route = self.state["loop_route"] >= 0.5
        defs = [
            (BLUE, "dead" if undo_dead else "off", "UNDO"),
            (PURPLE, "on" if self.state["loop_reverse"] >= 0.5 else "off", "REVERSE"),
            (TEAL, "on" if route else "off", "POST FX" if route else "PRE FX"),
            (GOLD, "off", "CLEAR"),
            (BLUE, "on" if self.state["loop_halfspeed"] >= 0.5 else "off", "1/2 SPEED"),
            (ORANGE, "on" if self.is_flash("fade") else "off", "FADE"),
        ]
        for r, (c, st, label) in zip(L["mods"], defs):
            self.lamp(r, c, st, label, 13, radius=6)
            if label == "CLEAR" and self.clear_progress > 0:
                bar = pygame.Rect(r.x + 8, r.bottom - 10, r.width - 16, 4)
                pygame.draw.rect(self.screen, (60, 50, 30), bar)
                bar.width = round(bar.width * self.clear_progress)
                pygame.draw.rect(self.screen, GOLD, bar)
        # status
        if rec:
            status, scol = "RECORDING", RED
        elif self.state["overdub_active"] >= 0.5:
            status, scol = "OVERDUBBING", ORANGE
        elif playing:
            status, scol = "PLAYING", GREEN
        elif self.state["loop_ms"] > 1050:
            status, scol = "STOPPED", SECONDARY
        else:
            status, scol = "EMPTY", (169, 156, 124)
        self.text(status, (18, 405), "display", 22, scol, "midleft", (255, 255, 255))
        self.text("RECORD SOURCE", (520, 408), "body", 12, MUTED, "midright")
        self.text("DRY INPUT", (622, 408), "bold", 12, SECONDARY, "midright")

    def edit_page(self):
        L = self.edit_layout()
        self.text("PRESETS", (18, 64), "bold", 11, MUTED)
        bank = self.preset_bank
        slot = int(self.state["preset_slot"])
        for i, r in enumerate(L["presets"]):
            if i == 0:
                self.lamp(r, PURPLE, "off", "A/B", 15, sublabel="9-16" if bank else "1-8")
            elif 1 <= i <= 8:
                s = bank * 8 + (i - 1)
                self.lamp(r, GREEN, "on" if slot == s else "off", str(s + 1), 15)
            elif i == 9:
                self.lamp(r, GREEN, "on" if self.is_flash("preset_recall") else "off", "LOAD", 15)
            else:
                self.lamp(r, ORANGE, "on" if self.is_flash("preset_save") else "off", "SAVE", 15)
        for r, (k, label, lo, hi, c, unit, curve) in zip(L["params"], EDIT_SLIDERS):
            self.fader(r, c, self.state[k], lo, hi, label, unit, curve)
        self.lamp(L["demo"], GREEN, "on" if self.state["demo"] >= 0.5 else "off", "DEMO INPUT", 14, radius=8)
        self.lamp(L["subdiv"], GOLD, "on", SUBDIVISIONS[self.subdiv][0], 15, radius=8, sublabel="SYNC")
        self.text("USB INPUT AUTO-SELECTED AT START", (622, 399), "body", 11, MUTED, "midright")

    def draw(self):
        self.screen.blit(self.faceplate, (0, 0))
        self.header()
        if self.page == 0:
            self.perform_page()
        elif self.page == 1:
            self.loop_page()
        else:
            self.edit_page()
        self.footer()
        self.screen.blit(self.overlay, (0, 0))
        pygame.display.flip()

    # ============ INPUT ======================================================
    def _fader_value(self, rect, spec, x):
        k, label, lo, hi, c, unit, curve = spec
        amount = max(0.0, min(1.0, (x - rect.x) / rect.width))
        value = self.denormalized(lo, hi, amount, curve)
        if k in ("bpm", "pitch", "tone"):
            value = round(value)
        self.set_value(k, value)

    def update_xy(self, pos):
        L = self.perform_layout()
        pad = L["pad"]
        mode = int(self.state["mode"]) % 6
        xs, ys = XY_SPECS[mode]
        xa = max(0.0, min(1.0, (pos[0] - pad.x) / pad.width))
        ya = max(0.0, min(1.0, 1 - (pos[1] - pad.y) / pad.height))
        for spec, amt in ((xs, xa), (ys, ya)):
            v = self.denormalized(spec[1], spec[2], amt, spec[4])
            if spec[0] in ("bpm", "pitch", "tone"):
                v = round(v)
            self.set_value(spec[0], v)

    def pointer_down(self, pos):
        now = time.monotonic()
        if hasattr(self, "exit_rect") and self.exit_rect.collidepoint(pos):
            self.running = False
            return
        if pos[1] >= HEIGHT - 50:
            self.page = min(2, pos[0] * 3 // WIDTH)
            return

        if self.page == 0:
            L = self.perform_layout()
            mode = int(self.state["mode"]) % 6
            for i, r in enumerate(L["tabs"]):
                if r.collidepoint(pos):
                    self.set_value("mode", i)
                    return
            for i, r in enumerate(L["subs"]):
                if r.collidepoint(pos):
                    self.apply_variant(mode, i)
                    return
            if L["pad"].collidepoint(pos):
                self.drag = ("xy", None, None)
                self.update_xy(pos)
                return
            for r, spec in zip(L["faders"], PERFORM_SLIDERS):
                if r.collidepoint(pos):
                    self.drag = ("fader", r, spec)
                    self._fader_value(r, spec, pos[0])
                    return
            if L["actions"][0].collidepoint(pos):
                self.toggle("freeze")
            elif L["actions"][1].collidepoint(pos):
                self.toggle("loop_record"); self.flash("capture")
            elif L["actions"][2].collidepoint(pos):
                self.toggle("bypass")

        elif self.page == 1:
            L = self.loop_layout()
            if L["record"].collidepoint(pos):
                self.toggle("loop_record")
            elif L["play"].collidepoint(pos):
                self.toggle("loop_play")
            elif L["over"].collidepoint(pos):
                self.action("overdub")
            else:
                for i, r in enumerate(L["mods"]):
                    if not r.collidepoint(pos):
                        continue
                    if i == 0 and self.state["undo_valid"] >= 0.5:
                        self.action("undo")
                    elif i == 1:
                        self.toggle("loop_reverse")
                    elif i == 2:
                        self.toggle("loop_route")
                    elif i == 3:
                        self.press_target = "clear"; self.press_started = now
                    elif i == 4:
                        self.toggle("loop_halfspeed")
                    elif i == 5:
                        self.action("fade"); self.flash("fade")
                    return

        else:
            L = self.edit_layout()
            for i, r in enumerate(L["presets"]):
                if not r.collidepoint(pos):
                    continue
                if i == 0:
                    self.preset_bank ^= 1
                elif 1 <= i <= 8:
                    self.set_value("preset_slot", self.preset_bank * 8 + (i - 1))
                elif i == 9:
                    self.action("preset_recall"); self.flash("preset_recall")
                else:
                    self.action("preset_save"); self.flash("preset_save")
                return
            for r, spec in zip(L["params"], EDIT_SLIDERS):
                if r.collidepoint(pos):
                    self.drag = ("fader", r, spec)
                    self._fader_value(r, spec, pos[0])
                    return
            if L["demo"].collidepoint(pos):
                self.toggle("demo")
            elif L["subdiv"].collidepoint(pos):
                self.subdiv = (self.subdiv + 1) % len(SUBDIVISIONS)
                self.set_value("subdivision", SUBDIVISIONS[self.subdiv][1])
                self.set_value("bpm", self.state["bpm"])  # re-send to apply now

    def pointer_move(self, pos):
        if not self.drag:
            return
        kind, rect, spec = self.drag
        if kind == "xy":
            self.update_xy(pos)
        elif kind == "fader":
            self._fader_value(rect, spec, pos[0])

    def pointer_up(self):
        self.drag = None
        self.press_target = None
        self.clear_progress = 0.0

    def keydown(self, key):
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
            self.set_value("preset_slot", key - pygame.K_6)
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
            self.tap_times = [s for s in self.tap_times if now - s < 3.0]
            self.tap_times.append(now)
            if len(self.tap_times) >= 2:
                intervals = [b - a for a, b in zip(self.tap_times[:-1], self.tap_times[1:])]
                bpm = max(40, min(200, 60 / (sum(intervals) / len(intervals))))
                self.set_value("bpm", round(bpm))

    def process_events(self):
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

    def update(self):
        now = time.monotonic()
        if self.press_target == "clear":
            self.clear_progress = min(1.0, (now - self.press_started) / 1.2)
            if self.clear_progress >= 1.0:
                self.action("clear")
                for k in ("loop_record", "loop_play", "overdub_active", "loop_phase", "undo_valid"):
                    self.state[k] = 0.0
                self.state["loop_ms"] = 1000.0
                self.press_target = None
                self.clear_progress = 0.0
        if now - self.last_sync > 2.0:
            self.sync()

    def run(self):
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
