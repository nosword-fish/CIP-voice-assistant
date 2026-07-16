"""
Text-to-speech using the standalone Piper executable (local, CPU-only,
no GPU needed). Calls piper.exe as a subprocess, writing to a temp file
instead of piping through stdout -- on Windows, piping raw binary audio
through stdout can get corrupted (newline translation), which sounds
like static/noise. Writing to a real file avoids that entirely.
"""
import subprocess
import wave
import sounddevice as sd
import numpy as np
import os
import tempfile

PIPER_EXE = os.path.join("piper", "piper.exe")
VOICE_MODEL_PATH = os.path.join("voices", "en_US-lessac-medium.onnx")


def speak(text: str) -> None:
    if not text.strip():
        return

    if not os.path.exists(PIPER_EXE):
        print(f"[TTS error: {PIPER_EXE} not found -- did you extract Piper into the project folder?]")
        return
    if not os.path.exists(VOICE_MODEL_PATH):
        print(f"[TTS error: {VOICE_MODEL_PATH} not found -- did you download the voice files?]")
        return

    # Write to a real temp file instead of stdout to avoid Windows pipe corruption
    tmp_path = os.path.join(tempfile.gettempdir(), "assistant_tts_output.wav")

    result = subprocess.run(
        [PIPER_EXE, "--model", VOICE_MODEL_PATH, "--output_file", tmp_path],
        input=text.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        print(f"[TTS error: {result.stderr.decode(errors='ignore')}]")
        return

    if not os.path.exists(tmp_path):
        print("[TTS error: piper did not produce an output file]")
        return

    with wave.open(tmp_path, "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        n_frames = wav_file.getnframes()
        audio_bytes = wav_file.readframes(n_frames)
        audio = np.frombuffer(audio_bytes, dtype=np.int16)

    sd.play(audio, samplerate=sample_rate)
    sd.wait()
