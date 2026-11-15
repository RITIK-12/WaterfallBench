"""Verifies the hello smoke task. Runs in the separate verifier container;
/app/hello.txt arrives there via the task's `artifacts` list."""

from pathlib import Path

HELLO = Path("/app/hello.txt")


def test_file_exists():
    assert HELLO.is_file(), f"{HELLO} was not created"


def test_file_contents():
    assert HELLO.read_text().strip() == "Hello, world!"
