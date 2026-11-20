# Search / answer response

What `search.py` and `qa.py` return to the UI. Build against this shape with fake data until the real code lands.

```json
{
  "status": "ok",
  "answer": "The Q3 budget was cut by 10% [1], but a later note reverses this [2].",
  "sources": [
    {
      "path": "/Users/me/Notes/team-sync-2026-09-03.md",
      "where": "## Decisions",
      "snippet": "Agreed: cut Q3 budget by 10%.",
      "flag": "superseded"
    },
    {
      "path": "/Users/me/Notes/budget-update.docx",
      "where": "page 2",
      "snippet": "Budget cut reversed after review.",
      "flag": "newer"
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `status` | `"ok"`, or `"no_support"`: nothing backs an answer, so the UI shows "No supporting notes found." |
| `answer` | Only for questions. `null` for a keyword search. `[n]` points to `sources[n-1]` |
| `path` | Full file path. The UI gets the file name from it and uses it for the open-file button |
| `where` | Page or heading |
| `snippet` | Passage re-read from the file when the response is built. Never stored |
| `flag` | `"superseded"`, `"newer"`, `"conflict"`, or `null` |

Keep it lean: sources are top-k only (5 at most), snippets are 300 characters at most, and nothing else goes in.
