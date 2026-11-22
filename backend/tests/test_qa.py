
"""Tests for local, source-aware question answering."""

import io
import json
from unittest.mock import patch

from app import qa
from app.citations import NO_SUPPORT


def mock_ollama_response(claims):
    """Simulate an Ollama API response without running the actual AI model."""

    # Construct a fake response using the same structure as Ollama's API.
    # The model's answer is stored as a JSON string inside "message.content".
    response = {
        "message": {
            "content": json.dumps({"claims": claims})
        }
    }

    # Convert the response into bytes, then wrap it in BytesIO.
    # BytesIO behaves like a file, allowing our code to read it
    # as though it came from an actual HTTP request.
    return io.BytesIO(json.dumps(response).encode("utf-8"))


def test_valid_evidence():
    """Verify that an answer supported by a genuine citation is accepted."""

    # Create a sample manager's note.
    # This represents a note retrieved by Eoin's search system.
    notes = {
        "meeting_001": (
            "Sarah agreed to send the revised budget "
            "to Finance by Friday."
        )
    }

    # Simulate an AI-generated answer containing a factual claim
    # and a quotation identifying where the evidence came from.
    claims = [
        {
            "text": "Sarah is responsible for the revised budget.",
            "citations": [
                {
                    "chunk_id": "meeting_001",
                    "quote": (
                        "Sarah agreed to send the revised budget "
                        "to Finance by Friday."
                    ),
                }
            ],
        }
    ]

    # Mock the model selection so the test doesn't depend on
    # which Ollama model the application currently uses.
    #
    # Mock urlopen so no HTTP request is sent to Ollama.
    # Instead, return our predefined fake response.
    with (
        patch.object(
            qa.models,
            "answer_model",
            return_value="qwen3:4b-instruct",
        ),
        patch.object(
            qa,
            "urlopen",
            return_value=mock_ollama_response(claims),
        ),
    ):
        # Ask a question using our sample notes.
        result = qa.ask_question(
            "Who is responsible for the revised budget?",
            notes,
        )

    # Verify that the answer has at least one validated claim.
    assert result.supported is True

    # Verify that exactly one claim was accepted.
    assert len(result.claims) == 1

    # Verify that the accepted citation references the correct source.
    assert result.claims[0].citations[0].chunk_id == "meeting_001"


def test_no_evidence():
    """Verify that the assistant handles questions without supporting evidence."""

    # Create a note containing information about Sarah,
    # but nothing about James or his holiday plans.
    notes = {
        "meeting_001": (
            "Sarah agreed to send the revised budget "
            "to Finance by Friday."
        )
    }

    # Simulate the AI correctly returning no claims
    # because the notes don't contain the requested information.
    with (
        patch.object(
            qa.models,
            "answer_model",
            return_value="qwen3:4b-instruct",
        ),
        patch.object(
            qa,
            "urlopen",
            return_value=mock_ollama_response([]),
        ),
    ):
        result = qa.ask_question(
            "When is James going on holiday?",
            notes,
        )

    # Verify that the response contains no supported claims.
    assert result.supported is False

    # Verify that the application returns its standard
    # no-evidence message instead of inventing an answer.
    assert result.message == NO_SUPPORT


def test_fabricated_citation():
    """Verify that quotations invented by the AI are rejected."""

    # Create a note that only mentions Sarah sending the budget.
    notes = {
        "meeting_001": (
            "Sarah agreed to send the revised budget "
            "to Finance by Friday."
        )
    }

    # Simulate an AI hallucination:
    # The model claims James approved the budget,
    # but this information doesn't exist in the original note.
    claims = [
        {
            "text": "James approved the revised budget.",
            "citations": [
                {
                    "chunk_id": "meeting_001",
                    "quote": "James approved the revised budget yesterday.",
                }
            ],
        }
    ]

    # Return the fabricated claim as if Ollama generated it.
    with (
        patch.object(
            qa.models,
            "answer_model",
            return_value="qwen3:4b-instruct",
        ),
        patch.object(
            qa,
            "urlopen",
            return_value=mock_ollama_response(claims),
        ),
    ):
        result = qa.ask_question(
            "Who approved the budget?",
            notes,
        )

    # Verify that the fabricated citation was rejected,
    # leaving the response with no supported claims.
    assert result.supported is False

    # Verify that the citation validator recorded one rejection.
    assert len(result.rejected) == 1

    # Verify that the rejection occurred because the quoted
    # text could not be found in the original source note.
    assert result.rejected[0].reason == "not_found"
