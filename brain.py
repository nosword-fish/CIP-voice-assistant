"""
The "brain" -- sends conversation to Gemini, which automatically calls
tools from tools.py when needed (Google's SDK handles the call loop).
"""
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from tools import (
    get_system_stats,
    list_processes,
    open_app,
    list_directory,
    get_network_connections,
    check_security_status,
    get_network_report,
    audit_processes,
)

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Using the "latest" alias so Google auto-updates this as models change,
# instead of a fixed name that can get deprecated (like gemini-2.5-flash did).
MODEL = "gemini-flash-lite-latest"

SYSTEM_PROMPT = """You are a personal AI assistant running on the user's own computer,
similar in spirit to Jarvis from Iron Man. You are helpful, concise, and speak
naturally since your replies will be read aloud via text-to-speech -- avoid long
lists, markdown, or anything that doesn't sound good spoken out loud. Keep replies
short unless the user asks for detail. You have tools to check system stats, list
processes, open certain apps, check network connections, check firewall/antivirus
status, get a flagged network report (unusual outbound connections), and audit
running processes for high CPU or unfamiliar processes. Use them when relevant."""

_chat = None


def get_chat():
    global _chat
    if _chat is None:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[
                get_system_stats,
                list_processes,
                open_app,
                list_directory,
                get_network_connections,
                check_security_status,
                get_network_report,
                audit_processes,
            ],
        )
        _chat = client.chats.create(model=MODEL, config=config)
    return _chat


def ask(user_text: str) -> str:
    """
    Sends user_text to Gemini. The SDK automatically calls any tools
    Gemini decides it needs, then returns the final text response.
    Conversation history is kept internally by the chat session.
    """
    chat = get_chat()
    response = chat.send_message(user_text)
    return (response.text or "").strip()
