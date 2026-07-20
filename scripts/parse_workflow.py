#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_workflow.py — n8n-to-skill 的 Parse 阶段脚本（确定性，零漂移）。

吃进一个 n8n workflow JSON，产出一个 WorkflowIR（结构化中间表示），
供后续 Understand 阶段（LLM）做目标对等重写。

用法：
    python3 parse_workflow.py <workflow.json> [--output ir.json] [--quiet]

输出：WorkflowIR（JSON）。stdout 打印人类可读摘要（除非 --quiet）。
"""
import json
import sys
import argparse
from collections import Counter

# ── 节点行为分类规则（与 references/node-mapping.md 保持一致）─────────────
# 顺序敏感：先匹特征强的，后匹宽泛的。

# 存储协作服务的 URL 特征（httpRequest 调这些 = 存储协作，不是付费数据）
_COLLAB_URL_MARKERS = (
    "googleapis.com", "sheets.googleapis", "notion.com", "notion.so",
    "gmail", "slack.com", "feishu", "larksuite", "airtable", "telegram",
    "discord",
)
# 外部付费数据服务的 URL/类型特征
_PAID_URL_MARKERS = (
    "dataforseo", "serp", "airtop", "keepa", "helium10", "exa.ai",
    "googlesearch", "dataforseo",
)


def _http_request_category(node):
    """专门处理 httpRequest 节点：看 url 判它是存储协作/付费数据/爬虫。"""
    params = node.get("parameters", {})
    url = str(params.get("url", "")).lower()
    has_cred = bool(node.get("credentials"))
    if any(m in url for m in _COLLAB_URL_MARKERS):
        return "5_存储协作"
    if any(m in url for m in _PAID_URL_MARKERS):
        return "4_外部付费数据"
    if has_cred:
        return "4_外部付费数据"
    return "3_爬虫HTTP无认证"


def classify(node):
    """把一个 n8n 节点归入相应行为类。返回 '类名' 或 '?_未归类(type)'。"""
    t = (node.get("type") or "").lower()
    # httpRequest 单独走 url 判定（修正原型 bug）
    if "httprequest" in t:
        return _http_request_category(node)
    if any(k in t for k in ["trigger", "webhook", "cron", "scheduletrigger",
                            "formtrigger", "chattrigger", "manualtrigger"]):
        return "1_触发器"
    if "executeworkflow" in t:
        return "9_子工作流"
    if any(k in t for k in ["errortrigger", "stopanderror"]):
        return "10_错误处理"
    if any(k in t for k in ["stickynote", "noop"]):
        return "11_文档"
    if any(k in t for k in ["langchain", "openai", "anthropic", "@n8n",
                            "agent", "ai_", "googlegemini", "gemini",
                            "chatmodel", "llm"]):
        return "2_生成式AI"
    if any(k in t for k in ["googlesheets", "notion", "gmail", "slack",
                            "feishu", "lark", "airtable", "telegram", "discord"]):
        return "5_存储协作"
    if any(k in t for k in ["airtop", "dataforseo", "serp"]):
        return "4_外部付费数据"
    if any(k in t for k in ["htmlextract", "rssfeed"]):
        return "3_爬虫HTTP无认证"
    if any(k in t for k in ["set", "code", "editfields", "aggregate",
                            "splitout", "itemlists", "function"]):
        return "6_数据转换"
    # wait / sendAndWait 归人工审批（暂停等待人工决策），须在控制流前判定
    if any(k in t for k in ["wait", "sendandwait"]):
        return "8_人工审批"
    if any(k in t for k in ["if", "switch", "merge", "splitinbatches",
                            "loop"]):
        return "7_控制流"
    return "?_未归类(" + (node.get("type") or "?") + ")"


def _params_summary(node):
    """抽节点关键参数（给 LLM 判断用，不抽全量）。"""
    p = node.get("parameters", {}) or {}
    keys = ("url", "model", "operation", "resource", "promptType", "prompt",
            "jsCode", "conditions", "batchSize", "keepOnlySet", "assignments",
            "mode", "method")
    out = {}
    for k in keys:
        if k in p:
            v = p[k]
            if isinstance(v, str) and len(v) > 80:
                v = v[:80] + "…"
            out[k] = v
    return out


def parse_workflow(wf):
    """n8n workflow dict → WorkflowIR dict。"""
    nodes = wf.get("nodes", []) or []
    ir_nodes = []
    cats = Counter()
    creds_all = []
    warnings = []
    subwf = 0

    for n in nodes:
        cat = classify(n)
        cats[cat] += 1
        cred = list((n.get("credentials") or {}).keys())
        creds_all.extend(cred)
        if cat.startswith("?"):
            warnings.append(f"未归类节点: {n.get('name')} ({n.get('type')})")
        if "executeworkflow" in (n.get("type") or "").lower():
            subwf += 1
            warnings.append(f"子工作流调用: {n.get('name')}（需递归解析）")
        ir_nodes.append({
            "id": n.get("id"),
            "name": n.get("name"),
            "type": n.get("type"),
            "category": cat,
            "has_credentials": bool(cred),
            "credentials": cred,
            "params_summary": _params_summary(n),
            "disabled": bool(n.get("disabled", False)),
        })

    # connections 扁平化：{源: main[端口][分支]→{node}} → [{from,to}]
    conns = wf.get("connections", {}) or {}
    edges = []
    for src, body in conns.items():
        for port in body.get("main", []) or []:
            if isinstance(port, list):
                for link in port:
                    if isinstance(link, dict) and link.get("node"):
                        edges.append({"from": src, "to": link["node"]})

    raw = json.dumps(wf, ensure_ascii=False)
    expr_count = raw.count("={{")
    if expr_count:
        warnings.append(f"含 {expr_count} 处 n8n 表达式 ={{}}（需运行时/样例数据解析）")

    entry = [n["name"] for n in ir_nodes if n["category"] == "1_触发器"]

    return {
        "workflow_name": wf.get("name"),
        "active": wf.get("active"),
        "node_count": len(nodes),
        "nodes": ir_nodes,
        "edges": edges,
        "category_distribution": dict(sorted(cats.items())),
        "credentials_referenced": sorted(set(creds_all)),
        "subworkflow_count": subwf,
        "expression_count": expr_count,
        "entry_nodes": entry,
        "warnings": warnings,
    }


def _print_summary(ir):
    print("=" * 64)
    print(f"workflow: {ir['workflow_name']}")
    print(f"节点数: {ir['node_count']}  | active: {ir['active']}")
    print(f"入口(触发器): {ir['entry_nodes'] or '无'}")
    print(f"子工作流: {ir['subworkflow_count']}  | 表达式: {ir['expression_count']}")
    print(f"凭证引用: {ir['credentials_referenced'] or '无'}")
    print("-" * 64)
    print("分类分布:")
    for k, v in ir["category_distribution"].items():
        print(f"  {k}: {v}")
    print("-" * 64)
    print(f"warnings ({len(ir['warnings'])}):")
    for w in ir["warnings"]:
        print(f"  ⚠ {w}")
    print("=" * 64)


def main():
    ap = argparse.ArgumentParser(description="n8n workflow → WorkflowIR")
    ap.add_argument("workflow", help="n8n workflow JSON 路径")
    ap.add_argument("--output", "-o", help="把完整 IR 写到该文件")
    ap.add_argument("--quiet", "-q", action="store_true", help="只输出 IR JSON，不打印摘要")
    args = ap.parse_args()

    try:
        with open(args.workflow, encoding="utf-8") as f:
            wf = json.load(f)
    except Exception as e:
        print(f"[解析失败] {e}", file=sys.stderr)
        sys.exit(1)

    ir = parse_workflow(wf)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(ir, f, ensure_ascii=False, indent=2)

    if args.quiet:
        print(json.dumps(ir, ensure_ascii=False, indent=2))
    else:
        _print_summary(ir)
        if args.output:
            print(f"完整 IR 已写入: {args.output}")


if __name__ == "__main__":
    main()
