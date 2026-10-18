"""
Neural sphere — a rotating globe of circuit traces for the HUD centre.

A slowly turning sphere made of short "circuit" paths that run along its
latitudes and longitudes, ending in small nodes, wrapped in tilted orbit
rings and long chords, with a glowing core and a fast spinning gyroscope in
the middle. Software QPainter + numpy only, like the rest of the HUD.

Everything reacts to the assistant:
  * idle      — slow turn, soft core
  * listening — a bit faster, core follows your voice level
  * thinking  — faster spin, pulses race along the traces
  * speaking  — sphere breathes with the voice, core flares
  * muted     — almost still, dim

`paint()` takes its colours as arguments, so the accent picker retints it.
"""

from __future__ import annotations

import math
import random

import numpy as np
from PyQt6.QtCore import QLineF, QPointF, QRectF
from PyQt6.QtGui import (QColor, QPainter, QPen, QRadialGradient, QBrush)
from PyQt6.QtCore import Qt


def _mix(a: QColor, b: QColor, k: float) -> QColor:
    k = max(0.0, min(1.0, k))
    return QColor(int(a.red() + (b.red() - a.red()) * k),
                  int(a.green() + (b.green() - a.green()) * k),
                  int(a.blue() + (b.blue() - a.blue()) * k))


def _sph(lat: float, lon: float, rad: float = 1.0):
    cl = math.cos(lat)
    return (rad * cl * math.sin(lon), rad * math.sin(lat), rad * cl * math.cos(lon))


def _rot(axis_tilt: float, yaw: float) -> np.ndarray:
    """Rotation: yaw around Y, then tilt around X."""
    cy, sy = math.cos(yaw), math.sin(yaw)
    ct, st = math.cos(axis_tilt), math.sin(axis_tilt)
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rx = np.array([[1, 0, 0], [0, ct, -st], [0, st, ct]])
    return rx @ ry


class NeuralSphere:
    N_LEVELS = 6          # depth buckets — one pen per bucket keeps it fast

    def __init__(self, seed: int = 7) -> None:
        rnd = random.Random(seed)

        # ── circuit traces on the surface ────────────────────────────────
        segs = []          # (p0, p1)
        nodes = []         # end points
        self._trace_paths = []   # list of point lists (for travelling pulses)
        for _ in range(230):
            rad = rnd.uniform(0.93, 1.0)
            lat = math.asin(rnd.uniform(-0.97, 0.97))
            lon = rnd.uniform(0, 2 * math.pi)
            pts = [_sph(lat, lon, rad)]
            along_lat = rnd.random() < 0.5
            for _k in range(rnd.randint(2, 6)):
                if along_lat:
                    step = rnd.uniform(0.06, 0.22) * rnd.choice((-1, 1))
                    n = max(2, int(abs(step) / 0.04))
                    for j in range(1, n + 1):
                        pts.append(_sph(lat, lon + step * j / n, rad))
                    lon += step
                else:
                    step = rnd.uniform(0.04, 0.14) * rnd.choice((-1, 1))
                    lat = max(-1.45, min(1.45, lat + step))
                    pts.append(_sph(lat, lon, rad))
                along_lat = not along_lat
            for a, b in zip(pts, pts[1:]):
                segs.append((a, b))
            nodes.append(pts[-1])
            if rnd.random() < 0.35:
                nodes.append(pts[0])
            self._trace_paths.append(np.array(pts))
        self._seg_a = np.array([s[0] for s in segs])
        self._seg_b = np.array([s[1] for s in segs])
        self._nodes = np.array(nodes)

        # small "chips" — tiny rectangles outlined on the surface
        chips = []
        for _ in range(26):
            lat = math.asin(rnd.uniform(-0.9, 0.9))
            lon = rnd.uniform(0, 2 * math.pi)
            dl, dn = rnd.uniform(0.04, 0.08), rnd.uniform(0.06, 0.14)
            c = [(lat, lon), (lat, lon + dn), (lat + dl, lon + dn), (lat + dl, lon)]
            for i in range(4):
                a, b = c[i], c[(i + 1) % 4]
                chips.append((_sph(*a, 0.99), _sph(*b, 0.99)))
        self._chip_a = np.array([c[0] for c in chips])
        self._chip_b = np.array([c[1] for c in chips])

        # long chords through the interior
        chords = []
        for _ in range(14):
            a = _sph(math.asin(rnd.uniform(-1, 1)), rnd.uniform(0, 6.283))
            b = _sph(math.asin(rnd.uniform(-1, 1)), rnd.uniform(0, 6.283))
            chords.append((a, b))
        self._chord_a = np.array([c[0] for c in chords])
        self._chord_b = np.array([c[1] for c in chords])

        # great circles / orbits (radius, tilt_x, tilt_z, own spin speed)
        self._orbits = [
            (1.00, 0.20, 0.00, 0.00),
            (0.98, 1.20, 0.35, 0.00),
            (1.00, -0.55, 1.10, 0.00),
            (1.10, 1.35, -0.25, 0.18),
            (1.16, 0.45, 0.75, -0.12),
            (0.62, 0.90, 0.20, 0.30),
            (0.45, -0.30, 0.60, -0.25),
        ]
        th = np.linspace(0, 2 * math.pi, 97)
        self._circle = np.stack([np.cos(th), np.zeros_like(th), np.sin(th)], 1)

        # faint dust inside the sphere
        d = []
        for _ in range(140):
            r = rnd.uniform(0.15, 0.95) ** 0.6
            d.append(_sph(math.asin(rnd.uniform(-1, 1)), rnd.uniform(0, 6.283), r))
        self._dust = np.array(d)

        # pulses travelling along traces: [path index, progress 0..1, speed]
        self._pulses = [[rnd.randrange(len(self._trace_paths)), rnd.random(),
                         rnd.uniform(0.4, 1.0)] for _ in range(18)]
        self._rnd = rnd

        # animated state
        self.yaw = 0.0
        self.tilt = 0.32
        self.core_spin = 0.0
        self.t = 0.0
        self.amp = 0.0
        self.energy = 0.3        # smoothed 0..1 activity
        self.pulse_on = 0.0
        self.scale = 1.0

    # ── animation ───────────────────────────────────────────────────────────
    def step(self, dt: float, amp: float, speaking: bool = False,
             muted: bool = False, state: str = "") -> None:
        dt = max(0.0, min(0.1, dt))
        self.t += dt
        self.amp += (amp - self.amp) * min(1.0, dt * 12)

        thinking = state in ("THINKING", "PROCESSING")
        if muted:
            target_e, spin = 0.05, 0.03
        elif speaking:
            target_e, spin = 0.75 + self.amp * 0.25, 0.22 + self.amp * 0.35
        elif thinking:
            target_e, spin = 0.65, 0.45
        elif state == "LISTENING":
            target_e, spin = 0.40 + self.amp * 0.4, 0.14 + self.amp * 0.2
        else:
            target_e, spin = 0.30, 0.10
        self.energy += (target_e - self.energy) * min(1.0, dt * 3)
        self.pulse_on += ((1.0 if (thinking or speaking) else 0.25)
                          - self.pulse_on) * min(1.0, dt * 2)

        self.yaw += spin * dt
        self.tilt = 0.32 + 0.06 * math.sin(self.t * 0.21)
        self.core_spin += (1.2 + self.energy * 3.0) * dt
        breath = 0.012 * math.sin(self.t * 1.3)
        tgt_scale = 1.0 + breath + (self.amp * 0.07 if speaking else self.amp * 0.03)
        self.scale += (tgt_scale - self.scale) * min(1.0, dt * 10)

        for pl in self._pulses:
            pl[1] += pl[2] * dt * (0.4 + self.energy)
            if pl[1] >= 1.0:
                pl[0] = self._rnd.randrange(len(self._trace_paths))
                pl[1] = 0.0
                pl[2] = self._rnd.uniform(0.4, 1.0)

    # ── drawing ─────────────────────────────────────────────────────────────
    def _project(self, pts: np.ndarray, R: np.ndarray, cx, cy, r):
        q = pts @ R.T
        persp = 1.0 / (1.0 - q[:, 2] * 0.12)
        x = cx + q[:, 0] * r * persp
        y = cy - q[:, 1] * r * persp
        return x, y, q[:, 2]

    def _bucket(self, z: np.ndarray) -> np.ndarray:
        # z in [-1.2, 1.2] -> 0..N-1 (0 = far back)
        k = ((z + 1.0) / 2.0 * self.N_LEVELS).astype(int)
        return np.clip(k, 0, self.N_LEVELS - 1)

    def _pens(self, line: QColor, bg: QColor, lo: float, hi: float, w: float):
        pens = []
        for i in range(self.N_LEVELS):
            k = lo + (hi - lo) * (i / (self.N_LEVELS - 1)) ** 1.4
            pen = QPen(_mix(bg, line, k), w)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            pens.append(pen)
        return pens

    def _draw_segs(self, p, a, b, R, cx, cy, r, pens):
        xa, ya, za = self._project(a, R, cx, cy, r)
        xb, yb, zb = self._project(b, R, cx, cy, r)
        bk = self._bucket((za + zb) * 0.5)
        for i in range(self.N_LEVELS):
            idx = np.nonzero(bk == i)[0]
            if idx.size == 0:
                continue
            p.setPen(pens[i])
            p.drawLines([QLineF(xa[j], ya[j], xb[j], yb[j]) for j in idx])

    def paint(self, p: QPainter, cx: float, cy: float, r: float,
              main: QColor, acc: QColor, bg: QColor) -> None:
        r = r * self.scale
        e = self.energy
        white = QColor(225, 240, 250)
        line = _mix(main, white, 0.68)          # pale, slightly tinted
        bright = _mix(line, white, 0.5)
        accent = _mix(acc, white, 0.35)

        R = _rot(self.tilt, self.yaw)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # 1. soft atmosphere behind everything
        g = QRadialGradient(QPointF(cx, cy), r * 1.15)
        c0 = QColor(_mix(bg, line, 0.10 + 0.08 * e)); c0.setAlpha(255)
        c1 = QColor(_mix(bg, line, 0.03)); c1.setAlpha(160)
        c2 = QColor(bg); c2.setAlpha(0)
        g.setColorAt(0.0, c0); g.setColorAt(0.55, c1); g.setColorAt(1.0, c2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(QPointF(cx, cy), r * 1.15, r * 1.15)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # 2. interior dust
        x, y, z = self._project(self._dust, R, cx, cy, r)
        p.setPen(QPen(_mix(bg, line, 0.25 + 0.15 * e), 1.2))
        p.drawPoints([QPointF(x[i], y[i]) for i in range(len(x))])

        # 3. chords through the inside
        self._draw_segs(p, self._chord_a, self._chord_b, R, cx, cy, r,
                        self._pens(line, bg, 0.06, 0.28 + 0.1 * e, 1.0))

        # 4. orbits / great circles
        orb_pens = self._pens(line, bg, 0.05, 0.42 + 0.15 * e, 1.0)
        for (rad, tx, tz, spd) in self._orbits:
            Ro = R @ _rot(tx, self.t * spd) @ np.array(
                [[math.cos(tz), -math.sin(tz), 0], [math.sin(tz), math.cos(tz), 0], [0, 0, 1]])
            pts = self._circle * rad
            a, b = pts[:-1], pts[1:]
            self._draw_segs(p, a, b, Ro, cx, cy, r, orb_pens)

        # 5. circuit traces and chips
        trace_pens = self._pens(line, bg, 0.06, 0.62 + 0.3 * e, 1.0)
        self._draw_segs(p, self._seg_a, self._seg_b, R, cx, cy, r, trace_pens)
        self._draw_segs(p, self._chip_a, self._chip_b, R, cx, cy, r,
                        self._pens(line, bg, 0.05, 0.55, 1.0))

        # 6. nodes (front ones brighter and larger)
        x, y, z = self._project(self._nodes, R, cx, cy, r)
        bk = self._bucket(z)
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(self.N_LEVELS):
            idx = np.nonzero(bk == i)[0]
            if idx.size == 0:
                continue
            k = 0.08 + 0.75 * (i / (self.N_LEVELS - 1)) ** 1.4
            p.setBrush(_mix(bg, bright, k))
            s = 0.7 + 0.8 * i / (self.N_LEVELS - 1)
            for j in idx:
                p.drawEllipse(QPointF(x[j], y[j]), s, s)

        # 7. pulses running along traces
        if self.pulse_on > 0.05:
            for pi, prog, _sp in self._pulses:
                path = self._trace_paths[pi]
                f = prog * (len(path) - 1)
                i0 = int(f); i1 = min(i0 + 1, len(path) - 1); u = f - i0
                pt = path[i0] * (1 - u) + path[i1] * u
                px, py, pz = self._project(pt[None, :], R, cx, cy, r)
                if pz[0] < -0.2:
                    continue
                k = self.pulse_on * (0.5 + 0.5 * (pz[0] + 0.2) / 1.2)
                p.setBrush(_mix(bg, accent, k))
                p.drawEllipse(QPointF(px[0], py[0]), 2.2, 2.2)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # 8. glowing core
        cr = r * (0.20 + 0.05 * e + 0.08 * self.amp)
        g = QRadialGradient(QPointF(cx, cy), cr * 1.8)
        a0 = QColor(_mix(line, white, 0.6)); a0.setAlpha(int(150 + 100 * e))
        a1 = QColor(line); a1.setAlpha(int(60 + 60 * e))
        a2 = QColor(line); a2.setAlpha(0)
        g.setColorAt(0.0, a0); g.setColorAt(0.25, a1); g.setColorAt(1.0, a2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(QPointF(cx, cy), cr * 1.8, cr * 1.8)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # 9. gyroscope rings around the core
        gyro = [(0.0, 1.0, 0.35), (1.1, -1.4, 0.30), (2.0, 0.8, 0.26), (0.6, 2.1, 0.40)]
        gyro_pens = self._pens(bright, bg, 0.25, 0.85 + 0.15 * e, 1.1)
        for k, (tx, mul, rad) in enumerate(gyro):
            Rg = _rot(tx + 0.3 * math.sin(self.t * 0.5 + k), self.core_spin * mul)
            pts = self._circle * rad * (1.0 + 0.15 * self.amp)
            self._draw_segs(p, pts[:-1], pts[1:], Rg, cx, cy, r, gyro_pens)
        # bright centre point
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_mix(bright, white, 0.7))
        p.drawEllipse(QPointF(cx, cy), 2.5 + 2 * self.amp, 2.5 + 2 * self.amp)
        p.setBrush(Qt.BrushStyle.NoBrush)
