# 接口

`POST /api/run`：{"text":"CSV内容"}。同规则版本与输入摘要只产生一条批次。

`GET/POST /api/1` 至 `/api/7`：独立样例或自定义文件计算。各模块返回 report、quarantine、balance。

`POST /api/review`：id、整数revision、decision取通过或退回。旧版本409；阻断项不能通过。

`GET /api/export/{id}`：唯一证据CSV。`GET /health`：存活检查。

## M8 捐赠分派

`POST /api/8/libraries`：{"name":"甲馆","gaps":[{"issn","title","year","issue","since?"}]} 或 {"name","text":"馆藏CSV"}（经既有流水线计算缺期）。同名馆复用，缺期并入。

`POST /api/8/donations`：{"issn","title","year","issues":"1-3","donor"?}。同册重复登记复用同一记录，返回含分派建议（名次、覆盖期、剩余缺期、理由）。

`POST /api/8/claims`：{"donation_id","library_id"}。同馆同册认领幂等；已确认去向后409。

`POST /api/8/review`：{"donation_id","claim_id","revision"}。确认唯一去向，其余认领自动驳回；同一认领重试幂等，他人已确认409，版本不符409。

`POST /api/8/arrive`：{"donation_id"}。整册到馆后核销确认馆补到的期次；重复到馆返回既有核销结果，不重复核销。未确认去向409。

`GET /api/8`、`GET /api/8/libraries`、`GET /api/8/donations`、`GET /api/8/donations/{id}`：复核页面数据（各馆剩余缺期、建议理由、认领与核销记录）。不做配送。

错误：结构/数值422，版本冲突409，不存在404，文件过大413。逐行异常进入quarantine。
