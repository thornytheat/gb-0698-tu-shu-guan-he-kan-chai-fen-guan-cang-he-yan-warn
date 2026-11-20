"""捐赠分派持久化：认领、复核确认唯一去向、整册到馆核销。

并发与幂等：
- 认领按 (donation_id, library_id) 唯一，重复认领复用原记录；
- 确认去向在 BEGIN IMMEDIATE 事务内完成，confirmed 部分唯一索引保证一册只有一个去向；
- 同一认领重复确认幂等返回；他人已确认时返回 409；
- 核销以 (library_id, issn, year, issue) 为主键 INSERT OR IGNORE，重复到馆不重复核销。
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

from app.config import DATA_DIR
from app.errors import BusinessError
from app.modules.m8_donation import rules

SCHEMA = """
CREATE TABLE IF NOT EXISTS d_libraries(
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS d_gaps(
  library_id TEXT NOT NULL,
  issn TEXT NOT NULL,
  title TEXT NOT NULL,
  year TEXT NOT NULL,
  issue TEXT NOT NULL,
  since TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  PRIMARY KEY(library_id, issn, year, issue));
CREATE TABLE IF NOT EXISTS d_donations(
  id TEXT PRIMARY KEY,
  issn TEXT NOT NULL,
  title TEXT NOT NULL,
  year TEXT NOT NULL,
  issues TEXT NOT NULL,
  donor TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'registered',
  created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS d_claims(
  id TEXT PRIMARY KEY,
  donation_id TEXT NOT NULL,
  library_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  revision INTEGER NOT NULL DEFAULT 0,
  created TEXT NOT NULL,
  UNIQUE(donation_id, library_id));
CREATE UNIQUE INDEX IF NOT EXISTS d_claims_one_confirmed
  ON d_claims(donation_id) WHERE status='confirmed';
CREATE TABLE IF NOT EXISTS d_writeoffs(
  library_id TEXT NOT NULL,
  issn TEXT NOT NULL,
  year TEXT NOT NULL,
  issue TEXT NOT NULL,
  donation_id TEXT NOT NULL,
  claim_id TEXT NOT NULL,
  created TEXT NOT NULL,
  PRIMARY KEY(library_id, issn, year, issue));
"""


def _now():
    return datetime.now(timezone.utc).isoformat()


def _ident(prefix, *parts):
    digest = hashlib.sha256("\n".join(str(p) for p in parts).encode()).hexdigest()
    return f"{prefix}-{digest[:12]}"


def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATA_DIR / "runs.sqlite", timeout=15)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def _check_year(year):
    text = str(year).strip()
    if not text.isdigit() or not 1900 <= int(text) <= 2100:
        raise BusinessError("YEAR", "年份无效")
    return text


def _check_gap(gap):
    if not isinstance(gap, dict):
        raise BusinessError("GAPS", "缺期须为对象列表")
    out = {}
    for field in ("issn", "title", "issue"):
        value = gap.get(field)
        if not isinstance(value, str) or not value.strip():
            raise BusinessError("GAPS", f"缺期缺少{field}")
        out[field] = value.strip()
    out["year"] = _check_year(gap.get("year", ""))
    since = str(gap.get("since") or _now()[:10]).strip()
    rules.age_days(since, datetime.now(timezone.utc).date())  # 校验日期格式
    if since > _now()[:10]:
        raise BusinessError("SINCE", "缺期起始日期不能晚于今天")
    out["since"] = since
    return out


def register_library(name, gaps=(), text=None):
    """登记馆与缺期。text 为馆藏CSV时经既有流水线计算缺期；同名馆复用，缺期并入。"""
    if not isinstance(name, str) or not name.strip():
        raise BusinessError("LIBRARY", "馆名不能为空")
    name = name.strip()
    entries = []
    if text is not None:
        if not isinstance(text, str):
            raise BusinessError("TEXT", "输入须为文本")
        from app.pipeline import run
        for row in run(text)["gaps"]:
            entries.extend({"issn": row["issn"], "title": row["title"], "year": row["year"],
                            "issue": issue, "since": _now()[:10]} for issue in row["missing"])
    entries.extend(_check_gap(g) for g in gaps or ())
    ident = _ident("lib", name)
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO d_libraries(id,name,created) VALUES(?,?,?)",
                   (ident, name, _now()))
        for e in entries:
            db.execute("INSERT OR IGNORE INTO d_gaps(library_id,issn,title,year,issue,since)"
                       " VALUES(?,?,?,?,?,?)",
                       (ident, e["issn"], e["title"], e["year"], e["issue"], e["since"]))
    return get_library(ident)


def get_library(ident):
    today = datetime.now(timezone.utc).date()
    with connect() as db:
        row = db.execute("SELECT * FROM d_libraries WHERE id=?", (ident,)).fetchone()
        if row is None:
            raise BusinessError("NOT_FOUND", "馆不存在", 404)
        gaps = [dict(r) for r in db.execute(
            "SELECT * FROM d_gaps WHERE library_id=? ORDER BY issn,year,issue", (ident,))]
    lib = dict(row)
    lib["gaps"] = sorted(gaps, key=lambda g: (g["issn"], g["year"], rules.issue_order(g["issue"])))
    open_gaps = [g for g in lib["gaps"] if g["status"] == "open"]
    lib["open"] = len(open_gaps)
    lib["oldest_days"] = max((rules.age_days(g["since"], today) for g in open_gaps), default=0)
    for g in lib["gaps"]:
        g["age_days"] = rules.age_days(g["since"], today)
    return lib


def list_libraries():
    with connect() as db:
        ids = [r["id"] for r in db.execute("SELECT id FROM d_libraries ORDER BY name")]
    return [get_library(i) for i in ids]


def register_donation(issn, title, year, issues, donor=""):
    """登记捐赠合刊。同刊同年同期次同捐赠人复用同一册。"""
    for field, value in (("issn", issn), ("title", title)):
        if not isinstance(value, str) or not value.strip():
            raise BusinessError("DONATION", f"捐赠缺少{field}")
    issn, title = issn.strip(), title.strip()
    year = _check_year(year)
    donor = str(donor or "").strip()
    expanded = rules.expand_issues(issues)
    ident = _ident("don", issn, year, ",".join(expanded), donor)
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO d_donations(id,issn,title,year,issues,donor,created)"
                   " VALUES(?,?,?,?,?,?,?)",
                   (ident, issn, title, year, json.dumps(expanded, ensure_ascii=False), donor, _now()))
    return donation(ident)


def _row_dicts(rows):
    return [dict(r) for r in rows]


def donation(ident, now=None):
    with connect() as db:
        row = db.execute("SELECT * FROM d_donations WHERE id=?", (ident,)).fetchone()
        if row is None:
            raise BusinessError("NOT_FOUND", "捐赠册不存在", 404)
        claims = _row_dicts(db.execute(
            "SELECT * FROM d_claims WHERE donation_id=? ORDER BY created", (ident,)))
        writeoffs = _row_dicts(db.execute(
            "SELECT * FROM d_writeoffs WHERE donation_id=?", (ident,)))
    d = dict(row)
    d["issues"] = json.loads(d["issues"])
    libraries = list_libraries()
    names = {lib["id"]: lib["name"] for lib in libraries}
    d["claims"] = [dict(c, library=names.get(c["library_id"], c["library_id"])) for c in claims]
    d["confirmed"] = next((c for c in d["claims"] if c["status"] == "confirmed"), None)
    d["writeoffs"] = sorted(writeoffs, key=lambda w: rules.issue_order(w["issue"]))
    d["suggestions"] = rules.suggest(d, libraries, now=now)
    return d


def list_donations():
    with connect() as db:
        ids = [r["id"] for r in db.execute("SELECT id FROM d_donations ORDER BY created DESC")]
    return [donation(i) for i in ids]


def claim(donation_id, library_id):
    """馆认领一册。重复认领幂等；已确认去向后不再受理。"""
    ident = _ident("clm", donation_id, library_id)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        don = db.execute("SELECT status FROM d_donations WHERE id=?", (donation_id,)).fetchone()
        if don is None:
            raise BusinessError("NOT_FOUND", "捐赠册不存在", 404)
        if db.execute("SELECT 1 FROM d_libraries WHERE id=?", (library_id,)).fetchone() is None:
            raise BusinessError("NOT_FOUND", "馆不存在", 404)
        if don["status"] != "registered":
            raise BusinessError("ALLOCATED", "该册已确认去向，不再受理认领", 409)
        db.execute("INSERT OR IGNORE INTO d_claims(id,donation_id,library_id,created)"
                   " VALUES(?,?,?,?)", (ident, donation_id, library_id, _now()))
    return donation(donation_id)


def confirm(donation_id, claim_id, revision):
    """复核确认唯一去向。同一认领重复确认幂等；他人已确认返回409。"""
    if type(revision) is not int:
        raise BusinessError("REVISION", "版本须为整数")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        don = db.execute("SELECT status FROM d_donations WHERE id=?", (donation_id,)).fetchone()
        if don is None:
            raise BusinessError("NOT_FOUND", "捐赠册不存在", 404)
        claim_row = db.execute("SELECT * FROM d_claims WHERE id=? AND donation_id=?",
                               (claim_id, donation_id)).fetchone()
        if claim_row is None:
            raise BusinessError("NOT_FOUND", "认领记录不存在", 404)
        if claim_row["status"] != "confirmed":
            if don["status"] != "registered":
                raise BusinessError("ALLOCATED", "该册已确认其他去向", 409)
            if claim_row["revision"] != revision:
                raise BusinessError("STALE", "版本已更新，请刷新", 409)
            changed = db.execute("UPDATE d_claims SET status='confirmed',revision=revision+1"
                                 " WHERE id=? AND status='pending'", (claim_id,)).rowcount
            if not changed:
                raise BusinessError("STALE", "认领状态已变化，请刷新", 409)
            try:
                db.execute("UPDATE d_claims SET status='rejected'"
                           " WHERE donation_id=? AND status='pending'", (donation_id,))
                db.execute("UPDATE d_donations SET status='allocated' WHERE id=?", (donation_id,))
            except sqlite3.IntegrityError:
                raise BusinessError("ALLOCATED", "该册已确认其他去向", 409)
    return donation(donation_id)


def arrive(donation_id):
    """整册到馆：核销确认馆补到的期次。重复到馆幂等，不重复核销。"""
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        don = db.execute("SELECT * FROM d_donations WHERE id=?", (donation_id,)).fetchone()
        if don is None:
            raise BusinessError("NOT_FOUND", "捐赠册不存在", 404)
        if don["status"] == "registered":
            raise BusinessError("NOT_ALLOCATED", "尚未复核确认去向，不能登记到馆", 409)
        if don["status"] == "allocated":
            claim_row = db.execute("SELECT * FROM d_claims WHERE donation_id=? AND status='confirmed'",
                                   (donation_id,)).fetchone()
            open_issues = {r["issue"] for r in db.execute(
                "SELECT issue FROM d_gaps WHERE library_id=? AND issn=? AND year=? AND status='open'",
                (claim_row["library_id"], don["issn"], don["year"]))}
            for issue in json.loads(don["issues"]):
                if issue not in open_issues:
                    continue  # 只核销该馆补到的期次
                db.execute("INSERT OR IGNORE INTO d_writeoffs"
                           "(library_id,issn,year,issue,donation_id,claim_id,created)"
                           " VALUES(?,?,?,?,?,?,?)",
                           (claim_row["library_id"], don["issn"], don["year"], issue,
                            donation_id, claim_row["id"], _now()))
                db.execute("UPDATE d_gaps SET status='fulfilled'"
                           " WHERE library_id=? AND issn=? AND year=? AND issue=? AND status='open'",
                           (claim_row["library_id"], don["issn"], don["year"], issue))
            db.execute("UPDATE d_donations SET status='arrived' WHERE id=? AND status='allocated'",
                       (donation_id,))
    return donation(donation_id)


def overview(now=None):
    """复核页面数据：各馆剩余缺期、各册建议与认领、核销记录。"""
    libraries = list_libraries()
    donations = list_donations()
    return {
        "libraries": libraries,
        "donations": donations,
        "metrics": {
            "libraries": len(libraries),
            "donations": len(donations),
            "pending_claims": sum(1 for d in donations for c in d["claims"] if c["status"] == "pending"),
            "writeoffs": sum(len(d["writeoffs"]) for d in donations),
        },
    }
