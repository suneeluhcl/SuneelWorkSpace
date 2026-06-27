#!/usr/bin/env python3
"""Local token auth for the Agent API Gateway."""
import os
import secrets
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', Path.home() / 'SuneelWorkSpace'))
TOKEN_FILE = WORKSPACE / 'nervous/gateway/.token'


def get_or_create_token() -> str:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    token = secrets.token_urlsafe(32)
    TOKEN_FILE.write_text(token)
    TOKEN_FILE.chmod(0o600)
    return token


def verify_token(provided: str) -> bool:
    expected = get_or_create_token()
    return secrets.compare_digest(provided, expected)


if __name__ == '__main__':
    print(get_or_create_token())
