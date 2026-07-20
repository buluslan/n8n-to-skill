#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_skill.py — n8n-to-skill 的软校验脚本（反"文档壳"）。

校验【生成的产物 skill】（用户用 n8n-to-skill 转出来的那个 skill）是否
包含目标对等重写必须交代清楚的关键信息。这是 quick_validate.py（frontmatter
硬校验）之外的语义层校验。

用法：
    python3 check_skill.py <生成的skill目录>

退出码：0 = 全绿；1 = 有缺失。
"""
import sys
import os
import re

# 每类至少命中一个变体即算通过（允许措辞差异，治"文档壳"非"措辞洁癖"）
REQUIRED_SECTIONS = {
    "触发语义": ["触发", "何时", "当用户", "trigger", "入口"],
    "输入约定": ["输入", "入参", "input"],
    "输出约定": ["输出", "产出", "output", "结果"],
    "凭证边界": ["凭证", "凭据", ".env", "环境变量", "api key", "api_key", "无需凭证", "不需要凭证"],
    "失败降级": ["失败", "降级", "警告", "warning", "出错", "异常", "容错"],
}


def parse_frontmatter(text):
    """简易 YAML frontmatter 解析（只取 name/description）。"""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def check(skill_dir):
    skill_md = os.path.join(skill_dir, "SKILL.md")
    problems = []
    if not os.path.isfile(skill_md):
        return [f"❌ 缺少 SKILL.md: {skill_md}"]
    text = open(skill_md, encoding="utf-8").read()
    low = text.lower()

    # 1. frontmatter 硬检查
    fm = parse_frontmatter(text)
    if "name" not in fm:
        problems.append("❌ frontmatter 缺 name")
    else:
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", fm["name"]):
            problems.append(f"❌ name 不合规（须连字符小写）: {fm['name']}")
    desc = fm.get("description", "")
    if not desc:
        problems.append("❌ frontmatter 缺 description")
    else:
        if "<" in desc or ">" in desc:
            problems.append("❌ description 含尖括号（quick_validate 会拒）")
        if len(desc) > 1024:
            problems.append(f"❌ description 超 1024 字符（{len(desc)}）")

    # 2. 关键段落软检查
    missing_phrases = []
    for cat, variants in REQUIRED_SECTIONS.items():
        if not any(v.lower() in low for v in variants):
            missing_phrases.append(cat)
    if missing_phrases:
        problems.append("❌ SKILL.md 缺少关键语义段（文档壳风险）: " + ", ".join(missing_phrases))

    # 3. 行数提醒（quality-checklist 建议 <500）
    lines = text.count("\n") + 1
    if lines > 500:
        problems.append(f"⚠ SKILL.md {lines} 行，超过 500 建议拆 references")

    return problems, {"name": fm.get("name"), "lines": lines,
                      "desc_len": len(desc), "missing_phrases": missing_phrases}


def main():
    if len(sys.argv) < 2:
        print("用法: python3 check_skill.py <生成的skill目录>", file=sys.stderr)
        sys.exit(2)
    skill_dir = sys.argv[1]
    problems, info = check(skill_dir)
    print("=" * 60)
    print(f"校验目标: {skill_dir}")
    print(f"name={info['name']}  行数={info['lines']}  desc长度={info['desc_len']}")
    print("-" * 60)
    if not problems:
        print("✅ 关键段落校验全绿")
        # 关键短语命中明细（正向反馈）
        text = open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8").read().lower()
        for cat, variants in REQUIRED_SECTIONS.items():
            hit = [v for v in variants if v.lower() in text]
            print(f"  ✓ {cat}: 命中 {hit[0]}")
    else:
        print(f"🔴 发现 {len(problems)} 个问题:")
        for p in problems:
            print(f"  {p}")
    print("=" * 60)
    sys.exit(0 if not problems else 1)


if __name__ == "__main__":
    main()
