"""
Local wake-word detection — "Atena".

Uses Vosk (offline speech recognition) with a tiny Portuguese model and a
restricted grammar, so it only ever tries to recognise a handful of phrases.
Light on the CPU, fully offline, audio never leaves the machine.

Same public API as before (is_installed / is_ready / install_and_download /
WakeWordDetector), so main.py and the UI did not need to change.

Setup (one click on the WAKE WORD button in CONTROLS):
  * pip install vosk
  * downloads vosk-model-small-pt-0.3 (~31 MB) into config/
"""
from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import zipfile
from pathlib import Path
from typing import Callable

WAKE_PHRASE = "Atena"
SAMPLE_RATE = 16000
DEFAULT_THRESHOLD = 0.5            # kept for API compatibility
MIN_CONF = 0.85                    # how sure Vosk must be that it heard "Atena"

MODEL_NAME = "vosk-model-small-pt-0.3"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"

# Words that count as the wake word. "antena"/"atenas" are acoustic neighbours
# that are certainly in the model's vocabulary, in case "atena" itself is not.
_TRIGGERS = ("atena", "atenas", "antena", "a tena")
_GRAMMAR = ["oi atena", "atena", "ei atena", "olá atena",
            "oi atenas", "atenas", "oi antena", "antena", "[unk]"]


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


MODEL_DIR = _base_dir() / "config" / MODEL_NAME


def is_installed() -> bool:
    try:
        import importlib.util
        return importlib.util.find_spec("vosk") is not None
    except Exception:
        return False


def _model_present() -> bool:
    # Newer Vosk models keep files in am/; older ones (like small-pt-0.3)
    # have final.mdl directly in the model folder.
    return ((MODEL_DIR / "am" / "final.mdl").is_file()
            or (MODEL_DIR / "final.mdl").is_file())


def is_ready() -> bool:
    return is_installed() and _model_present()


def install_and_download(logger: Callable[[str], None] = print,
                         notify: Callable[[str], None] | None = None) -> tuple[bool, str]:
    _tell = notify or (lambda _msg: None)
    try:
        if not is_installed():
            logger("Wake word: instalando vosk (uma vez)…")
            _tell("Wake word: instalando vosk (uma vez)…")
            r = subprocess.run([sys.executable, "-m", "pip", "install", "vosk"],
                               capture_output=True, text=True)
            if r.returncode != 0:
                tail = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or [""]
                return False, f"pip install falhou: {tail[0][:160]}"
        if not _model_present():
            logger("Wake word: baixando modelo de voz em português (~31 MB)…")
            _tell("Wake word: baixando modelo de voz em português (~31 MB)…")
            import urllib.request
            MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
            zpath = MODEL_DIR.parent / f"{MODEL_NAME}.zip"
            urllib.request.urlretrieve(MODEL_URL, zpath)
            with zipfile.ZipFile(zpath) as z:
                z.extractall(MODEL_DIR.parent)
            try:
                zpath.unlink()
            except Exception:
                pass
        if not is_ready():
            return False, "instalado, mas o modelo não foi encontrado."
        logger("Wake word: pronto.")
        return True, f"Palavra de ativação pronta — diga '{WAKE_PHRASE}'."
    except Exception as e:
        return False, f"erro na instalação: {e}"


class WakeWordDetector:
    def __init__(self, on_detect: Callable[[], None],
                 threshold: float = DEFAULT_THRESHOLD,
                 logger: Callable[[str], None] = print,
                 notify: Callable[[str], None] | None = None):
        self._on_detect = on_detect
        self._logger = logger
        self._notify = notify or (lambda _msg: None)
        self._queue: queue.Queue = queue.Queue(maxsize=100)
        self._thread: threading.Thread | None = None
        self._running = False
        self._rec = None
        self._ready = False

    def start(self) -> bool:
        if self._running:
            return True
        try:
            from vosk import Model, KaldiRecognizer, SetLogLevel
            SetLogLevel(-1)
            model = Model(str(MODEL_DIR))
            self._rec = KaldiRecognizer(model, SAMPLE_RATE, json.dumps(_GRAMMAR, ensure_ascii=False))
            self._rec.SetWords(True)
        except Exception as e:
            self._logger(f"Wake word: não consegui carregar o modelo — {e}")
            self._notify("Palavra de ativação indisponível — use o botão WAKE NOW.")
            self._rec = None
            return False
        self._running = True
        self._ready = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="WakeWordThread")
        self._thread.start()
        self._logger(f"Wake word: ouvindo '{WAKE_PHRASE}'.")
        return True

    def stop(self) -> None:
        self._running = False
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass
        self._rec = None
        self._ready = False

    @property
    def ready(self) -> bool:
        return self._ready

    def feed(self, frame_int16) -> None:
        if not self._running:
            return
        try:
            data = (frame_int16[:, 0].copy() if getattr(frame_int16, "ndim", 1) > 1
                    else frame_int16.copy())
            self._queue.put_nowait(data)
        except queue.Full:
            pass
        except Exception:
            pass

    @staticmethod
    def _hit(text: str) -> bool:
        t = (text or "").lower()
        return any(w in t for w in _TRIGGERS)

    def _loop(self) -> None:
        import numpy as np
        while self._running:
            try:
                frame = self._queue.get()
                if frame is None or not self._running:
                    break
                pcm = np.asarray(frame, dtype=np.int16).tobytes()
                # Only FINAL results count, and only when the recogniser is really
                # sure the name was said near the start. With a tiny grammar Kaldi
                # forces every sentence onto its closest phrase, so partials (and
                # low-confidence finals) fire on almost anything you say.
                if not self._rec.AcceptWaveform(pcm):
                    continue
                res = json.loads(self._rec.Result())
                words = [w for w in res.get("result", []) if w.get("word") != "[unk]"]
                hit = any(w.get("word", "") in ("atena", "atenas", "antena")
                          and float(w.get("conf", 0)) >= MIN_CONF
                          for w in words[:2])
                if hit:
                    self._rec.Reset()
                    self._drain()
                    try:
                        self._on_detect()
                    except Exception as e:
                        self._logger(f"Wake word: on_detect error — {e}")
            except Exception as e:
                self._logger(f"Wake word: inference error — {e}")

    def _drain(self) -> None:
        try:
            while True:
                self._queue.get_nowait()
        except Exception:
            pass
