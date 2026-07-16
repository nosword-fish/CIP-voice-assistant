"""
Main loop: hold F9 to talk, release to send, get spoken response back.

Press Ctrl+C to quit.
"""
from audio_io import record_while_held, HOTKEY, SAMPLE_RATE
from stt import transcribe
from brain import ask
from tts import speak


def main():
    print("=" * 50)
    print(" Personal Assistant -- Phase 1")
    print(f" Hold {HOTKEY.upper()} to talk. Ctrl+C to quit.")
    print("=" * 50)

    # Warm up models once at startup so first interaction isn't slow
    from stt import get_model
    get_model()

    while True:
        try:
            audio = record_while_held()
            if audio.size == 0:
                continue

            print("[Transcribing...]")
            text = transcribe(audio, SAMPLE_RATE)
            if not text:
                print("[Didn't catch that, try again]")
                continue

            print(f"You: {text}")

            reply = ask(text)
            print(f"Assistant: {reply}")

            speak(reply)

        except KeyboardInterrupt:
            print("\n[Shutting down]")
            break


if __name__ == "__main__":
    main()
