
"""Tests for the question-answering API endpoint."""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import api
from app.citations import Citation, Claim, check_answer


def test_ask_connects_search_and_qa():
    """Verify that the API passes retrieved notes to the AI correctly."""

    # Simulate the results returned by Eoin's search module.
    # Each source contains a chunk ID, file metadata and note text.
    fake_search_result = {
        "status": "ok",
        "answer": None,
        "sources": [
            {
                "chunkID": 1,
                "path": "meeting.txt",
                "date": None,
                "where": "lines 1–2",
                "snippet": (
                    "Sarah agreed to send the revised "
                    "budget to Finance by Friday."
                ),
                "flag": None,
            }
        ],
    }

    # Convert the sample source into the format expected by qa.py:
    # a dictionary mapping chunk IDs (strings) to their text.
    chunks = {
        "1": fake_search_result["sources"][0]["snippet"]
    }

    # Construct an AI answer containing a real citation.
    # check_answer() validates the quotation against the source text.
    fake_answer = check_answer(
        [
            Claim(
                text="Sarah is responsible for the budget.",
                citations=[
                    Citation(
                        chunk_id="1",
                        quote=chunks["1"],
                    )
                ],
            )
        ],
        chunks,
    )

    # Replace the actual search and AI functions with fake responses.
    # This lets us test the endpoint without running Ollama or reading files.
    with (
        patch.object(
            api.search_mod,
            "search",
            return_value=fake_search_result,
        ),
        patch.object(
            api.qa,
            "ask_question",
            return_value=fake_answer,
        ) as mock_qa,
    ):

        # Create a small FastAPI app containing the existing API router.
        # We test the endpoint without starting the real backend server.
        app = FastAPI()
        app.include_router(api.router)

        client = TestClient(app)

        # Simulate the frontend sending a question to /api/ask.
        response = client.post(
            "/api/ask",
            json={
                "question": "Who owns the budget task?"
            },
        )

    # Check that the endpoint successfully processed the request.
    assert response.status_code == 200

    # Convert the JSON response into a Python dictionary.
    data = response.json()

    # The response should indicate that supporting evidence exists.
    assert data["supported"] is True
    assert data["status"] == "ok"

    # The response should contain the correct generated claim.
    assert data["claims"][0]["text"] == (
        "Sarah is responsible for the budget."
    )

    # Verify that the correct source card is returned.
    assert len(data["sources"]) == 1
    assert data["sources"][0]["chunkID"] == 1

    # Verify that the citation references the correct source.
    assert data["claims"][0]["citations"][0]["chunk_id"] == 1

    # Finally, verify that the endpoint supplied the correct
    # question and retrieved note excerpts to qa.ask_question().
    mock_qa.assert_called_once_with(
        "Who owns the budget task?",
        chunks,
    )
