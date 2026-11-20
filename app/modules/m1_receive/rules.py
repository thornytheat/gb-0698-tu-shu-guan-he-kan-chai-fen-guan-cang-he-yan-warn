from app.reader import read_rows
from app.report import report,quarantine
FIELDS="record_id title issn year volume issue copy binding status note".split()
def apply(ctx):
    rows,bad,blank=read_rows(ctx["text"],FIELDS);ctx["quarantine"].extend(bad);ctx["blank_rows"]=blank;ctx["input_count"]=len(rows)+len(bad)+blank
    out=[];seen=set()
    for r in rows:
        if not r["record_id"]:quarantine(ctx,r,"ID_REQUIRED");continue
        if r["record_id"] in seen:quarantine(ctx,r,"DUPLICATE_ID");continue
        seen.add(r["record_id"]);out.append(r)
    ctx["raw"]=out;return report(out,馆藏记录=len(out),隔离=len(ctx["quarantine"]))
