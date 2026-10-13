import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from datetime import datetime
from app.services.eligibility import check_eligibility, check_registration_open, parse_majors

S = {"major": "Data Analytics", "cgpa": 3.4, "graduation_year": 2027}

def test_open_event_accepts_anyone():
    assert check_eligibility({}, S) == (True, [])
    assert check_eligibility({}, {}) == (True, [])

def test_major_case_insensitive_and_trimmed():
    ev = {"eligible_majors": "computer science, data analytics "}
    assert check_eligibility(ev, S)[0] is True
    assert check_eligibility(ev, {"major": "Biology"})[0] is False
    assert check_eligibility(ev, {})[0] is False

def test_cgpa_boundary_and_missing():
    assert check_eligibility({"min_cgpa": 3.4}, S)[0] is True
    assert check_eligibility({"min_cgpa": 3.41}, S)[0] is False
    assert check_eligibility({"min_cgpa": 3.0}, {"major": "x"})[0] is False

def test_grad_year_window_inclusive():
    assert check_eligibility({"min_grad_year": 2027, "max_grad_year": 2027}, S)[0] is True
    ok, why = check_eligibility({"min_grad_year": 2028}, S)
    assert not ok and "2028 or later" in why[0]
    assert check_eligibility({"max_grad_year": 2026}, S)[0] is False

def test_all_reasons_reported():
    ok, why = check_eligibility({"eligible_majors": "Law", "min_cgpa": 3.9}, S)
    assert not ok and len(why) == 2

def test_registration_open():
    now = datetime(2026, 10, 12)
    assert check_registration_open({"event_date": "2026-10-20T10:00:00", "capacity": 2}, 1, now) == (True, None)
    assert check_registration_open({"event_date": "2026-10-20T10:00:00", "capacity": 2}, 2, now)[0] is False
    assert check_registration_open({"event_date": "2026-10-01T10:00:00"}, 0, now)[0] is False
    assert check_registration_open({"event_date": datetime(2026, 11, 1)}, 99, now)[0] is True

def test_parse_majors():
    assert parse_majors(None) == [] and parse_majors(" A,, b ") == ["a", "b"]

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("ok", n)
