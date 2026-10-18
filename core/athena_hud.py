"""
Athena emblem — a HUD centrepiece inspired by Athena, Greek goddess of wisdom.

  * a stylised owl (Athena's symbol) whose eyes are the status display:
      idle      — calm, slow blinks
      listening — eyes wide, pupils glow
      thinking  — pupils glance around, iris rings spin fast
      speaking  — pupils pulse with the voice
      muted / asleep — eyes closed
  * a laurel wreath around the owl
  * a ring of radial ticks that moves with the audio level
  * a rotating band of Greek letters: ΑΘΗΝΑ · ΣΟΦΙΑ · ΠΑΛΛΑΣ
  * an outer Greek-key (meander) band turning slowly

Software QPainter only, same contract as core/sphere.py:
    step(dt, amp, speaking, muted, state)   paint(p, cx, cy, r, main, acc, bg)
"""

from __future__ import annotations

import math
import random

from PyQt6.QtCore import QLineF, QPointF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QRadialGradient
from datetime import datetime


def _mix(a: QColor, b: QColor, k: float) -> QColor:
    k = max(0.0, min(1.0, k))
    return QColor(int(a.red() + (b.red() - a.red()) * k),
                  int(a.green() + (b.green() - a.green()) * k),
                  int(a.blue() + (b.blue() - a.blue()) * k))


GOLD = QColor(232, 196, 112)
WHITE = QColor(230, 242, 250)
TEXT = "ΑΘΗΝΑ • ΣΟΦΙΑ • ΠΑΛΛΑΣ • "


class AthenaEmblem:
    def __init__(self) -> None:
        self.t = 0.0
        self.amp = 0.0
        self.energy = 0.3
        self.key_rot = 0.0
        self.text_rot = 0.0
        self.iris_rot = 0.0
        self.lid = 1.0            # 1 open … 0 closed
        self._lid_target = 1.0
        self._next_blink = 3.0
        self._blink_t = -1.0
        self.look = [0.0, 0.0]
        self._look_target = [0.0, 0.0]
        self._next_look = 1.0
        self.state = ""
        self.speaking = False
        self.muted = False
        # mood / night
        self.mood = None          # "happy" | "goodnight" | "goodmorning" | None
        self._mood_t = 0.0
        self.happy = 0.0          # 0..1 — eyes turn into happy arcs
        self.night = False
        self._night_check = 0.0
        self.sleep_pose = False   # true when she should look properly asleep
        self._fx = []             # floating hearts / sparkles / z's
        self._next_z = 0.0
        rnd = random.Random(11)
        self._tick_noise = [rnd.uniform(0.4, 1.0) for _ in range(120)]
        self._stars = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(1.04, 1.25),
                        rnd.uniform(0.6, 1.6), rnd.uniform(0, 6.28)) for _ in range(70)]

    # ── mood ────────────────────────────────────────────────────────────────
    def set_mood(self, mood: str) -> None:
        mood = (mood or "").lower()
        if mood not in ("happy", "goodnight", "goodmorning"):
            return
        self.mood = mood
        self._mood_t = {"happy": 6.0, "goodnight": 12.0, "goodmorning": 4.0}[mood]
        if mood == "happy":
            for _ in range(9):
                self._spawn("heart" if random.random() < 0.6 else "spark")
        elif mood == "goodmorning":
            for _ in range(10):
                self._spawn("spark")

    def _spawn(self, kind: str) -> None:
        if kind == "z":
            self._fx.append({"k": "z", "x": 0.20, "y": -0.30, "vx": 0.05,
                             "vy": -0.07, "life": 3.2, "age": 0.0,
                             "s": random.uniform(0.8, 1.2)})
        else:
            a = random.uniform(-2.6, -0.5)
            self._fx.append({"k": kind, "x": math.cos(a) * 0.30, "y": math.sin(a) * 0.20 - 0.05,
                             "vx": random.uniform(-0.06, 0.06), "vy": random.uniform(-0.20, -0.10),
                             "life": random.uniform(1.8, 2.8), "age": 0.0,
                             "s": random.uniform(0.7, 1.3)})

    def _step_mood(self, dt: float, asleep: bool) -> None:
        self._night_check -= dt
        if self._night_check <= 0:
            try:
                from memory.config_manager import get_night_mode
                self.night = get_night_mode()[0]
            except Exception:
                h = datetime.now().hour
                self.night = h >= 23 or h < 6
            self._night_check = 30.0
        if self.mood:
            self._mood_t -= dt
            if self._mood_t <= 0:
                self.mood = None
        tgt_h = 1.0 if self.mood == "happy" else 0.0
        self.happy += (tgt_h - self.happy) * min(1.0, dt * 6)
        self.sleep_pose = asleep or self.mood == "goodnight"
        # z's float up while she sleeps at night (or right after "boa noite")
        if (asleep and self.night) or (self.mood == "goodnight" and self.lid < 0.2):
            self._next_z -= dt
            if self._next_z <= 0:
                self._spawn("z")
                self._next_z = 1.4
        if self.mood == "happy" and random.random() < dt * 1.5:
            self._spawn("heart" if random.random() < 0.6 else "spark")
        for f in self._fx:
            f["age"] += dt
            f["x"] += f["vx"] * dt
            f["y"] += f["vy"] * dt
        self._fx = [f for f in self._fx if f["age"] < f["life"]]

    def _paint_fx(self, p, cx, cy, r, gold, accent, line, bg) -> None:
        if not self._fx:
            return
        for f in self._fx:
            u = f["age"] / f["life"]
            alpha = math.sin(math.pi * min(1.0, u)) * 0.95
            x, y = cx + f["x"] * r, cy + f["y"] * r
            sz = r * 0.035 * f["s"]
            if f["k"] == "heart":
                pts = []
                for i in range(21):
                    t = i / 20 * 2 * math.pi
                    hx = 16 * math.sin(t) ** 3
                    hy = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
                    pts.append((x + hx * sz / 16, y - hy * sz / 16))
                p.setPen(QPen(_mix(bg, _mix(accent, QColor(255, 90, 140), 0.6), alpha), 1.6))
                p.drawLines([QLineF(a[0], a[1], b[0], b[1]) for a, b in zip(pts, pts[1:])])
            elif f["k"] == "spark":
                p.setPen(QPen(_mix(bg, gold, alpha), 1.3))
                for ang in (0, math.pi / 2):
                    dx, dy = math.cos(ang) * sz, math.sin(ang) * sz
                    p.drawLine(QLineF(x - dx, y - dy, x + dx, y + dy))
            else:  # z
                font = QFont("Times New Roman", max(8, int(r * 0.07 * f["s"] * (0.7 + 0.6 * u))))
                p.setFont(font)
                p.setPen(QPen(_mix(bg, line, alpha * 0.9), 1.0))
                p.drawText(QPointF(x, y), "z")

    @staticmethod
    def _happy_eye(p, ex, ey, R, col) -> None:
        """Closed, smiling eye: an upward arc  ^"""
        pts = []
        for i in range(13):
            a = math.pi * i / 12
            pts.append((ex + math.cos(a) * R * 0.8, ey + R * 0.2 - math.sin(a) * R * 0.55))
        pn = QPen(col, 2.2)
        pn.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pn)
        p.drawLines([QLineF(a[0], a[1], b[0], b[1]) for a, b in zip(pts, pts[1:])])

    # ── animation ───────────────────────────────────────────────────────────
    def step(self, dt: float, amp: float, speaking: bool = False,
             muted: bool = False, state: str = "") -> None:
        dt = max(0.0, min(0.1, dt))
        self.t += dt
        self.state, self.speaking, self.muted = state, speaking, muted
        self.amp += (amp - self.amp) * min(1.0, dt * 12)
        thinking = state in ("THINKING", "PROCESSING")
        asleep = muted or state == "SLEEPING"
        self._step_mood(dt, asleep)
        asleep = self.sleep_pose

        if asleep:
            tgt_e, spin = 0.08, 0.02
        elif speaking:
            tgt_e, spin = 0.8 + 0.2 * self.amp, 0.10
        elif thinking:
            tgt_e, spin = 0.7, 0.16
        elif state == "LISTENING":
            tgt_e, spin = 0.5 + 0.3 * self.amp, 0.07
        else:
            tgt_e, spin = 0.32, 0.05
        self.energy += (tgt_e - self.energy) * min(1.0, dt * 3)
        self.key_rot += spin * dt
        self.text_rot -= spin * 0.7 * dt
        self.iris_rot += (0.6 + 4.0 * (1.0 if thinking else self.energy * 0.5)) * dt

        # eyelids: closed when asleep, otherwise natural blinks
        if asleep:
            self._lid_target = 0.0
        else:
            # a little drowsy late at night when nothing is happening
            drowsy = self.night and not (speaking or thinking or state == "LISTENING")
            self._lid_target = 0.65 if drowsy else 1.0
            self._next_blink -= dt
            if self._next_blink <= 0:
                self._blink_t = 0.0
                self._next_blink = random.uniform(2.5, 6.0)
        lid = self._lid_target
        if self._blink_t >= 0:
            self._blink_t += dt
            ph = self._blink_t / 0.18
            if ph >= 1.0:
                self._blink_t = -1.0
            else:
                lid = min(lid, abs(1.0 - 2.0 * ph))
        rate = 25 if self._blink_t >= 0 else (1.2 if self.mood == "goodnight" else 6)
        self.lid += (lid - self.lid) * min(1.0, dt * rate)

        # gaze: wanders while thinking, centred otherwise
        self._next_look -= dt
        if self._next_look <= 0:
            if thinking:
                self._look_target = [random.uniform(-1, 1), random.uniform(-0.6, 0.4)]
                self._next_look = random.uniform(0.35, 0.8)
            else:
                self._look_target = [random.uniform(-0.25, 0.25), random.uniform(-0.15, 0.15)]
                self._next_look = random.uniform(1.5, 4.0)
        for i in range(2):
            self.look[i] += (self._look_target[i] - self.look[i]) * min(1.0, dt * 8)

    # ── helpers ─────────────────────────────────────────────────────────────
    @staticmethod
    def _polar(cx, cy, ang, rad):
        return cx + math.cos(ang) * rad, cy + math.sin(ang) * rad

    def _meander(self, cx, cy, r_in, r_out, units, rot):
        """Greek-key band as line segments in (angle, radius) space."""
        pat = [(0, 0), (0, 1), (1, 1), (1, 0.3), (0.35, 0.3), (0.35, 0.65), (0.65, 0.65)]
        span = 2 * math.pi / units
        w = 1.3                                   # unit width incl. gap
        lines = []

        def m(u, v):
            a = rot + u * span / w
            return self._polar(cx, cy, a, r_in + (r_out - r_in) * v)

        for k in range(units):
            base = k * w
            pts = [m(base + u, v) for u, v in pat]
            for a, b in zip(pts, pts[1:]):
                lines.append(QLineF(a[0], a[1], b[0], b[1]))
            # continuous baseline and top border (subdivided so it stays round)
            for v in (-0.25, 1.25):
                for s in range(4):
                    a = m(base + w * s / 4, v)
                    b = m(base + w * (s + 1) / 4, v)
                    lines.append(QLineF(a[0], a[1], b[0], b[1]))
        return lines

    @staticmethod
    def _leaf(x, y, ang, length, width):
        """Lens-shaped leaf outline as lines."""
        ca, sa = math.cos(ang), math.sin(ang)
        pts_top, pts_bot = [], []
        n = 6
        for i in range(n + 1):
            u = i / n
            along = (u - 0.5) * length
            off = math.sin(u * math.pi) * width * 0.5
            for sign, arr in ((1, pts_top), (-1, pts_bot)):
                px = x + ca * along - sa * off * sign
                py = y + sa * along + ca * off * sign
                arr.append((px, py))
        lines = []
        for arr in (pts_top, pts_bot):
            for a, b in zip(arr, arr[1:]):
                lines.append(QLineF(a[0], a[1], b[0], b[1]))
        a, b = pts_top[0], pts_top[-1]
        lines.append(QLineF(a[0], a[1], b[0], b[1]))     # midrib
        return lines

    # ── drawing ─────────────────────────────────────────────────────────────
    def paint(self, p: QPainter, cx: float, cy: float, r: float,
              main: QColor, acc: QColor, bg: QColor) -> None:
        line, gold, accent, pen, e = self._paint_frame(p, cx, cy, r, main, acc, bg)
        self._paint_wreath(p, cx, cy, r, gold, pen, e)
        # the owl
        self._paint_owl(p, cx, cy + r * 0.02, r * 0.45, line, gold, accent, bg, e, pen)
        self._paint_fx(p, cx, cy, r, gold, accent, line, bg)

    def _paint_frame(self, p, cx, cy, r, main, acc, bg):
        """Glow, stars, Greek-key band, Greek letters, rings and audio ticks."""
        e = self.energy
        line = _mix(main, WHITE, 0.55)
        gold = _mix(GOLD, line, 0.25) if not self.muted else line
        accent = _mix(acc, WHITE, 0.25)

        def pen(col, k, w=1.2):
            pn = QPen(_mix(bg, col, k), w)
            pn.setCapStyle(Qt.PenCapStyle.RoundCap)
            return pn

        # 1. soft glow
        g = QRadialGradient(QPointF(cx, cy), r * 1.1)
        c0 = QColor(_mix(bg, line, 0.10 + 0.08 * e)); c0.setAlpha(255)
        c1 = QColor(_mix(bg, line, 0.03)); c1.setAlpha(150)
        c2 = QColor(bg); c2.setAlpha(0)
        g.setColorAt(0.0, c0); g.setColorAt(0.6, c1); g.setColorAt(1.0, c2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(QPointF(cx, cy), r * 1.1, r * 1.1)

        # 2. twinkling stars outside the band
        for ang, rad, size, ph in self._stars:
            tw = 0.5 + 0.5 * math.sin(self.t * 1.3 + ph)
            x, y = self._polar(cx, cy, ang + self.key_rot * 0.3, r * rad)
            p.setBrush(_mix(bg, line, 0.15 + 0.35 * tw))
            p.drawEllipse(QPointF(x, y), size * 0.7, size * 0.7)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # 3. Greek-key band
        p.setPen(pen(gold, 0.45 + 0.25 * e, 1.3))
        p.drawLines(self._meander(cx, cy, r * 0.93, r * 0.99, 40, self.key_rot))

        # 4. Greek letters ring
        fs = max(7, int(r * 0.058))
        font = QFont("Times New Roman", fs)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        p.setFont(font)
        p.setPen(pen(gold, 0.55 + 0.3 * e))
        text = TEXT * 3
        tr = r * 0.845
        step = 2 * math.pi / len(text)
        for i, ch in enumerate(text):
            a = self.text_rot + i * step
            x, y = self._polar(cx, cy, a, tr)
            p.save()
            p.translate(x, y)
            p.rotate(math.degrees(a) + 90)
            p.drawText(QPointF(-fs * 0.35, fs * 0.35), ch)
            p.restore()

        # 5. thin rings framing the text
        p.setPen(pen(line, 0.30 + 0.15 * e, 1.0))
        p.drawEllipse(QPointF(cx, cy), r * 0.905, r * 0.905)
        p.drawEllipse(QPointF(cx, cy), r * 0.785, r * 0.785)

        # 6. audio ticks
        n = len(self._tick_noise)
        ticks = []
        for i in range(n):
            a = i * 2 * math.pi / n
            wob = 0.5 + 0.5 * math.sin(self.t * 6 + i * 0.7)
            ln = r * (0.012 + 0.05 * self.amp * self._tick_noise[i] * (0.4 + 0.6 * wob)
                      + 0.006 * e)
            x1, y1 = self._polar(cx, cy, a, r * 0.745)
            x2, y2 = self._polar(cx, cy, a, r * 0.745 + ln)
            ticks.append(QLineF(x1, y1, x2, y2))
        p.setPen(pen(accent if (self.speaking and not self.muted) else line,
                     0.35 + 0.5 * e, 1.4))
        p.drawLines(ticks)
        return line, gold, accent, pen, e

    def _paint_wreath(self, p, cx, cy, r, gold, pen, e):
        # laurel wreath (two branches, gap at the top)
        wr = r * 0.66
        leaves = []
        sway = 0.015 * math.sin(self.t * 0.8)
        for side in (-1, 1):
            for i in range(15):
                u = i / 14
                a = math.pi / 2 + side * (0.25 + u * 2.35) + sway * side
                x, y = self._polar(cx, cy, a, wr)
                tang = a + side * math.pi / 2
                for off, tilt in ((1, 0.55), (-1, -0.55)):
                    lx, ly = self._polar(x, y, a, off * r * 0.035)
                    size = r * (0.085 - 0.03 * u)
                    leaves += self._leaf(lx, ly, tang + side * tilt * off, size, size * 0.42)
            # stem
            stem = []
            prev = None
            for i in range(31):
                a = math.pi / 2 + side * (0.18 + (i / 30) * 2.45) + sway * side
                pt = self._polar(cx, cy, a, wr)
                if prev:
                    stem.append(QLineF(prev[0], prev[1], pt[0], pt[1]))
                prev = pt
            leaves += stem
        p.setPen(pen(gold, 0.40 + 0.25 * e, 1.1))
        p.drawLines(leaves)

    def _paint_owl(self, p, cx, cy, s, line, gold, accent, bg, e, pen):
        def P(x, y):
            return cx + x * s, cy + y * s

        def poly(pts, closed=False):
            pts = [P(*q) for q in pts]
            if closed:
                pts.append(pts[0])
            return [QLineF(a[0], a[1], b[0], b[1]) for a, b in zip(pts, pts[1:])]

        # head / body silhouette (mirrored)
        right = [(0.0, -0.46), (0.22, -0.55), (0.46, -0.86), (0.52, -0.50),
                 (0.66, -0.20), (0.68, 0.18), (0.58, 0.52), (0.36, 0.80),
                 (0.0, 0.92)]
        left = [(-x, y) for x, y in reversed(right)]
        body = poly(left + right[1:], closed=False)
        p.setPen(pen(line, 0.65 + 0.3 * e, 1.6))
        p.drawLines(body)

        # facial disc + brows
        p.setPen(pen(line, 0.35 + 0.2 * e, 1.0))
        disc = []
        for side in (-1, 1):
            pts = []
            for i in range(25):
                a = i / 24 * 2 * math.pi
                pts.append((side * 0.27 + math.cos(a) * 0.30, -0.10 + math.sin(a) * 0.33))
            disc += poly(pts)
        p.drawLines(disc)
        p.setPen(pen(gold, 0.6 + 0.3 * e, 1.6))
        p.drawLines(poly([(-0.56, -0.44), (-0.22, -0.40), (0.0, -0.24),
                          (0.22, -0.40), (0.56, -0.44)]))

        # beak
        p.setPen(pen(gold, 0.7 + 0.3 * e, 1.4))
        p.drawLines(poly([(0, -0.18), (0.07, -0.02), (0, 0.16), (-0.07, -0.02)], closed=True))

        # chest feathers — little chevrons
        chev = []
        for row, yy in enumerate((0.36, 0.52, 0.68)):
            cnt = 4 - row
            for k in range(cnt):
                x0 = (k - (cnt - 1) / 2) * 0.17
                chev += poly([(x0 - 0.06, yy), (x0, yy + 0.05), (x0 + 0.06, yy)])
        p.setPen(pen(line, 0.30 + 0.2 * e, 1.0))
        p.drawLines(chev)

        # eyes
        lid = max(0.0, min(1.0, self.lid))
        for side in (-1, 1):
            ex, ey = P(side * 0.27, -0.10)
            R = s * 0.21
            if self.happy > 0.5:
                self._happy_eye(p, ex, ey, R, _mix(bg, gold, 0.95))
                continue
            if lid < 0.08:
                # closed: a soft arc
                p.setPen(pen(line, 0.5, 1.6))
                arc = []
                prev = None
                for i in range(13):
                    a = math.pi * (0.15 + 0.7 * i / 12)
                    pt = (ex + math.cos(a) * R, ey + math.sin(a) * R * 0.35)
                    if prev:
                        arc.append(QLineF(prev[0], prev[1], pt[0], pt[1]))
                    prev = pt
                p.drawLines(arc)
                continue
            # outer eye ring (squashed by the lid)
            p.setPen(pen(line, 0.7 + 0.3 * e, 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(ex, ey), R, R * lid)
            # rotating dashed iris ring
            iris = []
            for i in range(16):
                a0 = self.iris_rot * side + i * (2 * math.pi / 16)
                a1 = a0 + (2 * math.pi / 16) * 0.55
                x0, y0 = ex + math.cos(a0) * R * 0.72, ey + math.sin(a0) * R * 0.72 * lid
                x1, y1 = ex + math.cos(a1) * R * 0.72, ey + math.sin(a1) * R * 0.72 * lid
                iris.append(QLineF(x0, y0, x1, y1))
            p.setPen(pen(gold, 0.55 + 0.4 * e, 1.3))
            p.drawLines(iris)
            # pupil: glows and pulses with the voice
            pr = R * (0.30 + 0.12 * e + 0.18 * self.amp)
            px = ex + self.look[0] * R * 0.28
            py = ey + self.look[1] * R * 0.28 * lid
            glow = QRadialGradient(QPointF(px, py), pr * 2.4)
            gc = QColor(accent if not self.muted else line)
            g0 = QColor(gc); g0.setAlpha(int(110 + 120 * e))
            g1 = QColor(gc); g1.setAlpha(0)
            glow.setColorAt(0.0, g0); glow.setColorAt(1.0, g1)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(glow))
            p.drawEllipse(QPointF(px, py), pr * 2.4, pr * 2.4 * lid)
            p.setBrush(_mix(gc, WHITE, 0.35))
            p.drawEllipse(QPointF(px, py), pr, pr * lid)
            p.setBrush(WHITE)
            p.drawEllipse(QPointF(px - pr * 0.35, py - pr * 0.35 * lid), pr * 0.25, pr * 0.25 * lid)
            p.setBrush(Qt.BrushStyle.NoBrush)
