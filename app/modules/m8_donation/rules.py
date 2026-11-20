"""捐赠合刊分派建议：齐套优先，超龄兜底。

优先级规则（确定性、可解释）：
1. 超龄兜底：被覆盖缺期中有积压 >= stale_days 的缺期，所在馆最优先；
2. 齐套优先：整册到馆后当年不再缺期的馆次之；
3. 同级比较：覆盖期数多者先，再按最老缺期积压天数，再按馆名。
"""
from datetime import datetime, timezone

from app.errors import BusinessError
from app.modules.m3_issues.rules import expand

STALE_DAYS = 730  # 缺期积压超龄阈值（天）


def issue_order(issue):
    text = str(issue)
    return (0, int(text)) if text.isdigit() else (1, text)


def expand_issues(spec):
    """期次表达：逗号分隔，支持 3 / 1-6 / 2/5 混写，如 '1-6,8'。去重排序。"""
    if isinstance(spec, (list, tuple)):
        parts = [str(x) for x in spec]
    else:
        parts = str(spec).replace("，", ",").split(",")
    out = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        for issue in expand(part):
            if issue not in out:
                out.append(issue)
    if not out:
        raise BusinessError("ISSUE_SYNTAX", "期号表达无效")
    return sorted(out, key=issue_order)


def age_days(since, now):
    """缺期积压天数。since 为 YYYY-MM-DD 或 ISO 时间，now 为 date。"""
    try:
        day = datetime.fromisoformat(str(since)[:10]).date()
    except ValueError:
        raise BusinessError("SINCE", "缺期起始日期无效")
    return max((now - day).days, 0)


def suggest(donation, libraries, now=None, stale_days=STALE_DAYS):
    """对一册捐赠合刊给出分派建议排序。

    donation: {"issn","title","year","issues":[...]}；
    libraries: [{"id","name","gaps":[{"issn","year","issue","since","status"}]}]。
    仅统计与同刊同年且 status=open 的缺期；返回按优先级排序的建议，每条含分派理由。
    """
    now = now or datetime.now(timezone.utc).date()
    issues = [str(i) for i in donation["issues"]]
    entries = []
    for lib in libraries:
        open_gaps = {str(g["issue"]): g["since"] for g in lib.get("gaps", [])
                     if g.get("status", "open") == "open"
                     and g["issn"] == donation["issn"] and str(g["year"]) == str(donation["year"])}
        covered = [i for i in issues if i in open_gaps]
        if not covered:
            continue
        remaining = sorted((i for i in open_gaps if i not in issues), key=issue_order)
        oldest_issue = max(covered, key=lambda i: (age_days(open_gaps[i], now), issue_order(i)))
        oldest_days = age_days(open_gaps[oldest_issue], now)
        entries.append({
            "library_id": lib["id"], "library": lib["name"],
            "covered": sorted(covered, key=issue_order),
            "remaining": remaining,
            "completes_year": not remaining,
            "oldest_issue": oldest_issue,
            "oldest_days": oldest_days,
            "stale": oldest_days >= stale_days,
        })
    entries.sort(key=lambda e: (not e["stale"], not e["completes_year"],
                                -len(e["covered"]), -e["oldest_days"], e["library"]))
    winner = entries[0] if entries else None
    for rank, entry in enumerate(entries, 1):
        entry["rank"] = rank
        entry["reason"] = _reason(entry, winner, donation, stale_days)
    return entries


def _reason(entry, winner, donation, stale_days):
    base = "覆盖" + "、".join(entry["covered"]) + "期"
    if entry is winner:
        if entry["stale"]:
            return (f"{base}；{entry['oldest_issue']}期已积压{entry['oldest_days']}天，"
                    f"超过{stale_days}天阈值，超龄缺期兜底优先")
        if entry["completes_year"]:
            return (f"{base}；{donation['year']}年仅缺此{len(entry['covered'])}期，"
                    "整册到馆即全年齐套，齐套优先")
        return f"{base}；覆盖期数最多"
    parts = [base]
    if entry["remaining"]:
        parts.append("分派后仍缺" + "、".join(entry["remaining"]) + "期")
    if entry["completes_year"] and winner["completes_year"]:
        parts.append(f"同为齐套，覆盖期数与积压时长不及{winner['library']}")
    elif winner["stale"] and not entry["stale"]:
        parts.append(f"最老缺期积压{entry['oldest_days']}天未超龄，让位于{winner['library']}超龄缺期")
    elif winner["completes_year"] and not entry["completes_year"]:
        parts.append(f"不能齐套，让位于{winner['library']}全年齐套")
    else:
        parts.append(f"覆盖期数少于{winner['library']}")
    return "；".join(parts)
