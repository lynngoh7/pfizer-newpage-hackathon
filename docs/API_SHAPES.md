# Search response

`GET /api/search?q=` returns keyword or meaning-based results. `answer` is
always `null`; questions use `POST /api/ask` instead.

```json
{
  "status": "ok",
  "answer": null,
  "sources": [
    {
      "chunkID": 12,
      "path": "/Users/me/Notes/team-sync.md",
      "date": "2026-09-03",
      "where": "lines 10–14",
      "snippet": "Agreed: cut Q3 budget by 10%.",
      "flag": null
    }
  ]
}
```

`status` is `"ok"` or `"no_support"`. Source metadata includes the index
`chunkID`, full path, ISO date, page/heading location, short snippet, and an
optional decision flag. Snippets are re-read from the file and never stored.

## Question answer response

`POST /api/ask` accepts only a question. It returns claims that have passed
backend citation verification and only the corresponding source cards. The UI
maps each citation's `chunk_id` to its source card and renders a navigable
number. If a verified quote extends beyond a source card's short preview, the
UI displays the exact quote as evidence; the backend does not trust or accept
client-supplied note text.

```json
{
  "status": "ok",
  "supported": true,
  "answer": "Sarah will send the revised budget to Finance by Friday.",
  "message": null,
  "claims": [
    {
      "text": "Sarah will send the revised budget to Finance by Friday.",
      "citations": [
        {
          "chunk_id": 12,
          "quote": "Sarah agreed to send the revised budget to Finance by Friday.",
          "start": 42,
          "end": 104
        }
      ]
    }
  ],
  "sources": [
    {
      "chunkID": 12,
      "path": "/Users/me/Notes/team-sync.md",
      "date": "2026-09-03",
      "where": "lines 10–14",
      "snippet": "Sarah agreed to send the revised budget to Finance by Friday.",
      "flag": null
    }
  ]
}
```

With no verified evidence, `status` is `"no_support"`, `supported` is `false`,
`answer` is `null`, `message` is `"No supporting notes found."`, and both
`claims` and `sources` are empty.

Keep it lean: search sources are top-k only (5 at most), snippets are 300 characters at most, and nothing else goes in.

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
