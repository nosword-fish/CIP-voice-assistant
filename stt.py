"""
Speech-to-text using faster-whisper, running on CPU (no GPU needed).
"""
from faster_whisper import WhisperModel
import numpy as np

# "tiny.en" is fastest and fine for commands on CPU-only hardware.
# Bump to "base.en" if accuracy feels rough and you can spare ~1-2s more.
MODEL_SIZE = "tiny.en"

_model = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        print("[Loading Whisper model... this happens once]")
        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def transcribe(audio: np.ndarray, sample_rate: int = 16000) -> str:
    if audio.size == 0:
        return ""

    model = get_model()
    segments, _ = model.transcribe(audio, language="en", beam_size=1)
    text = " ".join(seg.text.strip() for seg in segments)
    return text.strip()
