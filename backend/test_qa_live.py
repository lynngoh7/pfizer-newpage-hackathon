
"""Test question answering using the real local Ollama model."""

from unittest.mock import patch

from app import models
from app.qa import ask_question


# Simulated manager notes.
# Eventually these will come from Eoin's search system.
notes = {
    "meeting_001": (
        "During Monday's planning meeting, Sarah agreed "
        "to send the revised budget to Finance by Friday."
    ),
    "meeting_002": (
        "James will prepare the quarterly sales report "
        "for the leadership meeting next week."
    ),
}


# Ask a question that can be answered using meeting_001.
#question = "Who is responsible for sending the revised budget?"
question = "When is James going on holiday?"

# This calls the real Ollama API, not a mocked response.
#result = ask_question(question, notes)

# Temporarily select Qwen3 for this test only.
# The actual Ollama inference still runs normally.
with patch.object(
    models,
    "answer_model",
    return_value="qwen3:4b-instruct",
):
    result = ask_question(question, notes)

# Check whether at least one claim has a verified citation.
print("Supported:", result.supported)

# If no citations are accepted, this contains the fallback message.
print("Message:", result.message)


# Display each accepted claim and its supporting evidence.
for claim in result.claims:
    print("\nClaim:", claim.text)

    for citation in claim.citations:
        print("Source:", citation.chunk_id)
        print("Quote:", citation.quote)
        print("Start:", citation.start)
        print("End:", citation.end)


# Display any citations rejected by the validator.
print("\nRejected citations:", result.rejected)
