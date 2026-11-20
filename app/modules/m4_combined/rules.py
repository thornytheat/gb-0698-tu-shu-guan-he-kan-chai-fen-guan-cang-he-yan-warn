from app.report import report

def collisions(rows):
    owners={};conflicts=[]
    for r in rows:
        if r["status"]!="held":continue
        for issue in r["issues"]:
            key=(r["journal_key"],r["year"],issue,r["copy"])
            previous=owners.get(key)
            if previous and previous["binding"]!=r["binding"]:conflicts.append({"issue":issue,"copy":r["copy"],"left":previous["record_id"],"right":r["record_id"],"reason":"BINDING_CONFLICT"})
            owners[key]=r
    return conflicts

def apply(ctx):
    conflict=collisions(ctx["expanded"]);ctx["binding_conflicts"]=conflict
    out=[dict(r,physical_books=1,covered_issues=len(r["issues"])) for r in ctx["expanded"] if r["status"]=="held"]
    ctx["held"]=out;return report(out,合刊=sum(len(r["issues"])>1 for r in out),装订冲突=len(conflict))
