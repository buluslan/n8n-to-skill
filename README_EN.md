<div align="center">

# n8n-to-skill 🔄

**Rewrite any n8n workflow into an Agent Skill that achieves the same business goal.**

**For the latest AI industry insights, AI + e-commerce/advertising practices, and thoughts on human-AI collaboration, follow 【新西楼.AI】**

![XinxiLou.AI WeChat](https://github.com/user-attachments/assets/d8f068d9-c4f8-46c7-914c-fbcab5d52f2a)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-black.svg)]()
[![n8n](https://img.shields.io/badge/n8n-workflow-FF6D5A.svg)](https://n8n.io)
[![Agent Skill](https://img.shields.io/badge/Agent-Skill-7C3AED.svg)]()

**Goal-Parity Rewrite | No Calls to Original Workflow | skill-creator Compliant | Zero Credential Leakage**

**Created By bulus lan**

</div>

> 中文文档：[README.md](README.md)

---

## Overview

n8n-to-skill is an Agent meta-skill: feed it an n8n workflow JSON, it understands **what the workflow does**, and produces a self-contained agent Skill directory that achieves the same business goal and complies with the skill-creator spec.

**Unlike "wrapper" approaches that have the Skill call the n8n API**, n8n-to-skill performs a **goal-parity rewrite**: the output Skill reimplements the business logic natively with LLM + scripts + tools, as a standalone capability agents can invoke directly.

**Use case**: You have a library of n8n workflows and want to turn them into native Skills that AI agents can invoke directly.

---

## Core Idea: Goal Parity

What's aligned is the **business goal and the I/O contract**, not the node structure:

- **Input alignment**: the new Skill's trigger is semantically equivalent to the original workflow's trigger
- **Output alignment**: the new Skill delivers the same business value as the original workflow
- **Implementation freedom**: what n8n builds with N nodes, the Skill can reimplement more simply with LLM + scripts

**One-liner: understand what the workflow does — don't translate how it does it.**

> Example: a review-analysis workflow uses 8 nodes to manage Google Sheets (read / write / create sheet / resize columns). After a goal-parity rewrite to "local CSV", those 8 nodes collapse into 2-3 file operations — the business goal (store reviews and reports) is unchanged, the implementation far simpler.

---

## Key Features

| Feature | Description |
|---------|-------------|
| 🎯 Goal-Parity Rewrite | Reimplement with agent-native capabilities after understanding the goal; no calls to the original workflow |
| 📋 Node Behavior Taxonomy | Classify n8n nodes by business contribution (trigger / AI / data-transform / storage, etc.), not a 1:1 translation |
| 🔄 5-Step Pipeline | Parse → Understand → Ask → Plan & Build → Verify |
| ✅ Goal-Parity Verification | Run original workflow and new Skill on the same input; pass only when business results are equivalent |
| 🔒 Zero Credential Leakage | Strip original workflow credentials; everything goes through `.env` placeholders |
| 🧰 skill-creator Compliant | Output fully complies with skill-creator spec; passes `quick_validate` |

---

## Quick Start

### Prerequisites

- Any Skill-compatible AI agent (Claude Code / OpenClaw / Cursor / Windsurf, etc.)
- An n8n workflow exported as JSON

### Install

Copy `n8n-to-skill` into your agent's skills directory (Claude Code example):

```bash
git clone https://github.com/buluslan/n8n-to-skill.git
cp -r n8n-to-skill ~/.claude/skills/
```

### Usage

In your agent, describe what you want:

```
Convert this n8n workflow into a skill: /path/to/your-workflow.json
```

or:

```
Analyze this n8n workflow and generate a skill
```

The agent auto-triggers n8n-to-skill and runs the 5-step pipeline to produce a compliant Skill.

---

## Project Structure

```
n8n-to-skill/
├── SKILL.md                    # Entry point (routing + core idea + 5-step pipeline)
├── references/                 # Lazy-loaded rule docs
│   ├── node-mapping.md         # Node behavior taxonomy + equivalence design
│   ├── workflow-anatomy.md     # n8n JSON structure / connections / expressions
│   ├── goal-parity-design.md   # Goal-parity design methodology (the soul doc)
│   ├── step-spec.md            # Step spec table + I/O contract template + question list
│   ├── credential-safety.md    # Credential safety hard rules
│   └── output-template.md      # Output Skill design guide
├── scripts/
│   ├── parse_workflow.py       # n8n JSON → WorkflowIR (deterministic)
│   └── check_skill.py          # Required-sections soft check (anti "doc shell")
├── assets/                     # Templates (skill-template / io-contract / env.example)
├── evals/                      # Trigger cases (5 positive / 5 negative / 3 edge)
└── examples/
    ├── example-input.json      # Sample input: Amazon review-analysis workflow
    └── example-output/         # Sample output: amazon-review-analyzer
```

---

## How It Works (5-Step Pipeline)

```
n8n workflow JSON
    │
    ▼  ① Parse (deterministic script)
WorkflowIR (nodes / connections / credentials / expressions)
    │
    ▼  ② Understand (LLM: distill goal + I/O contract + equivalence plan)
Business goal + I/O contract + node contribution map
    │
    ▼  ③ Ask (confirm key decisions: localization / credentials / trigger / acceptance)
User decisions
    │
    ▼  ④ Plan & Build (show plan first; generate Skill dir after approval)
Compliant Skill draft
    │
    ▼  ⑤ Verify (hard check + soft check + goal-parity dual-run)
Success / warnings
```

---

## Example: Review-Analysis Workflow

The repo's `examples/` shows a complete conversion:

- **Input**: Amazon review deep-analysis workflow (18 nodes, Gemini tagging + Google Sheets I/O)
- **Output**: `amazon-review-analyzer` Skill (local-CSV version)
- **Collapse**: 18 nodes → 4 core capabilities (read CSV / 22-dim tagging / stats / 6-chapter insights)
- **Effect**: Gemini API key and Google Sheets OAuth credentials fully dissolved (Claude-native + local CSV); the Skill has zero credential dependencies

---

## Node-by-Node Translation vs. n8n-to-skill

n8n-to-skill does not translate n8n nodes 1:1 into Skill steps. It understands the business goal and reimplements natively:

| Aspect | Node-by-node translation | n8n-to-skill (goal-parity rewrite) |
|--------|--------------------------|------------------------------------|
| Aligns with | Node structure (1:1 mapping) | Business goal (N nodes → M capabilities, M ≪ N) |
| Output | Bloated, rigid, copies n8n concepts | Lean, native, agent-friendly |
| Credentials | Copies original dependencies | Auto-stripped, zero leakage |
| Acceptance | Structural similarity | Business-result parity (dual-run on same input) |

---

## License

[MIT License](LICENSE)

## Contact

**bulus lan**

- **WeChat Official Account**: 新西楼.AI — AI + e-commerce/advertising practices, human-AI collaboration
- **GitHub Issues**: https://github.com/buluslan/n8n-to-skill/issues

---

If this project helps you, please give it a ⭐️

[![GitHub Stars](https://img.shields.io/github/stars/buluslan/n8n-to-skill?style=social)](https://github.com/buluslan/n8n-to-skill/stargazers)
