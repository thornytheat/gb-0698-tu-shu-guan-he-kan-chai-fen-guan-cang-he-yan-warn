from app.report import report

def book_count(rows):
    return len({(r["journal_key"],r["year"],r["copy"],(r["binding"] or r.get("record_id",""))) for r in rows if r["status"]=="held"})

def apply(ctx):
    ctx["books"]=book_count(ctx["held"])
    ctx["balance"]={"input":ctx["input_count"],"accepted":ctx["input_count"]-len(ctx["quarantine"])-ctx["blank_rows"],"quarantined":len(ctx["quarantine"]),"blank":ctx["blank_rows"]}
    rows=[{"kind":"实体册","count":ctx["books"]},{"kind":"覆盖期次","count":sum(len(r["issues"]) for r in ctx["held"])},{"kind":"合刊记录","count":sum(len(r["issues"])>1 for r in ctx["held"])},{"kind":"冲突","count":len(ctx["binding_conflicts"])}]
    return report(rows,实体册=ctx["books"],装订冲突=len(ctx["binding_conflicts"]))
