import threading
from datetime import date

import pytest

from app.errors import BusinessError
from app.modules.m8_donation import rules, store

NOW = date(2026, 11, 20)


@pytest.fixture
def dbs(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    return store


def gap(issue, year="2025", since="2026-01-01", issn="1000-0001", title="图情学刊"):
    return {"issn": issn, "title": title, "year": year, "issue": issue, "since": since}


def libs(*specs):
    return [{"id": f"lib-{name}", "name": name, "gaps": [dict(g, status="open") for g in gaps]}
            for name, gaps in specs]


def test_expand_issues_spec():
    assert rules.expand_issues("1-3,5") == ["1", "2", "3", "5"]


def test_expand_issues_dedup_sorted():
    assert rules.expand_issues("3,1-2") == ["1", "2", "3"]


def test_expand_issues_invalid():
    with pytest.raises(BusinessError, match="期号表达无效"):
        rules.expand_issues("abc")


def test_suggest_complete_year_beats_older_gap():
    donation = {"issn": "1000-0001", "year": "2025", "issues": ["1", "2", "3"]}
    entries = rules.suggest(donation, libs(
        ("甲馆", [gap("1", since="2026-02-01"), gap("2", since="2026-02-01"), gap("3", since="2026-02-01")]),
        ("乙馆", [gap("2", since="2025-06-01"), gap("5", since="2025-06-01")]),
    ), now=NOW)
    assert [e["library"] for e in entries] == ["甲馆", "乙馆"]
    assert entries[0]["completes_year"] and entries[0]["remaining"] == []
    assert "齐套优先" in entries[0]["reason"]
    assert entries[1]["covered"] == ["2"] and entries[1]["remaining"] == ["5"]
    assert "让位于甲馆全年齐套" in entries[1]["reason"]


def test_suggest_stale_gap_overrides_complete():
    donation = {"issn": "1000-0001", "year": "2025", "issues": ["1", "2", "3"]}
    entries = rules.suggest(donation, libs(
        ("甲馆", [gap("1"), gap("2"), gap("3")]),
        ("乙馆", [gap("2", since="2020-01-01"), gap("5", since="2020-01-01")]),
    ), now=NOW)
    assert entries[0]["library"] == "乙馆" and entries[0]["stale"]
    assert "超龄缺期兜底优先" in entries[0]["reason"]
    assert "让位于乙馆超龄缺期" in entries[1]["reason"]


def test_suggest_ignores_other_years_and_fulfilled():
    donation = {"issn": "1000-0001", "year": "2025", "issues": ["1"]}
    libraries = libs(("甲馆", [gap("7", year="2024")]))
    libraries[0]["gaps"].append(dict(gap("1"), status="fulfilled"))
    assert rules.suggest(donation, libraries, now=NOW) == []


def test_register_donation_idempotent(dbs):
    a = dbs.register_donation("1000-0001", "图情学刊", "2025", "1-3", "张氏赠")
    b = dbs.register_donation("1000-0001", "图情学刊", "2025", "1-3", "张氏赠")
    assert a["id"] == b["id"] and len(dbs.list_donations()) == 1


def test_claim_idempotent_and_blocked_after_allocation(dbs):
    la = dbs.register_library("甲馆", gaps=[gap("1")])
    don = dbs.register_donation("1000-0001", "图情学刊", "2025", "1")
    first = dbs.claim(don["id"], la["id"])
    again = dbs.claim(don["id"], la["id"])
    assert [c["id"] for c in first["claims"]] == [c["id"] for c in again["claims"]]
    dbs.confirm(don["id"], first["claims"][0]["id"], 0)
    with pytest.raises(BusinessError, match="不再受理认领"):
        dbs.claim(don["id"], la["id"])


def test_confirm_single_destination_and_retry(dbs):
    la = dbs.register_library("甲馆", gaps=[gap("1")])
    lb = dbs.register_library("乙馆", gaps=[gap("1")])
    don = dbs.register_donation("1000-0001", "图情学刊", "2025", "1")
    dbs.claim(don["id"], la["id"])
    dbs.claim(don["id"], lb["id"])
    claims = {c["library"]: c for c in dbs.donation(don["id"])["claims"]}
    done = dbs.confirm(don["id"], claims["甲馆"]["id"], 0)
    assert done["status"] == "allocated"
    assert done["confirmed"]["library"] == "甲馆"
    assert {c["library"]: c["status"] for c in done["claims"]} == {"甲馆": "confirmed", "乙馆": "rejected"}
    retry = dbs.confirm(don["id"], claims["甲馆"]["id"], 1)  # 同一去向重试：幂等
    assert retry["confirmed"]["library"] == "甲馆"
    with pytest.raises(BusinessError, match="已确认其他去向"):
        dbs.confirm(don["id"], claims["乙馆"]["id"], 0)


def test_confirm_stale_revision(dbs):
    la = dbs.register_library("甲馆", gaps=[gap("1")])
    don = dbs.register_donation("1000-0001", "图情学刊", "2025", "1")
    dbs.claim(don["id"], la["id"])
    claim_id = dbs.donation(don["id"])["claims"][0]["id"]
    with pytest.raises(BusinessError, match="版本已更新"):
        dbs.confirm(don["id"], claim_id, 99)


def test_confirm_concurrent_only_one_wins(dbs):
    la = dbs.register_library("甲馆", gaps=[gap("1")])
    lb = dbs.register_library("乙馆", gaps=[gap("1")])
    don = dbs.register_donation("1000-0001", "图情学刊", "2025", "1")
    dbs.claim(don["id"], la["id"])
    dbs.claim(don["id"], lb["id"])
    claim_ids = [c["id"] for c in dbs.donation(don["id"])["claims"]]
    barrier = threading.Barrier(len(claim_ids))
    results, errors = [], []

    def hit(cid):
        barrier.wait()
        try:
            results.append(dbs.confirm(don["id"], cid, 0))
        except BusinessError as e:
            errors.append(e)

    threads = [threading.Thread(target=hit, args=(cid,)) for cid in claim_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) == 1 and len(errors) == 1
    assert errors[0].status == 409
    final = dbs.donation(don["id"])
    assert final["status"] == "allocated"
    assert sum(c["status"] == "confirmed" for c in final["claims"]) == 1


def test_arrive_requires_allocation(dbs):
    dbs.register_library("甲馆", gaps=[gap("1")])
    don = dbs.register_donation("1000-0001", "图情学刊", "2025", "1")
    with pytest.raises(BusinessError, match="不能登记到馆"):
        dbs.arrive(don["id"])


def test_no_writeoff_before_arrival(dbs):
    la = dbs.register_library("甲馆", gaps=[gap("1")])
    don = dbs.register_donation("1000-0001", "图情学刊", "2025", "1")
    dbs.claim(don["id"], la["id"])
    dbs.confirm(don["id"], dbs.donation(don["id"])["claims"][0]["id"], 0)
    assert dbs.get_library(la["id"])["gaps"][0]["status"] == "open"  # 复核确认不核销


def test_arrive_writes_off_only_filled_issues(dbs):
    la = dbs.register_library("甲馆", gaps=[gap("1"), gap("2"), gap("3"), gap("7", year="2024")])
    don = dbs.register_donation("1000-0001", "图情学刊", "2025", "1-3")
    dbs.claim(don["id"], la["id"])
    dbs.confirm(don["id"], dbs.donation(don["id"])["claims"][0]["id"], 0)
    done = dbs.arrive(don["id"])
    assert done["status"] == "arrived"
    assert [w["issue"] for w in done["writeoffs"]] == ["1", "2", "3"]
    remaining = dbs.get_library(la["id"])
    assert [(g["year"], g["issue"]) for g in remaining["gaps"] if g["status"] == "open"] == [("2024", "7")]


def test_arrive_retry_does_not_duplicate(dbs):
    la = dbs.register_library("甲馆", gaps=[gap("1"), gap("2")])
    don = dbs.register_donation("1000-0001", "图情学刊", "2025", "1-2")
    dbs.claim(don["id"], la["id"])
    dbs.confirm(don["id"], dbs.donation(don["id"])["claims"][0]["id"], 0)
    first = dbs.arrive(don["id"])
    second = dbs.arrive(don["id"])
    assert [w["issue"] for w in first["writeoffs"]] == [w["issue"] for w in second["writeoffs"]] == ["1", "2"]
    assert dbs.overview()["metrics"]["writeoffs"] == 2


def test_overview_shows_reasons_and_remaining(dbs):
    la = dbs.register_library("甲馆", gaps=[gap("1", since="2026-02-01"), gap("2", since="2026-02-01"), gap("3", since="2026-02-01")])
    lb = dbs.register_library("乙馆", gaps=[gap("2", since="2025-06-01"), gap("5", since="2025-06-01")])
    don = dbs.register_donation("1000-0001", "图情学刊", "2025", "1-3")
    dbs.claim(don["id"], la["id"])
    dbs.claim(don["id"], lb["id"])
    overview = dbs.overview()
    detail = next(d for d in overview["donations"] if d["id"] == don["id"])
    assert detail["suggestions"][0]["library"] == "甲馆"
    assert "齐套优先" in detail["suggestions"][0]["reason"]
    assert detail["suggestions"][1]["remaining"] == ["5"]
    remaining = {lib["name"]: lib["open"] for lib in overview["libraries"]}
    assert remaining == {"甲馆": 3, "乙馆": 2}
