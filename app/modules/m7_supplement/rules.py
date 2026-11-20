from app.report import report

def request_list(gaps):
    return [{"issn":r["issn"],"title":r["title"],"year":r["year"],"issue":i,"status":"待补录"} for r in gaps for i in r["missing"]]

def apply(ctx):
    ctx["final"]=request_list(ctx["gaps"]);ctx["blocked"]=bool(ctx["binding_conflicts"] or ctx["identity_conflicts"])
    return report(ctx["final"],补录任务=len(ctx["final"]),冲突=len(ctx["binding_conflicts"])+len(ctx["identity_conflicts"]))
