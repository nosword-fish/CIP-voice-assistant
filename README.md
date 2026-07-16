# CIP — Personal Voice Assistant with Security Tooling

A local, voice-activated AI assistant inspired by Jarvis (Iron Man), built to
learn how voice pipelines, LLM tool-calling, and sandboxed system access fit
together — with a focus on doing it *securely*, not just making it work.

Hold a hotkey, ask a question or give a command, get a spoken answer back.
The assistant can check your system's security posture (firewall, Defender,
network connections, running processes) — all voice-triggered, all read-only,
all through an explicit function allowlist.

## Demo

> _Add a 20-30 second GIF or short video here showing: hold F9 → ask "is my
> firewall on, give me a network report, and audit my processes" → spoken
> response. This is the single most persuasive thing in this README — a
> recruiter or hiring manager can see it work in 15 seconds without installing
> anything._

## Why this project exists

Most "AI assistant" tutorials give the model a `run_shell_command` tool and
call it done. That's a real security problem the moment the assistant reads
anything untrusted (a webpage, a file, an email) — a hidden instruction in
that content could hijack the model into running something harmful.

This project is built the other way: the LLM only ever sees a small, explicit
set of Python functions it's allowed to call. It cannot construct or run
arbitrary commands. Every capability was added deliberately, one function at
a time.

## Architecture

```
  Mic (push-to-talk, F9)
        │
        ▼
  faster-whisper (STT)          — runs locally, CPU-only
        │
        ▼
  Google Gemini API             — reasoning + automatic tool-calling
        │
        ▼
  tools.py (allowlisted funcs)  — the ONLY thing the model can execute
        │
        ▼
  Piper TTS                     — runs locally, CPU-only
        │
        ▼
  Speaker output
```

No GPU required — the reasoning happens via API call, so the whole pipeline
runs comfortably on integrated graphics and 8-16GB RAM.

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Speech-to-text | faster-whisper (`tiny.en`) | Fast, accurate enough, runs on CPU |
| Reasoning / tool-calling | Google Gemini API (`gemini-flash-lite-latest`) | Free tier, no local GPU needed, native function-calling |
| Text-to-speech | Piper (standalone binary) | Natural voices, CPU-only, no cloud dependency for output |
| Hotkey / audio capture | `keyboard`, `sounddevice` | Push-to-talk instead of always-listening |
| System tools | `psutil`, PowerShell (fixed commands only) | Sandboxed system + security introspection |

## Security-focused tools (the interesting part)

All of these are voice-triggered and read-only — nothing here can modify
system state:

- **`check_security_status()`** — firewall (per network profile) and Windows
  Defender status, via two *fixed* PowerShell commands. The model can invoke
  this function; it cannot alter what command runs.
- **`get_network_report()`** — active connections, with a simple heuristic
  flagging outbound traffic to public IPs on uncommon ports.
- **`audit_processes()`** — top processes by CPU, flagged if usage is high or
  the process name isn't in a known-common allowlist.
- **`get_system_stats()` / `list_processes()` / `get_network_connections()`**
  — baseline system introspection.
- **`open_app()` / `list_directory()`** — both restricted to explicit
  allowlists (approved apps only; Desktop/Documents only).

## Setup

```bash
# 1. Create a virtual environment (Python 3.12 recommended)
py -3.12 -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Get a free Gemini API key: https://aistudio.google.com/apikey
copy .env.example .env
# paste your key into .env

# 4. Download Piper (standalone binary) and a voice model — see below

# 5. Run it
python main.py
```

**Piper setup:** download the Windows build from the Piper releases page on
GitHub, extract it into a `piper/` folder in this project, and download a
voice (e.g. `en_US-lessac-medium`) from the Piper voices repo on Hugging Face
into a `voices/` folder.

## Usage

Hold **F9**, speak, release. Try:

- *"How much RAM am I using?"*
- *"Is my firewall on?"*
- *"Give me a network security report."*
- *"Audit my running processes."*
- *"Open the calculator."*

## What I'd build next

- SQLite-backed memory so it remembers context across sessions
- Wake-word activation instead of push-to-talk
- Basic port-scan tooling (safely wrapped, local-network only)
- Log file summarization for quick triage

## Project structure

```
main.py         — orchestration loop (record → transcribe → think → speak)
audio_io.py     — push-to-talk mic capture
stt.py          — faster-whisper wrapper
brain.py        — Gemini API + tool-calling config
tools.py        — every function the assistant is allowed to call
tts.py          — Piper subprocess wrapper
requirements.txt
.env.example
```

---

Built as a hands-on learning project while studying for CompTIA Security+
and AWS Cloud Essentials.
