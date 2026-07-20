---
name: amazon-review-analyzer
description: 把一批亚马逊商品评论变成「22 维度标签 + 标签分布统计 + 6 章深度洞察报告」，给跨境卖家做产品迭代决策（改款、差评应对、卖点提炼）。当用户提供评论 CSV 路径，并说「分析评论 / 给评论打标签 / 出评论洞察 / 从评论挖卖点 / 评论分析」时，必须使用本 skill。不负责实时采集评论（评论须现成 CSV）；不处理非亚马逊来源评论；不做选品分析（非评论维度）。
allowed-tools: Read, Write, Edit, Bash(python3:*)
license: MIT
metadata:
  source_workflow: 亚马逊商品评论AI深度分析工作流V1.0.json
  goal_alignment: 读评论→AI 22维打标→统计→AI 6章洞察→输出（全链路目标对等，原 18 节点收敛为 4 能力）
  conversion_date: 2026-07-20
---

# amazon-review-analyzer

## 定位
给跨境卖家：把一批亚马逊商品评论变成「每条评论的 22 维度标签 + 分布统计 + 6 章深度洞察报告」，支撑产品迭代决策（改款方向、差评应对、卖点提炼）。

## 触发
用户给一个评论 CSV 路径，并说「分析评论 / 打标签 / 出洞察 / 挖卖点 / 评论分析」任一关键词时启动。

## 输入
- 评论 CSV（utf-8）。期望列：`标题`/`标题(翻译)`、`内容`/`内容(翻译)`（核心文本）、`星级`、`VP评论`；英文列名 `title`/`text`/`rating`/`vp` 同样识别。
- **必须**有评论文本列（`内容` / `内容(翻译)` / `text` 任一），否则报错终止。

## 输出（3 个文件，落执行目录的 `output/`）
- `tagged.csv`：原评论列 + 22 个标签列
- `stats.csv`：每个标签列的值分布（计数 + 占比）
- `insight.md`：6 章深度洞察报告

## 核心能力
1. **读 CSV 校验**（脚本 `scripts/io.py count`）
2. **22 维度打标**（Agent 逐条评论，维度体系见 `references/tagging.md`）
3. **标签统计**（脚本 `scripts/io.py stats`，对 22 个标签列算分布）
4. **6 章洞察生成**（Agent，框架见 `references/insight.md`）

## 流程
1. **校验**：`python3 scripts/io.py count <reviews.csv>` → 打印行数 + 列名 → 确认有评论文本列。
2. **打标**：逐条评论按 `references/tagging.md` 输出 22 维 JSON 标签 → 汇总成 `output/tagged.csv`（原列 + 22 标签列）→ 打印进度（每 10 条一次）。
3. **统计**：`python3 scripts/io.py stats output/tagged.csv output/stats.csv` → 对 22 个标签列算值分布 → 写 `stats.csv`。
4. **洞察**：读 `stats.csv` + 精选正负各 Top3 评论，按 `references/insight.md` 的 6 章框架生成报告 → 写 `output/insight.md`。

## 凭证边界
无。目标对等重写后，原 workflow 的 Gemini API key 与 googleSheets OAuth 均已消化——LLM 能力由执行环境（Claude）直接提供，存储改为本地 CSV，无需任何外部凭证。

## 失败降级
- CSV 缺评论文本列（`内容` / `内容(翻译)` / `text`）→ 报错并指明缺哪列，终止。
- 单条评论 AI 打标失败 → 重试 3 次后该条标签全填 `未提及` / `不明`，标 `[TAG_FAILED]` 后继续，不阻塞整体。
- 评论数 < 5 → 只出 `tagged.csv` + `stats.csv`，跳过洞察（样本不足），在 `insight.md` 注明"样本不足，未生成洞察"。
- 单条评论 > 2000 字 → 截断到 2000 字打标，`tagged.csv` 标 `[truncated]`。
