import re,unicodedata
from app.report import report,quarantine
from app.errors import BusinessError
ALIASES={"环境监测技术":"环境监测技术","环境监测科技":"环境监测技术","数据工程月刊":"数据工程月刊","数据工程":"数据工程月刊"}
def canonical(title,issn):
    title=unicodedata.normalize("NFKC",title).replace(" ","").strip()
    if not re.fullmatch(r"[0-9]{4}-[0-9]{3}[0-9X]",issn):raise BusinessError("ISSN","ISSN格式无效")
    return ALIASES.get(title,title),issn

def apply(ctx):
    out=[];identity={}
    for r in ctx["raw"]:
        try:
            name,issn=canonical(r["title"],r["issn"])
            x=dict(r);x["canonical"]=name;x["journal_key"]=issn;out.append(x);identity.setdefault(issn,set()).add(name)
        except BusinessError as e:quarantine(ctx,r,e.code)
    conflicts={key for key,names in identity.items() if len(names)>1}
    ctx["canonical"]=out;ctx["identity_conflicts"]=sorted(conflicts)
    return report(out,期刊=len(identity),刊名冲突=len(conflicts))
