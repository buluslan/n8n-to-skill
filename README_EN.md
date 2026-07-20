# n8n-to-skill 🔄

**Rewrite any n8n workflow into a Claude Code Skill that achieves the same business goal — n8n can be retired after conversion.**

**For the latest AI industry insights, AI + e-commerce/advertising practices, and thoughts on human-AI collaboration, follow 【新西楼 / XinxiLou.AI】**

![XinxiLou WeChat](https://github.com/user-attachments/assets/d8f068d9-c4f8-46c7-914c-fbcab5d52f2a)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-black.svg)]()
[![n8n](https://img.shields.io/badge/n8n-workflow-FF6D5A.svg)](https://n8n.io)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-7C3AED.svg)](https://claude.com/claude-code)

**Goal-Parity Rewrite | No Calls to Original Workflow | skill-creator Compliant | Zero Credential Leakage**

**Created By Buluu@新西楼**

> 中文文档：[README.md](README.md)

---

## Overview

n8n-to-skill is a Claude Code meta-skill: feed it an n8n workflow JSON, it understands **what the workflow does**, and produces a self-contained Skill directory that achieves the same business goal and complies with the skill-creator spec.

**Unlike "wrapper" approaches that have the Skill call the n8n API**, n8n-to-skill performs a **goal-parity rewrite**: the output Skill reimplements the business logic natively with LLM + scripts + tools, so n8n can be fully retired afterwards.

**Use case**: You have a library of n8n workflows and want to turn them into Skills that AI agents can invoke directly — without depending on a running n8n instance.

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
| 🎯 Goal-Parity Rewrite | Reimplement after understanding the goal; n8n can retire; no calls to the original workflow |
| 📋 Node Behavior Taxonomy | Classify n8n nodes by business contribution (trigger / AI / data-transform / storage, etc.), not a 1:1 translation |
| 🔄 5-Step Pipeline | Parse → Understand → Ask → Plan & Build → Verify |
| ✅ Goal-Parity Verification | Run original workflow and new Skill on the same input; pass only when business results are equivalent |
| 🔒 Zero Credential Leakage | Strip original workflow credentials; everything goes through `.env` placeholders |
| 🧰 skill-creator Compliant | Output fully complies with skill-creator spec; passes `quick_validate` |

---

## Quick Start

### Prerequisites

- [Claude Code](https://claude.com/claude-code) installed
- An n8n workflow exported as JSON

### Install

Copy `n8n-to-skill` into Claude Code's skills directory:

```bash
git clone https://github.com/buluslan/n8n-to-skill.git
cp -r n8n-to-skill ~/.claude/skills/
```

### Usage

In Claude Code, describe what you want:

```
Convert this n8n workflow into a skill: /path/to/your-workflow.json
```

or:

```
Analyze this n8n workflow and generate a skill
```

Claude Code auto-triggers n8n-to-skill and runs the 5-step pipeline to produce a compliant Skill.

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

## Wrapper Approach vs. n8n-to-skill

| Aspect | Wrapper (call n8n API) | n8n-to-skill (goal-parity rewrite) |
|--------|------------------------|------------------------------------|
| n8n dependency | Must stay running | Can be retired |
| Implementation | Skill calls n8n REST API | Skill uses LLM/scripts natively |
| Behavior drift | None (same code) | Guarded by goal-parity verification |
| Best for | High-audit, high-frequency cases | Reusable flows with clear business goals |

---

## License

[MIT License](LICENSE)

## Contact

**Buluu@新西楼 (XinxiLou.AI)**

- **WeChat Official Account**: 新西楼 — AI + e-commerce/advertising practices, human-AI collaboration
- **GitHub Issues**: https://github.com/buluslan/n8n-to-skill/issues

---

If this project helps you, please give it a ⭐️

[![GitHub Stars](https://img.shields.io/github/stars/buluslan/n8n-to-skill?style=social)](https://github.com/buluslan/n8n-to-skill/stargazers)
