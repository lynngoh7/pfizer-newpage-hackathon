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
| `chunkID` | Index ID of the passage (qa.py cites it; `/api/search` includes it) |
| `date` | Note date, ISO: from the file name, else modified time |
| `flag` | `"superseded"`, `"newer"`, `"conflict"`, or `null` |

Keep it lean: sources are top-k only (5 at most), snippets are 300 characters at most, and nothing else goes in.

# Decision extraction response

`GET /api/decisions` returns explicit decision sections and `DECISION:` labels
from currently indexed notes. Each entry preserves the original wording and
includes its source passage metadata; the text is re-read from the original
file and is not stored separately.

```json
{
  "decisions": [
    {
      "text": "We are going with Corvid Analytics.",
      "chunkID": 12,
      "path": "/Users/me/Notes/vendor-decision.md",
      "date": "2026-09-22",
      "start": 10,
      "end": 14
    }
  ]
}
```

# Upcoming dates response

`GET /api/upcoming` returns every line in the indexed notes that names a date,
oldest first. Weekdays and dates without a year are read against the note's
own date. Ticked to-dos, headings and the note's own date are left out. Rebuilt
per request; nothing is stored. Home filters it to the next 14 days plus open
to-dos (`todo: true`) whose date has passed.

```json
{
  "items": [
    {
      "when": "2026-11-24",
      "text": "- [ ] tell pilot customers new beta date (24 Nov)",
      "todo": true,
      "chunkID": 7,
      "path": "/Users/me/Notes/todo.md",
      "noteDate": "2026-11-12"
    }
  ]
}
```

# Hooks `db.py` must register

Without these, "remove folder" and "Forget everything" leave chunks in memory.

```python
permissions.on_revoke("index", drop_chunks_under)  # fn(path: Path) -> int: drop chunks at or under path, return count
session.on_forget("index", drop_everything)        # fn() -> int: empty the index, return count
```
