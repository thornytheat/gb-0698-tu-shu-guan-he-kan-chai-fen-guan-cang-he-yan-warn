# 图书馆合刊拆分与馆藏核验

期刊编目数据员使用本工具解析期刊卷期和合刊标识，复核年度馆藏缺期与重复装订。

## 核心计算

卷期展开使用显式范围语法，合刊只占一册但覆盖多期；增刊独立编号，停刊区间不报缺期。

## 启动

```bash
docker compose up --build -d
docker compose exec -T app pytest -q
docker compose config --quiet
```

浏览器访问 http://localhost:18212 。默认载入仓内样例。工具条可选择CSV文件运行；样例文件位于 `sample_data/instrument.csv`。重复执行同一内容复用同一批次。

## 模块

- M1 馆藏接收：`/module/1`，独立计算 `POST /api/1`。
- M2 刊名归一：`/module/2`，独立计算 `POST /api/2`。
- M3 卷期展开：`/module/3`，独立计算 `POST /api/3`。
- M4 合刊裁决：`/module/4`，独立计算 `POST /api/4`。
- M5 缺期定位：`/module/5`，独立计算 `POST /api/5`。
- M6 装订对账：`/module/6`，独立计算 `POST /api/6`。
- M7 补录复核：`/module/7`，独立计算 `POST /api/7`。

## 输入与输出

CSV可用UTF-8或GB18030；上传保留字符串编号和物理行号。POST `/api/run` 接收 `text` 字段。`GET /api/runs` 查询历史，`POST /api/review` 接收 id、revision、decision。导出按钮下载唯一证据CSV，含运行摘要与隔离记录。

SQLite命名卷保存运行记录。重建演示数据可更换卷名后重启。无需外部网络数据。规则定义见 `docs/DATA-DICTIONARY.md`；边界和测试对应关系见 `docs/DEPTH.md`。

## 范围

只处理仓内CSV定义，不连接生产系统。单次输入最多2MB。原始输入流式解析，业务计算阶段需容纳该文件的采信行。并非无限容量任务。
