from datetime import date

from app.dates import find_date

NOTE = date(2026, 11, 18)  # a Wednesday


def test_explicit_dates():
    assert find_date("Review on 24 Nov", NOTE) == date(2026, 11, 24)
    assert find_date("Launch Dec 3rd, 2027", NOTE) == date(2027, 12, 3)
    assert find_date("due 2026-12-01", NOTE) == date(2026, 12, 1)


def test_missing_year_rolls_forward():
    assert find_date("kickoff 5 Jan", NOTE) == date(2027, 1, 5)


def test_weekdays_resolve_from_note_date():
    assert find_date("send deck by Friday", NOTE) == date(2026, 11, 20)
    assert find_date("sync next Fri", NOTE) == date(2026, 11, 27)
    assert find_date("standup Wednesday", NOTE) == date(2026, 11, 25)


def test_vague_or_no_date_is_skipped():
    assert find_date("by end of month", NOTE) is None
    assert find_date("we may revisit", NOTE) is None
    assert find_date("meeting on floor 2", NOTE) is None
