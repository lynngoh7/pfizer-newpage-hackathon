from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import db, extractions, permissions
from app.config import Settings
from app.main import create_app

TOKEN = "t" * 48


@pytest.fixture
def indexed_note(tmp_path):
    db.clear()
    permissions.allowed_folders.clear()
    notes = tmp_path / "notes"
    notes.mkdir()
    note = notes / "2026-09-22 decision.md"
    text = "# Decision\nWe chose Acme.\n\n## Actions\n- [ ] Send the update\n"
    note.write_text(text)
    permissions.allowed_folders.add(notes.resolve())
    chunk = SimpleNamespace(filePath=str(note), start=0, end=4, text=text)
    chunk_id = db.add_file(str(note), [chunk])[0]
    yield note, chunk_id
    db.clear()
    permissions.allowed_folders.clear()


def test_read_chunks_returns_text_and_source_metadata(indexed_note):
    note, chunk_id = indexed_note

    assert extractions.read_chunks() == [{
        "chunkID": chunk_id,
        "path": str(note.resolve()),
        "date": "2026-09-22",
        "start": 0,
        "end": 4,
        "text": "# Decision\nWe chose Acme.\n\n## Actions\n- [ ] Send the update\n",
    }]


def test_read_chunk_omits_unknown_or_changed_passages(indexed_note):
    note, chunk_id = indexed_note

    assert extractions.read_chunk(-1) is None
    note.write_text("# Decision\nWe chose another vendor.\n")
    assert extractions.read_chunk(chunk_id) is None
    assert extractions.read_chunks() == []


def test_todos_parses_markdown_checkboxes_with_source_metadata(monkeypatch):
    monkeypatch.setattr(extractions, "read_chunks", lambda: [{
        "chunkID": 12,
        "path": "/notes/todo.md",
        "date": "2026-11-12",
        "start": 4,
        "end": 10,
        "text": (
            "# Actions\n"
            "- [ ] Draft the update\n"
            "* [x] Send the old version\n"
            "2. [X] Confirm the date\n"
            "+ [ ]   \n"
            "```md\n"
            "- [ ] Example, not a real task\n"
            "```\n"
        ),
    }])

    assert extractions.todos() == {"todos": [
        {
            "task": "Draft the update",
            "completed": False,
            "chunkID": 12,
            "path": "/notes/todo.md",
            "date": "2026-11-12",
            "start": 4,
            "end": 10,
        },
        {
            "task": "Send the old version",
            "completed": True,
            "chunkID": 12,
            "path": "/notes/todo.md",
            "date": "2026-11-12",
            "start": 4,
            "end": 10,
        },
        {
            "task": "Confirm the date",
            "completed": True,
            "chunkID": 12,
            "path": "/notes/todo.md",
            "date": "2026-11-12",
            "start": 4,
            "end": 10,
        },
    ]}


def test_todos_api_route_returns_extracted_items(indexed_note):
    note, chunk_id = indexed_note
    response = TestClient(create_app(Settings(port=0, session_token=TOKEN))).get(
        "/api/todos",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    assert response.status_code == 200
    assert response.json() == {"todos": [{
        "task": "Send the update",
        "completed": False,
        "chunkID": chunk_id,
        "path": str(note.resolve()),
        "date": "2026-09-22",
        "start": 0,
        "end": 4,
    }]}


def test_adding_folder_triggers_reindex(indexed_note, monkeypatch):
    note, _ = indexed_note
    reindexed = []
    monkeypatch.setattr("app.api.search_mod.reindex", lambda: reindexed.append(True))
    response = TestClient(create_app(Settings(port=0, session_token=TOKEN))).post(
        "/api/folders",
        json={"path": str(note.parent)},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    assert response.status_code == 200
    assert reindexed == [True]
