"""
RVC voice server for JARVIS.

Runs inside the RVC AMD/Intel (DirectML) runtime, NOT inside Jarvis's Python:
    <RVC>\\runtime\\python.exe rvc_server.py --rvc <RVC dir> --voice <voice dir>

Protocol (TCP, 127.0.0.1):
    request : 4-byte little-endian length N, then N bytes int16 mono PCM @ 24 kHz
    response: 4-byte length M, then M bytes int16 mono PCM @ 24 kHz (converted)
    N == 0 is a ping → response length 0.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import struct
import sys
import time
import traceback

import numpy as np

SR_IO = 24000      # what Jarvis sends and expects back
SR_RVC = 16000     # what RVC's front-end wants


def log(msg: str) -> None:
    print(f"[RVC] {msg}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rvc", required=True, help="RVC1006AMD_Intel folder")
    ap.add_argument("--voice", required=True, help="folder with .pth/.index/voice.json")
    ap.add_argument("--port", type=int, default=18888)
    args = ap.parse_args()

    rvc_dir = os.path.abspath(args.rvc)
    voice_dir = os.path.abspath(args.voice)

    cfg = {"pitch": 0, "f0_method": "rmvpe", "index_rate": 0.6,
           "protect": 0.33, "rms_mix_rate": 0.25, "filter_radius": 3}
    try:
        with open(os.path.join(voice_dir, "voice.json"), encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass

    pth = [f for f in os.listdir(voice_dir) if f.lower().endswith(".pth")]
    idx = [f for f in os.listdir(voice_dir) if f.lower().endswith(".index")]
    if not pth:
        log(f"no .pth model in {voice_dir}")
        sys.exit(2)
    model_name = pth[0]
    index_path = os.path.join(voice_dir, idx[0]) if idx else ""

    # RVC uses relative paths and reads its settings from env + argv.
    os.chdir(rvc_dir)
    sys.path.insert(0, rvc_dir)
    os.environ["weight_root"] = voice_dir
    os.environ.setdefault("index_root", os.path.join(rvc_dir, "logs"))
    os.environ.setdefault("rmvpe_root", os.path.join(rvc_dir, "assets", "rmvpe"))
    sys.argv = [sys.argv[0], "--dml", "--noautoopen"]

    from configs.config import Config
    import infer.modules.vc.modules as vcmod
    from infer.modules.vc.modules import VC

    # Feed audio straight from memory instead of a temp file + ffmpeg per chunk.
    holder = {"audio": None}
    vcmod.load_audio = lambda *_a, **_k: holder["audio"]

    try:
        from scipy.signal import resample_poly
    except Exception:
        resample_poly = None

    def to16k(x: np.ndarray) -> np.ndarray:
        if resample_poly is not None:
            return resample_poly(x, 2, 3).astype(np.float32)
        n = int(len(x) * SR_RVC / SR_IO)
        return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)

    def fit(y: np.ndarray, n: int) -> np.ndarray:
        if len(y) == n:
            return y
        return np.interp(np.linspace(0, len(y) - 1, n), np.arange(len(y)), y)

    t0 = time.time()
    config = Config()
    vc = VC(config)
    vc.get_vc(model_name, 0.33, 0.33)
    log(f"model '{model_name}' loaded in {time.time() - t0:.1f}s "
        f"(index: {os.path.basename(index_path) or 'none'}, device: {config.device})")

    def convert(pcm16: np.ndarray) -> np.ndarray:
        x = pcm16.astype(np.float32) / 32768.0
        n_in = len(x)
        pad = 0
        if n_in < int(0.35 * SR_IO):          # HuBERT dislikes tiny clips
            pad = int(0.35 * SR_IO) - n_in
            x = np.concatenate([x, np.zeros(pad, np.float32)])
        holder["audio"] = to16k(x)
        info, (sr, y) = vc.vc_single(
            0, "mem.wav", int(cfg["pitch"]), None, cfg["f0_method"],
            index_path, "", float(cfg["index_rate"]), int(cfg["filter_radius"]),
            SR_IO, float(cfg["rms_mix_rate"]), float(cfg["protect"]),
        )
        if y is None:
            raise RuntimeError(info)
        y = np.asarray(y, dtype=np.float32)
        if sr and sr != SR_IO:
            y = fit(y, int(len(y) * SR_IO / sr))
        y = fit(y, len(x))[:n_in]
        return np.clip(y, -32768, 32767).astype(np.int16)

    # warm-up so the first real reply isn't slow
    try:
        convert(np.zeros(SR_IO // 2, np.int16))
    except Exception as e:
        log(f"warm-up failed: {e}")

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", args.port))
    srv.listen(1)
    log(f"READY on port {args.port}")

    def recv_exact(c, n):
        buf = bytearray()
        while len(buf) < n:
            part = c.recv(n - len(buf))
            if not part:
                raise ConnectionError("closed")
            buf.extend(part)
        return bytes(buf)

    while True:
        conn, _ = srv.accept()
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        try:
            while True:
                (n,) = struct.unpack("<I", recv_exact(conn, 4))
                if n == 0:
                    conn.sendall(struct.pack("<I", 0))
                    continue
                pcm = np.frombuffer(recv_exact(conn, n), dtype=np.int16)
                try:
                    out = convert(pcm).tobytes()
                except Exception as e:
                    log(f"convert error: {e}")
                    traceback.print_exc()
                    out = pcm.tobytes()          # never leave Jarvis silent
                conn.sendall(struct.pack("<I", len(out)) + out)
        except Exception:
            pass
        finally:
            conn.close()


if __name__ == "__main__":
    main()
