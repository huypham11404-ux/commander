import pytest
from commander.storage.session_memory import ProjectSessionMemory

def test_extended_secret_redaction():
    cases = [
        ("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "[REDACTED"),
        ("api_key = 'abcdef1234567890'", "[REDACTED_SECRET]"),
        ("API-KEY: secret_token_value_999", "[REDACTED_SECRET]"),
        ("My sk-ant-api03-abcdefghijklmnop12345678 is secret", "[REDACTED"),
        ("password: 'supersecretpassword'", "[REDACTED_SECRET]")
    ]
    for inp, expected in cases:
        sanitized = ProjectSessionMemory.sanitize_secrets(inp)
        assert expected in sanitized
        assert "abcdef1234567890" not in sanitized
        assert "supersecretpassword" not in sanitized
