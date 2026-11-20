import re,unicodedata
from app.report import report,quarantine
from app.errors import BusinessError

def expand(text):
    text=unicodedata.normalize("NFKC",text).strip().upper()
    if re.fullmatch(r"S[1-9][0-9]?",text):return [text]
    if not re.fullmatch(r"[0-9]+(?:[-/][0-9]+)?",text):raise BusinessError("ISSUE_SYNTAX","期号表达无效")
    if "-" in text:
        a,b=map(int,text.split("-"))
        if not 1<=a<=b<=24:raise BusinessError("ISSUE_RANGE","期号范围无效")
        return [str(x) for x in range(a,b+1)]
    nums=list(map(int,text.split("/")))
    if any(not 1<=n<=24 for n in nums) or len(set(nums))!=len(nums):raise BusinessError("ISSUE_RANGE","期号范围无效")
    return [str(x) for x in sorted(nums)]

def apply(ctx):
    out=[]
    for r in ctx["canonical"]:
        try:
            if not r["year"].isdigit() or not 1900<=int(r["year"])<=2100:raise BusinessError("YEAR","年份无效")
            if r["status"] not in {"held","suspended","missing"}:raise BusinessError("STATUS","馆藏状态无效")
            if r["status"]=="held" and not r["binding"]:raise BusinessError("BINDING_REQUIRED","在馆记录缺少装订号")
            x=dict(r);x["issues"]=expand(r["issue"]);out.append(x)
        except BusinessError as e:quarantine(ctx,r,e.code)
    ctx["expanded"]=out;return report(out,展开期次=sum(len(r["issues"]) for r in out),实体记录=len(out))
