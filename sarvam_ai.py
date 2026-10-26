"""Thin wrappers over the Sarvam AI APIs used by Bazaar Saathi.

  Saaras v3      speech-to-text, also detects the spoken language
  Sarvam-105B    chat, tool calling and explanations
  Bulbul v3      text-to-speech
  Sarvam-Translate  lesson translation
  Document AI    reading screenshots (WhatsApp tips, broker holdings)
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path

from sarvamai import SarvamAI

ROOT = Path(__file__).resolve().parent
CHAT_MODEL = "sarvam-105b-conversations"
TTS_CHUNK = 1500  # Bulbul allows 2500 characters per request; stay well under
TRANSLATE_CHUNK = 1800  # Sarvam-Translate allows 2000

LANGUAGES = {
    "en-IN": "English", "hi-IN": "हिन्दी (Hindi)", "ta-IN": "தமிழ் (Tamil)",
    "te-IN": "తెలుగు (Telugu)", "bn-IN": "বাংলা (Bengali)", "mr-IN": "मराठी (Marathi)",
    "gu-IN": "ગુજરાતી (Gujarati)", "kn-IN": "ಕನ್ನಡ (Kannada)", "ml-IN": "മലയാളം (Malayalam)",
    "pa-IN": "ਪੰਜਾਬੀ (Punjabi)", "od-IN": "ଓଡ଼ିଆ (Odia)",
}
LANGUAGE_NAMES = {code: label.split(" (")[-1].rstrip(")") for code, label in LANGUAGES.items()}


def _load_dotenv() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def make_client() -> SarvamAI:
    _load_dotenv()
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        raise RuntimeError("SARVAM_API_KEY is not set. Put it in .env (or Streamlit secrets).")
    return SarvamAI(api_subscription_key=api_key)


# --- chat ------------------------------------------------------------------

def chat(client: SarvamAI, messages: list[dict], **kwargs):
    """One chat completion; returns the message object."""
    response = client.chat.completions(model=CHAT_MODEL, messages=messages, **kwargs)
    return response.choices[0].message


def chat_text(client: SarvamAI, system: str, user: str) -> str:
    message = chat(client, [{"role": "system", "content": system}, {"role": "user", "content": user}])
    return (message.content or "").strip()


def chat_json(client: SarvamAI, system: str, user: str) -> dict:
    """Ask for a JSON object and parse it, tolerating a ```json fence around it."""
    message = chat(client, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                   response_format={"type": "json_object"})
    text = (message.content or "").strip()
    match = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(match.group(0) if match else text)
    except json.JSONDecodeError:
        return {}


# --- speech ----------------------------------------------------------------

def transcribe(client: SarvamAI, audio: bytes, filename: str = "question.wav") -> tuple[str, str]:
    """Return (transcript, language_code) for recorded speech."""
    result = client.speech_to_text.transcribe(
        file=(filename, audio), model="saaras:v3", mode="transcribe", language_code="unknown")
    return result.transcript, result.language_code or "en-IN"


def detect_language(client: SarvamAI, text: str) -> str:
    code = client.text.identify_language(input=text[:1000]).language_code
    return code if code in LANGUAGES else "en-IN"


def _speakable(text: str) -> str:
    """Strip markdown and emoji so the voice doesn't read out symbols."""
    text = re.sub(r"[*_#`>|]+", " ", text)
    text = re.sub(r"[\U0001F000-\U0001FAFF☀-➿️]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _chunks(text: str, size: int) -> list[str]:
    """Split on sentence ends so each piece is under `size` characters."""
    pieces, current = [], ""
    for sentence in re.split(r"(?<=[.!?।])\s+", text):
        if current and len(current) + len(sentence) + 1 > size:
            pieces.append(current)
            current = ""
        current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return [p[:size] for p in pieces]


def speak(client: SarvamAI, text: str, language_code: str, speaker: str = "shubh") -> bytes | None:
    """MP3 audio of `text` in the given language. MP3 frames concatenate cleanly."""
    text = _speakable(text)
    if language_code not in LANGUAGES or not text:
        return None
    audio = b""
    for piece in _chunks(text, TTS_CHUNK):
        result = client.text_to_speech.convert(
            text=piece, language_code=language_code, model="bulbul:v3",
            speaker=speaker, output_audio_codec="mp3")
        audio += b"".join(base64.b64decode(a) for a in result.audios)
    return audio


# --- translation -----------------------------------------------------------

def translate(client: SarvamAI, text: str, target: str) -> str:
    """Translate English text, paragraph by paragraph so markdown structure survives."""
    if target == "en-IN" or not text.strip():
        return text
    out = []
    for para in text.split("\n"):
        if not para.strip():
            out.append(para)
            continue
        parts = [client.text.translate(input=p, source_language_code="en-IN",
                                       target_language_code=target, model="sarvam-translate:v1",
                                       ).translated_text
                 for p in _chunks(para, TRANSLATE_CHUNK)]
        out.append(" ".join(parts))
    return "\n".join(out)


# --- Document AI -----------------------------------------------------------

def extract_from_image(client: SarvamAI, image: bytes, filename: str, schema: dict,
                       timeout: float = 120) -> dict:
    """Run a Document AI extract job on one image and wait for the structured result."""
    job = client.doc_ai.extract(file=[(filename, image)], schema=json.dumps(schema),
                                output_format="json")
    deadline = time.time() + timeout
    status = job.status
    while status not in {"completed", "partially_completed", "failed", "rejected"}:
        if time.time() > deadline:
            raise TimeoutError("Document AI took too long to read the image.")
        time.sleep(2)
        status = client.doc_ai.get_status(job.job_id).status
    if status in {"failed", "rejected"}:
        raise RuntimeError(f"Document AI could not read the image ({status}).")
    result = client.doc_ai.get_results(job.job_id).result
    if isinstance(result, list):  # one result per file
        result = result[0] if result else {}
    return result if isinstance(result, dict) else {}
