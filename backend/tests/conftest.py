"""Shared test setup: keep prefs.json in a temp folder, never the real app data."""
import pytest


@pytest.fixture(autouse=True)
def prefs_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTES_PREFS_DIR", str(tmp_path / "prefs"))


@pytest.fixture(autouse=True)
def no_real_ollama(monkeypatch):
    """Forget now unloads the model; never touch a developer's running Ollama."""
    from app import group
    monkeypatch.setattr(group, "OLLAMA", "http://127.0.0.1:9")
