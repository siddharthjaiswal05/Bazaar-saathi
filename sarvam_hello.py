#!/usr/bin/env python3
"""Make one chat completion call to Sarvam AI and print the reply.

    ~/.venvs/sarvam-build/bin/python sarvam_hello.py

Reads SARVAM_API_KEY from the environment or .env.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sarvamai import SarvamAI

ROOT = Path(__file__).resolve().parent


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


def main() -> int:
    _load_dotenv()
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        print("SARVAM_API_KEY is not set. Put it in .env.", file=sys.stderr)
        return 1

    client = SarvamAI(api_subscription_key=api_key)
    response = client.chat.completions(
        model="sarvam-105b-conversations",
        messages=[{"role": "user", "content": "Say hello in Hindi and English."}],
    )
    print(response.choices[0].message.content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
