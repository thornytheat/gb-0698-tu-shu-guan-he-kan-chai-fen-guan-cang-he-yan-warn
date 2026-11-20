from app.report import report

def missing(covered,suspended,expected=12):
    return sorted(set(map(str,range(1,expected+1)))-set(covered)-set(suspended),key=int)

def apply(ctx):
    groups={}
    for r in ctx["expanded"]:groups.setdefault((r["journal_key"],r["year"],r["canonical"]),[]).append(r)
    out=[]
    for (issn,year,title),rows in groups.items():
        covered={i for r in rows if r["status"]=="held" for i in r["issues"]};suspended={i for r in rows if r["status"]=="suspended" for i in r["issues"]}
        absent=missing(covered,suspended)
        out.append({"issn":issn,"title":title,"year":year,"missing":absent,"covered":sorted(covered),"suspended":sorted(suspended),"status":"GAP" if absent else "COMPLETE"})
    ctx["gaps"]=out;return report(out,缺期=sum(len(r["missing"]) for r in out),年度=len(out))
