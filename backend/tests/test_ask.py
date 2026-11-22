
"""Tests for the question-answering API endpoint."""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import api
from app.citations import Citation, Claim, check_answer



def test_ask_connects_search_and_qa():
    """The ask endpoint must use full passages, not truncated search previews."""

    # The search result contains only a short UI preview.
    preview = "During Monday's planning meeting, the team discussed budgets."

    # The full passage contains evidence beyond the preview.
    full_passage = (
        preview
        + " Sarah agreed to send the revised budget "
        + "to Finance by Friday."
    )

    fake_search_result = {
        "status": "ok",
        "answer": None,
        "sources": [
            {
                "chunkID": 1,
                "path": "meeting.txt",
                "date": None,
                "where": "lines 1–2",
                "snippet": preview,
                "flag": None,
            }
        ],
    }

    full_source = {
        **fake_search_result["sources"][0],
        "snippet": full_passage,
    }

    chunks = {"1": full_passage}

    # The citation is only valid against the full passage.
    quote = "Sarah agreed to send the revised budget to Finance by Friday."

    fake_answer = check_answer(
        [
            Claim(
                text="Sarah is responsible for the budget.",
                citations=[
                    Citation(
                        chunk_id="1",
                        quote=quote,
                    )
                ],
            )
        ],
        chunks,
    )

    with (
        patch.object(
            api.search_mod,
            "search",
            return_value=fake_search_result,
        ),
        patch.object(
            api.search_mod,
            "source",
            return_value=full_source,
        ) as mock_source,
        patch.object(
            api.qa,
            "ask_question",
            return_value=fake_answer,
        ) as mock_qa,
    ):
        app = FastAPI()
        app.include_router(api.router)
        client = TestClient(app)

        response = client.post(
            "/api/ask",
            json={"question": "Who owns the budget task?"},
        )

    assert response.status_code == 200

    data = response.json()

    assert data["supported"] is True
    assert data["status"] == "ok"
    assert data["claims"][0]["text"] == (
        "Sarah is responsible for the budget."
    )

    assert len(data["sources"]) == 1
    assert data["sources"][0]["chunkID"] == 1
    assert data["claims"][0]["citations"][0]["chunk_id"] == 1

    # Crucial regression checks:
    # The endpoint must request the complete authorised passage.
    mock_source.assert_called_once_with(1, full=True)

    # The AI must receive the full passage, including evidence
    # that was absent from the search preview.
    mock_qa.assert_called_once_with(
        "Who owns the budget task?",
        {"1": full_passage},
    )

