"""
RVC voice conversion for JARVIS — client side.

Jarvis keeps Gemini Live for thinking and speaking; this module converts the
voice it plays into an RVC voice (e.g. Cortana) using a separate engine process
(voice_engine/rvc_server.py running on the RVC AMD/Intel DirectML runtime).

Design:
  * The engine is started in the background when Jarvis launches. Until it
    reports ready — or if it ever fails — audio passes through unchanged, so
    Jarvis is never left mute.
  * Audio is converted in ~0.8 s blocks with 0.3 s of left context and a 20 ms
    crossfade, which hides the seams between blocks.

Layout:
  <Jarvis>/voice_engine/rvc/          ← RVC1006AMD_Intel (installed by instalar_voz.bat)
  <Jarvis>/voices/<name>/model.pth    ← your voice model (+ .index, voice.json)
"""

from __future__ import annotations

import json
import os
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np

SR = 24000
BLOCK = int(0.80 * SR)      # new audio per conversion
CTX = int(0.30 * SR)        # left context re-sent with each block
XF = int(0.02 * SR)         # crossfade length
PORT = 18888


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE = _base_dir()
ENGINE_DIR = BASE / "voice_engine"
VOICES_DIR = BASE / "voices"


def _find_runtime() -> Path | None:
    for p in ENGINE_DIR.glob("rvc*/**/runtime/python.exe"):
        return p
    for p in ENGINE_DIR.glob("**/runtime/python.exe"):
        return p
    return None


def list_voices() -> list[str]:
    if not VOICES_DIR.exists():
        return []
    return sorted(d.name for d in VOICES_DIR.iterdir()
                  if d.is_dir() and any(d.glob("*.pth")))


class RvcVoice:
    def __init__(self, voice: str = "cortana", log=print) -> None:
        self.voice = voice
        self._log = log
        self._proc: subprocess.Popen | None = None
        self._sock: socket.socket | None = None
        self._ready = False
        self._failed = False
        self._lock = threading.Lock()
        self._buf = np.zeros(0, np.int16)       # input not yet converted
        self._ctx = np.zeros(0, np.int16)       # previous input tail (context)
        self._held = np.zeros(0, np.int16)      # last XF output samples, not yet played
        self._enabled_cache = (0.0, False)

    # ── lifecycle ───────────────────────────────────────────────────────────
    def _enabled(self) -> bool:
        t, v = self._enabled_cache
        if time.monotonic() - t < 2.0:
            return v
        try:
            from memory.config_manager import get_rvc_enabled, get_rvc_voice
            v = get_rvc_enabled()
            self.voice = get_rvc_voice() or self.voice
        except Exception:
            v = False
        if v and not self._enabled_cache[1] and self._failed:
            # switched back on after a failure: allow a fresh attempt
            self._failed = False
            self._proc = None
        self._enabled_cache = (time.monotonic(), v)
        return v

    @property
    def active(self) -> bool:
        if not self._enabled():
            return False
        if not self._ready and not self._failed and self._proc is None:
            self.start()
        return self._ready

    def status(self) -> str:
        if self._ready:
            return "ready"
        if self._failed:
            return "failed"
        return "starting" if self._proc else "off"

    def start(self) -> None:
        if self._proc is not None:
            return
        runtime = _find_runtime()
        vdir = VOICES_DIR / self.voice
        if runtime is None:
            self._fail("motor RVC não instalado — rode instalar_voz.bat")
            return
        if not any(vdir.glob("*.pth")):
            self._fail(f"nenhum modelo .pth em voices\\{self.voice}")
            return
        rvc_dir = runtime.parent.parent
        cmd = [str(runtime), str(ENGINE_DIR / "rvc_server.py"),
               "--rvc", str(rvc_dir), "--voice", str(vdir), "--port", str(PORT)]
        flags = 0x08000000 if os.name == "nt" else 0       # CREATE_NO_WINDOW
        logf = open(ENGINE_DIR / "rvc_server.log", "w", encoding="utf-8", errors="replace")
        try:
            self._proc = subprocess.Popen(cmd, cwd=str(rvc_dir), stdout=logf,
                                          stderr=subprocess.STDOUT, creationflags=flags)
        except Exception as e:
            self._fail(f"não consegui iniciar o motor: {e}")
            return
        import atexit
        atexit.register(self.stop)
        self._log(f"SYS: Voz {self.voice}: carregando motor RVC…")
        threading.Thread(target=self._connect_loop, daemon=True).start()

    def _connect_loop(self) -> None:
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if self._proc and self._proc.poll() is not None:
                self._fail("o motor RVC fechou — veja voice_engine\\rvc_server.log")
                return
            try:
                s = socket.create_connection(("127.0.0.1", PORT), timeout=2)
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                s.sendall(struct.pack("<I", 0))
                s.settimeout(5)
                self._recv_exact(s, 4)
                s.settimeout(4.0)
                self._sock = s
                self._ready = True
                self._log(f"SYS: Voz {self.voice} ativa (RVC).")
                return
            except Exception:
                time.sleep(1.0)
        self._fail("o motor RVC demorou demais para iniciar")

    def _fail(self, why: str) -> None:
        self._failed = True
        self._ready = False
        self._log(f"SYS: Voz RVC desligada — {why}. Usando a voz normal.")

    def stop(self) -> None:
        self._ready = False
        try:
            if self._sock:
                self._sock.close()
        except Exception:
            pass
        try:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
        except Exception:
            pass
        self._proc = None

    # ── streaming ───────────────────────────────────────────────────────────
    def reset(self) -> None:
        """Drop everything buffered (user interrupted)."""
        with self._lock:
            self._buf = np.zeros(0, np.int16)
            self._ctx = np.zeros(0, np.int16)
            self._held = np.zeros(0, np.int16)

    def pending(self) -> bool:
        return self._buf.size > 0 or self._held.size > 0

    def feed(self, pcm_bytes: bytes) -> None:
        with self._lock:
            self._buf = np.concatenate([self._buf, np.frombuffer(pcm_bytes, np.int16)])

    def take(self, final: bool = False) -> bytes:
        """Convert every full block buffered (and the remainder if final).
        Returns playable bytes (possibly empty)."""
        out = []
        with self._lock:
            while self._buf.size >= BLOCK or (final and self._buf.size > 0):
                n = min(BLOCK, self._buf.size)
                block, self._buf = self._buf[:n], self._buf[n:]
                out.append(self._convert_block(block))
            if final and self._held.size:
                out.append(self._held)
                self._held = np.zeros(0, np.int16)
                self._ctx = np.zeros(0, np.int16)
        return b"".join(o.tobytes() for o in out)

    def _convert_block(self, block: np.ndarray) -> np.ndarray:
        ctx = self._ctx
        x = np.concatenate([ctx, block])
        try:
            y = self._remote(x)
        except Exception as e:
            self._fail(f"erro na conversão ({e})")
            y = x
        self._ctx = block[-CTX:]
        c = ctx.size
        held = self._held
        h = min(held.size, c)
        if h > 0:
            # crossfade the held tail with the same instant of the new output
            w = np.linspace(0.0, 1.0, h, dtype=np.float32)
            seg = y[c - h:c].astype(np.float32)
            mix = (held[-h:].astype(np.float32) * (1 - w) + seg * w).astype(np.int16)
            head = mix
        else:
            head = held
        body = y[c:]
        if body.size > XF:
            emit, self._held = body[:-XF], body[-XF:]
        else:
            emit, self._held = body[:0], body
        return np.concatenate([head, emit]).astype(np.int16)

    def _remote(self, x: np.ndarray) -> np.ndarray:
        if not self._ready or self._sock is None:
            return x
        data = x.astype(np.int16).tobytes()
        self._sock.sendall(struct.pack("<I", len(data)) + data)
        (m,) = struct.unpack("<I", self._recv_exact(self._sock, 4))
        y = np.frombuffer(self._recv_exact(self._sock, m), np.int16)
        if y.size != x.size:
            y = np.interp(np.linspace(0, y.size - 1, x.size),
                          np.arange(y.size), y).astype(np.int16)
        return y

    @staticmethod
    def _recv_exact(s: socket.socket, n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            part = s.recv(n - len(buf))
            if not part:
                raise ConnectionError("closed")
            buf.extend(part)
        return bytes(buf)
