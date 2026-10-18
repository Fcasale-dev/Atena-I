"""
Athena owl 3D — a sculpted, front-facing owl with open wings inside the Athena
frame (Greek-key border, golden ring of Greek letters, audio ticks).

The owl is made of ~500 individual 3D feathers (body plumage in overlapping
rows, a round head with a heart-shaped facial disc of tiny radial feathers,
ear tufts, broad wings with coverts, secondaries and long primaries, tail fan),
each a curved teardrop with its own normal. Every frame they are posed,
lit from the top-left, depth-sorted and painted back to front, which gives a
carved, holographic look. Colours follow the HUD theme.

No mouse interaction. She reacts to what ATENA is doing:
  * idle      — breathes, sways, turns her head to look around now and then,
                occasionally stretches her wings
  * listening — faces you and leans in, wings lift, eyes glow
  * thinking  — tilts her head side to side, eyes glance around
  * speaking  — wings beat with the voice, small nods, pupils pulse
  * muted / asleep — wings fold, head lowers, eyes closed
"""

from __future__ import annotations

import math
import random

import numpy as np
from PyQt6.QtCore import QLineF, QPointF, Qt
from PyQt6.QtGui import QBrush, QColor, QPen, QPolygonF, QRadialGradient

from core.athena_hud import AthenaEmblem, _mix, WHITE

# feather outline template: (s along the feather 0..1, t across -1..1)
_K = 8
_S = np.concatenate([np.linspace(0.0, 1.0, _K), np.linspace(1.0, 0.0, _K)])
_PROFILE = np.sin(np.pi * np.clip(_S, 0, 1) ** 0.75) * (1.0 - 0.25 * _S)
_T = np.concatenate([np.ones(_K), -np.ones(_K)]) * _PROFILE
_LIGHT = np.array([-0.45, 0.65, 0.62])
_LIGHT = _LIGHT / np.linalg.norm(_LIGHT)

G_BODY, G_HEAD, G_WING_R, G_WING_L, G_TAIL = 0, 1, 2, 3, 4


def _rot(yaw: float, pitch: float, roll: float = 0.0) -> np.ndarray:
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cr, sr = math.cos(roll), math.sin(roll)
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return rz @ rx @ ry


def _rotz(ang: float) -> np.ndarray:
    c, s = math.cos(ang), math.sin(ang)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


class AthenaOwl3D(AthenaEmblem):
    NECK = np.array([0.0, 0.20, 0.0])
    SHOULDER = np.array([0.36, 0.12, -0.02])

    def __init__(self) -> None:
        super().__init__()
        self.yaw = 0.0
        self.pitch = 0.08
        self.head_yaw = 0.0
        self.head_tilt = 0.0
        self.head_drop = 0.0
        self.flap = 0.0
        self.spread = 0.12
        self._flap_angle = 0.12
        self._rnd = random.Random(5)
        self._next_glance = 3.0
        self._glance_target = 0.0
        self._next_stretch = 18.0
        self._stretch = 0.0
        self._build()

    # kept so older canvases calling these never break; they do nothing now
    def look_at(self, *_a, **_k) -> None:
        pass

    def poke(self) -> None:
        pass

    # ── model ───────────────────────────────────────────────────────────────
    def _build(self) -> None:
        F = []   # (base, U, normal, length, width, group, bias, tone)

        def add(base, U, n, L, W, g, bias=0.0, tone=0.0):
            U = _unit(U)
            n = _unit(np.asarray(n, float) - np.dot(n, U) * U)
            F.append((np.asarray(base, float), U, n, L, W, g, bias, tone))

        # body: ellipsoid, rows of feathers pointing down, upper rows on top
        bc, br = np.array([0.0, -0.28, 0.02]), np.array([0.52, 0.66, 0.44])
        rows = 12
        for row in range(rows):
            y = 0.22 - row * (1.10 / (rows - 1))
            sphi = (y - bc[1]) / br[1]
            if abs(sphi) >= 0.99:
                continue
            cphi = math.sqrt(1 - sphi * sphi)
            n_a = 11
            off = 0.5 if row % 2 else 0.0
            for k in range(n_a):
                a = -1.75 + (k + off) * (3.5 / n_a)
                p = bc + br * np.array([cphi * math.sin(a), sphi, cphi * math.cos(a)])
                nrm = _unit((p - bc) / (br * br))
                down = np.array([0.0, -1.0, 0.0])
                U = down - np.dot(down, nrm) * nrm
                size = 0.75 + 0.35 * cphi
                add(p + nrm * 0.005 * (rows - row), U, nrm, 0.21 * size, 0.11 * size,
                    G_BODY, bias=0.0, tone=0.05 * math.sin(k * 1.7 + row))

        # head: crown feathers (top/back), facial disc rings, ear tufts
        hc, hr = np.array([0.0, 0.56, 0.02]), np.array([0.47, 0.41, 0.40])
        for row in range(6):
            lat = 1.35 - row * 0.22
            for k in range(12):
                a = -2.2 + (k + 0.5 * (row % 2)) * (4.4 / 12)
                p = hc + hr * np.array([math.cos(lat) * math.sin(a), math.sin(lat),
                                        math.cos(lat) * math.cos(a)])
                if p[2] > 0.18 and p[1] < 0.80:   # leave the face for the disc
                    continue
                nrm = _unit((p - hc) / (hr * hr))
                U = np.array([0.0, -0.4, -1.0]) - np.dot([0.0, -0.4, -1.0], nrm) * nrm
                add(p, U, nrm, 0.13, 0.075, G_HEAD, bias=0.01)
        # facial disc: two fans of fine radial feathers around the eyes
        for side in (-1, 1):
            ec = np.array([side * 0.19, 0.55, 0.34])
            for ring, (rr, cnt, L) in enumerate(((0.10, 10, 0.07), (0.15, 14, 0.08),
                                                 (0.20, 18, 0.09), (0.25, 22, 0.10))):
                for k in range(cnt):
                    a = k * 2 * math.pi / cnt + ring * 0.2
                    d = np.array([math.cos(a), math.sin(a), 0.0])
                    if side * d[0] < -0.75 and ring > 0:   # rings meet at the centre
                        continue
                    p = ec + d * rr + np.array([0, 0, -0.10 * rr])
                    nrm = _unit([d[0] * 0.5 + side * 0.15, d[1] * 0.5 + 0.1, 1.0])
                    add(p, d + np.array([0, 0, -0.25]), nrm, L, 0.045,
                        G_HEAD, bias=0.03 + 0.005 * (3 - ring), tone=0.08)
        # brow / centre ridge feathers between the eyes
        for k in range(5):
            y = 0.70 - k * 0.07
            add([0.0, y, 0.38], [0, -1, 0.15], [0, 0.3, 1], 0.09, 0.05, G_HEAD,
                bias=0.06, tone=0.1)
        # ear tufts
        for side in (-1, 1):
            for j in range(4):
                base = np.array([side * (0.20 + 0.05 * j), 0.86 - 0.03 * j, 0.10])
                U = np.array([side * (0.25 + 0.12 * j), 1.0, -0.05])
                add(base, U, [side * 0.2, 0.0, 1.0], 0.30 - 0.04 * j, 0.06,
                    G_HEAD, bias=0.02 - 0.003 * j, tone=0.12)

        # wings (right template; left mirrored)
        def lead(u):
            return self.SHOULDER + np.array([u * 1.55, 0.60 * math.sin(u * math.pi * 0.72),
                                             -0.14 * u])

        def fdir(u):
            ang = -math.pi / 2 + 0.75 * u ** 1.4
            return np.array([math.cos(ang), math.sin(ang), -0.03])

        def chord(u):
            return 0.95 * (1 - u) ** 0.45 + 0.32

        wing = []
        for i in range(10):                        # primaries
            u = 0.52 + 0.48 * i / 9
            L = chord(u) * (1.05 + 0.6 * (u - 0.5))
            wing.append((lead(u) + fdir(u) * 0.05, fdir(u), [0.05, 0.1, 1.0], L, 0.14, 0.0, 0.10))
        for i in range(11):                        # secondaries
            u = 0.04 + 0.48 * i / 10
            wing.append((lead(u) + fdir(u) * 0.05, fdir(u), [0.0, 0.1, 1.0], chord(u) * 0.95,
                         0.13, 0.01, 0.06))
        for r_i, (frac, cnt, L, W) in enumerate(((0.52, 14, 0.30, 0.10), (0.34, 16, 0.24, 0.09),
                                                 (0.18, 17, 0.18, 0.08), (0.05, 18, 0.13, 0.065))):
            for i in range(cnt):                   # covert rows, leading edge on top
                u = 0.02 + 0.88 * (i + 0.5 * (r_i % 2)) / cnt
                base = lead(u) + fdir(u) * chord(u) * frac * 0.9
                wing.append((base, fdir(u), [0.0, 0.25, 1.0], L * (1 - 0.35 * u), W,
                             0.02 + 0.01 * r_i, 0.0))
        for base, U, n, L, W, bias, tone in wing:
            add(base, U, n, L, W, G_WING_R, bias, tone)
            m = np.array([-1.0, 1.0, 1.0])
            add(base * m, np.asarray(U) * m, np.asarray(n) * m, L, W, G_WING_L, bias, tone)

        # tail fan (behind the body)
        for a in np.linspace(-0.55, 0.55, 9):
            add([math.sin(a) * 0.08, -0.78, -0.10], [math.sin(a), -1.0, -0.1],
                [0, 0, 1], 0.42, 0.10, G_TAIL, bias=-0.3)

        base = np.array([f[0] for f in F])
        U = np.array([f[1] for f in F])
        nrm = np.array([f[2] for f in F])
        L = np.array([f[3] for f in F])[:, None, None]
        W = np.array([f[4] for f in F])[:, None, None]
        V = np.cross(nrm, U)
        s = _S[None, :, None]
        t = _T[None, :, None]
        # outline vertices with a gentle curl: tips lift off the surface
        self._verts = (base[:, None, :] + U[:, None, :] * s * L + V[:, None, :] * t * W
                       + nrm[:, None, :] * (0.25 * W * s ** 2 + 0.06 * W * (1 - t ** 2)))
        self._normals = nrm
        self._group = np.array([f[5] for f in F])
        self._bias = np.array([f[6] for f in F])
        self._tone = np.array([f[7] for f in F])
        self._eyes = np.array([[-0.19, 0.55, 0.40], [0.19, 0.55, 0.40]])
        self._beak = np.array([[0.0, 0.53, 0.44], [0.055, 0.44, 0.46],
                               [0.0, 0.31, 0.44], [-0.055, 0.44, 0.46]])

        # olive branch + talons (lines, drawn in front)
        segs = []
        br_pts = [np.array([x, -0.94 + 0.04 * math.sin(x * 2.2), 0.10]) for x in np.linspace(-1.0, 1.0, 17)]
        segs += list(zip(br_pts, br_pts[1:]))
        for j, x in enumerate(np.linspace(-0.9, 0.9, 10)):
            y = -0.94 + 0.04 * math.sin(x * 2.2)
            up = 1 if j % 2 else -1
            dx, dy = 0.10 * (1 if x > 0 else -1), 0.17 * up
            nn = math.hypot(dx, dy)
            nx, ny = -dy / nn, dx / nn
            top, bot = [], []
            for u in np.linspace(0, 1, 7):
                off = math.sin(u * math.pi) * 0.045
                top.append(np.array([x + dx * u + nx * off, y + dy * u + ny * off, 0.12]))
                bot.append(np.array([x + dx * u - nx * off, y + dy * u - ny * off, 0.12]))
            segs += list(zip(top, top[1:])) + list(zip(bot, bot[1:])) + [(top[0], top[-1])]
        talon = []
        for side in (-1, 1):
            b0 = np.array([side * 0.17, -0.84, 0.22])
            for k in (-1, 0, 1):
                toe = [b0 + np.array([k * 0.055, -0.07 * t - 0.03 * t * t, 0.05 * t * (1 - t)])
                       for t in np.linspace(0, 1.4, 6)]
                talon += list(zip(toe, toe[1:]))
        self._branch = (np.array([a for a, _ in segs]), np.array([b for _, b in segs]))
        self._talons = (np.array([a for a, _ in talon]), np.array([b for _, b in talon]))

    # ── animation ───────────────────────────────────────────────────────────
    def step(self, dt: float, amp: float, speaking: bool = False,
             muted: bool = False, state: str = "") -> None:
        super().step(dt, amp, speaking, muted, state)
        dt = max(0.0, min(0.1, dt))
        thinking = state in ("THINKING", "PROCESSING")
        listening = state == "LISTENING" and not speaking
        asleep = self.sleep_pose            # includes "boa noite"
        happy = self.mood == "happy"

        def k(rate):
            return min(1.0, dt * rate)

        tgt_yaw = 0.16 * math.sin(self.t * 0.22)
        tgt_pitch = 0.08 + 0.03 * math.sin(self.t * 0.31)
        if listening:
            tgt_yaw *= 0.3
            tgt_pitch = 0.16 + 0.08 * self.amp
        if speaking:
            tgt_pitch = 0.08 + 0.07 * self.amp * math.sin(self.t * 9)
        self.yaw += (tgt_yaw - self.yaw) * k(2)
        self.pitch += (tgt_pitch - self.pitch) * k(4)

        self._next_glance -= dt
        if self._next_glance <= 0:
            self._glance_target = self._rnd.choice((-0.7, -0.45, 0.0, 0.0, 0.45, 0.7))
            self._next_glance = self._rnd.uniform(3.0, 7.0)
        if asleep:
            hy, ht, hd = 0.0, 0.0, 1.0
        elif happy:
            hy, ht, hd = 0.0, 0.22 * math.sin(self.t * 5.0), 0.0   # happy head bob
        elif listening or speaking:
            hy, ht, hd = 0.0, 0.0, 0.0
        elif thinking:
            hy, ht, hd = 0.25 * math.sin(self.t * 0.9), 0.28 * math.sin(self.t * 1.6), 0.0
        else:
            hy, ht, hd = self._glance_target, 0.06 * math.sin(self.t * 0.5), 0.0
        self.head_yaw += (hy - self.head_yaw) * k(3.5)
        self.head_tilt += (ht - self.head_tilt) * k(3)
        self.head_drop += (hd - self.head_drop) * k(1.5)
        if not thinking:
            self._look_target = [self.head_yaw * 0.6, 0.0]

        self._next_stretch -= dt
        if self._next_stretch <= 0 and not (asleep or speaking or thinking):
            self._stretch = 1.0
            self._next_stretch = self._rnd.uniform(18, 35)
        self._stretch = max(0.0, self._stretch - dt * 0.45)

        if asleep:
            tgt_spread, rate, depth = -0.60, 0.6, 0.02
        elif happy:
            tgt_spread, rate, depth = 0.35, 6.0, 0.28        # joyful flapping
        elif speaking:
            tgt_spread, rate, depth = 0.14, 3.0 + 4.0 * self.amp, 0.10 + 0.32 * self.amp
        elif thinking:
            tgt_spread, rate, depth = 0.10, 1.6, 0.05
        elif listening:
            tgt_spread, rate, depth = 0.22, 1.2, 0.05
        else:
            tgt_spread, rate, depth = 0.12, 0.9, 0.035
        tgt_spread += 0.42 * math.sin(math.pi * self._stretch)
        self.spread += (tgt_spread - self.spread) * k(2.5)
        self.flap += rate * dt
        self._flap_angle = self.spread + depth * math.sin(self.flap)

    # ── posing ──────────────────────────────────────────────────────────────
    def _pose(self):
        """World-space vertices and normals for the current frame."""
        V = self._verts.copy()
        N = self._normals.copy()
        g = self._group
        # head: turn + tilt around the neck, drop when asleep
        Rh = _rot(self.head_yaw, -0.25 * self.head_drop, self.head_tilt)
        hm = g == G_HEAD
        V[hm] = (V[hm] - self.NECK) @ Rh.T + self.NECK + np.array([0, -0.05 * self.head_drop, 0])
        N[hm] = N[hm] @ Rh.T
        # wings: flap around the shoulders
        for grp, sign in ((G_WING_R, 1.0), (G_WING_L, -1.0)):
            m = g == grp
            Rw = _rotz(sign * self._flap_angle)
            piv = self.SHOULDER * np.array([sign, 1.0, 1.0])
            V[m] = (V[m] - piv) @ Rw.T + piv
            N[m] = N[m] @ Rw.T
        return V, N, Rh

    def _project(self, pts, R, cx, cy, s):
        q = pts @ R.T
        persp = 1.0 / (1.0 - q[..., 2] * 0.16)
        return cx + q[..., 0] * s * persp, cy - q[..., 1] * s * persp, q[..., 2]

    # ── drawing ─────────────────────────────────────────────────────────────
    def paint(self, p, cx, cy, r, main, acc, bg) -> None:
        line, gold, accent, pen, e = self._paint_frame(p, cx, cy, r, main, acc, bg)
        s = r * 0.335
        ocy = cy + r * 0.07
        R = _rot(self.yaw, self.pitch)

        V, N, Rh = self._pose()
        X, Y, Z = self._project(V, R, cx, ocy, s)
        Nw = N @ R.T
        shade = np.clip(Nw @ _LIGHT, 0.0, 1.0)
        facing = np.clip(Nw[:, 2], 0.0, 1.0)
        depth = Z.mean(axis=1) + self._bias
        order = np.argsort(depth)

        wing_col = _mix(line, gold, 0.20)
        head_col = _mix(line, gold, 0.08)
        cols = {G_BODY: line, G_HEAD: head_col, G_WING_R: wing_col,
                G_WING_L: wing_col, G_TAIL: line}
        rim_k = 0.10 + 0.12 * e
        for i in order:
            if facing[i] < 0.02 and self._group[i] != G_TAIL:
                continue                               # back-facing, hidden
            base = cols[int(self._group[i])]
            lit = 0.04 + 0.62 * shade[i] ** 1.4 + 0.08 * self._tone[i] + 0.06 * e
            fill = _mix(bg, base, lit)
            rim = _mix(bg, _mix(base, WHITE, 0.15), min(1.0, lit * 1.25 + rim_k))
            p.setBrush(fill)
            pn = QPen(rim, 0.9)
            pn.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pn)
            xs, ys = X[i], Y[i]
            p.drawPolygon(QPolygonF([QPointF(xs[j], ys[j]) for j in range(len(xs))]))
        p.setBrush(Qt.BrushStyle.NoBrush)

        # branch and talons (gold lines)
        for (a, b), lo, hi, w in ((self._branch, 0.25, 0.75, 1.3), (self._talons, 0.4, 0.95, 1.6)):
            xa, ya, _ = self._project(a, R, cx, ocy, s)
            xb, yb, _ = self._project(b, R, cx, ocy, s)
            p.setPen(QPen(_mix(bg, gold, hi), w))
            p.drawLines([QLineF(xa[j], ya[j], xb[j], yb[j]) for j in range(len(xa))])

        # beak (follows the head)
        head_off = np.array([0, -0.05 * self.head_drop, 0])
        bk = (self._beak - self.NECK) @ Rh.T + self.NECK + head_off
        bx, by, _ = self._project(bk, R, cx, ocy, s)
        p.setBrush(_mix(bg, gold, 0.55 + 0.25 * e))
        p.setPen(QPen(_mix(bg, gold, 0.95), 1.0))
        p.drawPolygon(QPolygonF([QPointF(bx[j], by[j]) for j in range(4)]))
        p.setBrush(Qt.BrushStyle.NoBrush)

        # eyes
        eyes = (self._eyes - self.NECK) @ Rh.T + self.NECK + head_off
        ex, ey, ez = self._project(eyes, R, cx, ocy, s)
        lid = max(0.0, min(1.0, self.lid))
        Rr = s * 0.13
        for i in range(2):
            vis = 0.30 + 0.70 * max(0.0, min(1.0, (ez[i] + 0.1) / 0.5))
            # dark socket
            p.setPen(QPen(_mix(bg, gold, 0.7 * vis), 1.4))
            p.setBrush(_mix(bg, line, 0.06))
            p.drawEllipse(QPointF(ex[i], ey[i]), Rr * 1.05, Rr * 1.05 * max(lid, 0.12))
            if self.happy > 0.5:
                self._happy_eye(p, ex[i], ey[i], Rr, _mix(bg, gold, 0.95 * vis))
                continue
            if lid < 0.08:
                p.setPen(QPen(_mix(bg, line, 0.7 * vis), 1.6))
                p.drawLine(QLineF(ex[i] - Rr, ey[i], ex[i] + Rr, ey[i]))
                continue
            iris = []
            for kq in range(14):
                a0 = self.iris_rot * (1 if i else -1) + kq * (2 * math.pi / 14)
                a1 = a0 + (2 * math.pi / 14) * 0.55
                iris.append(QLineF(ex[i] + math.cos(a0) * Rr * 0.85, ey[i] + math.sin(a0) * Rr * 0.85 * lid,
                                   ex[i] + math.cos(a1) * Rr * 0.85, ey[i] + math.sin(a1) * Rr * 0.85 * lid))
            p.setPen(QPen(_mix(bg, gold, (0.55 + 0.4 * e) * vis), 1.2))
            p.drawLines(iris)
            pr = Rr * (0.42 + 0.15 * e + 0.22 * self.amp)
            px = ex[i] + self.look[0] * Rr * 0.25
            py = ey[i] - self.look[1] * Rr * 0.25 * lid
            gc = QColor(accent if not self.muted else line)
            glow = QRadialGradient(QPointF(px, py), pr * 2.6)
            g0 = QColor(gc); g0.setAlpha(int((110 + 130 * e) * vis))
            g1 = QColor(gc); g1.setAlpha(0)
            glow.setColorAt(0.0, g0); glow.setColorAt(1.0, g1)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(glow))
            p.drawEllipse(QPointF(px, py), pr * 2.6, pr * 2.6 * lid)
            p.setBrush(_mix(bg, _mix(gc, WHITE, 0.35), vis))
            p.drawEllipse(QPointF(px, py), pr, pr * lid)
            p.setBrush(WHITE)
            p.drawEllipse(QPointF(px - pr * 0.35, py - pr * 0.35 * lid), pr * 0.28, pr * 0.28 * lid)
            p.setBrush(Qt.BrushStyle.NoBrush)

        self._paint_fx(p, cx, cy - r * 0.10, r, gold, accent, line, bg)
