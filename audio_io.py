"""
Handles microphone recording while a hotkey is held down.
"""
import numpy as np
import sounddevice as sd
import keyboard
import time

SAMPLE_RATE = 16000  # Whisper wants 16kHz
CHANNELS = 1
HOTKEY = "f9"  # change this if you want a different push-to-talk key


def record_while_held(hotkey: str = HOTKEY) -> np.ndarray:
    """
    Waits for the hotkey to be pressed, records audio while it's held,
    stops when released. Returns a float32 numpy array of samples.
    """
    print(f"\n[Hold {hotkey.upper()} to talk]")
    keyboard.wait(hotkey)  # blocks until pressed

    print("[Recording...]")
    frames = []

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        callback=callback,
    )

    with stream:
        while keyboard.is_pressed(hotkey):
            time.sleep(0.01)

    print("[Recording stopped]")

    if not frames:
        return np.array([], dtype=np.float32)

    audio = np.concatenate(frames, axis=0).flatten()
    return audio
