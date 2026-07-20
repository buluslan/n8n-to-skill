#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
amazon-review-analyzer 的 IO 辅助脚本（确定性操作）。
职责：读 CSV / 校验必要列 / 对 22 个标签列算分布。
打标和洞察生成是生成性任务，由 Agent(Claude) 直接做，不在本脚本。

用法：
    python3 io.py count <reviews.csv>
    python3 io.py stats <tagged.csv> <out_stats.csv>
"""
import csv
import sys
from collections import Counter

# 评论文本/元数据列（非标签列）——统计时排除这些
_TEXT_COLS = {
    "review_id", "title", "text", "rating", "date", "asin", "author", "vp",
    "标题", "标题(翻译)", "内容", "内容(翻译)", "星级", "VP评论", "评论ID", "作者", "日期",
}


def cmd_count(csv_path):
    """校验 CSV，打印行数 + 列名，确认有评论文本列。"""
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("⚠ CSV 为空"); sys.exit(1)
    cols = list(rows[0].keys())
    text_candidates = ["内容", "内容(翻译)", "text", "Text"]
    has_text = any(c in cols for c in text_candidates)
    print(f"行数: {len(rows)}")
    print(f"列: {cols}")
    if not has_text:
        print(f"❌ 缺评论文本列（需 内容 / 内容(翻译) / text 任一）"); sys.exit(1)
    print("✅ 校验通过（含评论文本列）")


def cmd_stats(tagged_csv, out_path):
    """读 tagged.csv，对所有标签列（排除文本/元数据列）算值分布，写 stats.csv。"""
    with open(tagged_csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("⚠ tagged.csv 为空"); sys.exit(1)
    tag_cols = [c for c in rows[0].keys() if c.strip() not in _TEXT_COLS]
    if not tag_cols:
        print("⚠ 没有标签列（除文本/元数据列外无其他列）"); sys.exit(1)
    out_rows = []
    for col in tag_cols:
        c = Counter((r.get(col) or "").strip() for r in rows)
        total = sum(v for k, v in c.items() if k and k != "TAG_FAILED")
        for tag, n in c.most_common():
            display = tag if tag else "(空)"
            pct = f"{n/total*100:.1f}%" if total else "0%"
            out_rows.append({"标签列": col, "标签值": display, "计数": n, "占比": pct})
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["标签列", "标签值", "计数", "占比"])
        w.writeheader()
        w.writerows(out_rows)
    print(f"✅ 统计写入 {out_path}（{len(tag_cols)} 个标签列）")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "count" and len(sys.argv) >= 3:
        cmd_count(sys.argv[2])
    elif cmd == "stats" and len(sys.argv) >= 4:
        cmd_stats(sys.argv[2], sys.argv[3])
    else:
        print("用法:\n  io.py count <reviews.csv>\n  io.py stats <tagged.csv> <out_stats.csv>")


if __name__ == "__main__":
    main()
