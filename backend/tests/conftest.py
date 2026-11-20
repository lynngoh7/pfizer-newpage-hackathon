"""Shared test setup: keep prefs.json in a temp folder, never the real app data."""
import pytest


@pytest.fixture(autouse=True)
def prefs_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTES_PREFS_DIR", str(tmp_path / "prefs"))
