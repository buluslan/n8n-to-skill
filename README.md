<div align="center">
    
# n8n-to-skill 🔄

**把任意 n8n 工作流，目标对等地重写成实现同业务目标的 Agent Skill **

**想了解更多最新 AI 行业动态，AI+电商/广告的行业实践方法，人与 AI 如何协作共生的思考，请关注公众号：【新西楼.AI】**

![新西楼公众号](https://github.com/user-attachments/assets/d8f068d9-c4f8-46c7-914c-fbcab5d52f2a)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-black.svg)]()
[![n8n](https://img.shields.io/badge/n8n-workflow-FF6D5A.svg)](https://n8n.io)
[![Agent Skill](https://img.shields.io/badge/Agent-Skill-7C3AED.svg)]()

**目标对等重写 | 不调用原 workflow | 符合 skill-creator 规范 | 凭证零泄漏**

**Created By buluslan@新西楼.AI**

</div>

---

## 项目简介

n8n-to-skill 是一个 Agent 元 Skill（meta-skill）：吃进一个 n8n 工作流导出的 JSON，理解它**在干什么**，产出一个能独立达成同业务目标、符合 skill-creator 规范的 Agent Skill 目录。

**与"让 Skill 调用 n8n API"的封装方案不同**——n8n-to-skill 做的是**目标对等重写**：产出的 Skill 用 LLM + 脚本 + 工具以原生方式重新实现业务逻辑，是 Agent 能直接调用的独立能力。

**适用场景**：你有大量 n8n 工作流沉淀，想把它们变成 Agent 可直接调用的原生 Skill。

> English: [README_EN.md](README_EN.md)

---

## 核心理念：目标对等（Goal Parity）

对齐的是**业务目标和输入输出约定**，不是节点结构：

- **输入对齐**：新 Skill 的触发与原 workflow 触发器语义等价
- **输出对齐**：新 Skill 跑完得到与原 workflow 同等业务价值的结果
- **内部实现自由**：n8n 用 N 个节点拼的，Skill 可以用 LLM + 脚本以更简单的方式等价实现

**一句话原则：读懂 workflow 在干什么，不翻译它怎么干。**

> 例：一个评论分析 workflow 用 8 个节点伺候 Google Sheets（读/写/建表/改列宽）。目标对等重写成"本地 CSV"后，这 8 个节点收敛成 2-3 个文件操作——业务目标（存取评论和报告）不变，实现大幅简化。

---

## 核心特性

| 特性 | 说明 |
|------|------|
| 🎯 目标对等重写 | 理解业务目标后用 Agent 原生能力重新实现，不调用原 workflow |
| 📋 节点行为分类 | 把 n8n 节点按业务贡献分类（触发/AI/数据转换/存储协作等），非逐节点翻译 |
| 🔄 5 步转换流程 | Parse 解析 → Understand 理解 → Ask 反问 → Plan&Build 构建 → Verify 验收 |
| ✅ 目标对等验收 | 同输入双跑比对，业务结果对等才算转换成功 |
| 🔒 凭证零泄漏 | 自动剥离原 workflow 凭证，统一走 `.env` 占位 |
| 🧰 复用 skill-creator | 产物完全符合 skill-creator 规范，可过 `quick_validate` |

---

## 快速开始

### 前置要求

- 任意支持 Skill 的 AI Agent（Claude Code / OpenClaw / Cursor / Windsurf 等均可）
- 一个 n8n 工作流导出的 JSON 文件

### 安装

把 `n8n-to-skill` 复制到你的 Agent 的 skills 目录（以 Claude Code 为例）：

```bash
git clone https://github.com/buluslan/n8n-to-skill.git
cp -r n8n-to-skill ~/.claude/skills/
```

### 使用

在你的 Agent 里，描述你的需求：

```
把这个 n8n 工作流转成 skill：/path/to/your-workflow.json
```

或：

```
分析这个 n8n workflow 并生成 skill
```

Agent 会自动触发 n8n-to-skill，走 5 步流程产出合规 Skill 目录。

---

## 项目结构

```
n8n-to-skill/
├── SKILL.md                    # Skill 入口（路由 + 核心理念 + 5 步流程）
├── references/                 # 按需加载的规则文档
│   ├── node-mapping.md         # 节点行为分类 + 等价实现判断骨架
│   ├── workflow-anatomy.md     # n8n JSON 结构 / connections / 表达式
│   ├── goal-parity-design.md   # 目标对等设计方法论（灵魂文档）
│   ├── step-spec.md            # 步骤规格表 + IO 约定模板 + 反问清单
│   ├── credential-safety.md    # 凭证安全硬约束
│   └── output-template.md      # 产物 Skill 的设计说明
├── scripts/
│   ├── parse_workflow.py       # n8n JSON → WorkflowIR（确定性解析）
│   └── check_skill.py          # 关键段落软校验（反"文档壳"）
├── assets/                     # 模板（skill-template / io-contract / env.example）
├── evals/                      # 触发用例（5 正 / 5 负 / 3 边界）
└── examples/
    ├── example-input.json      # 示例输入：亚马逊评论分析 workflow
    └── example-output/         # 转换产物示例：amazon-review-analyzer
```

---

## 工作原理（5 步流程）

```
n8n workflow JSON
    │
    ▼  ① Parse（脚本确定性解析）
WorkflowIR（节点 / 连接 / 凭证 / 表达式）
    │
    ▼  ② Understand（LLM 提炼业务目标 + IO 约定 + 等价实现方案）
业务目标 + IO 约定表 + 节点贡献图
    │
    ▼  ③ Ask（反问关键决策：本地化 / 凭证 / 触发器 / 验收标的）
用户决策记录
    │
    ▼  ④ Plan & Build（先出方案过目，确认后生成 Skill 目录）
合规 Skill 目录草稿
    │
    ▼  ⑤ Verify（硬校验 + 软校验 + 目标对等双跑比对）
转换成功 / warnings 记录
```

---

## 示例：评论分析 workflow 转换

仓库自带的示例（`examples/`）演示了一次完整转换：

- **输入**：亚马逊商品评论 AI 深度分析 workflow（18 节点，含 Gemini 打标 + Google Sheets 读写）
- **产物**：`amazon-review-analyzer` Skill（本地 CSV 版）
- **收敛**：原始 18 节点 → 4 个核心能力（读 CSV / 22 维打标 / 统计 / 6 章洞察）
- **效果**：Gemini API key 和 Google Sheets OAuth 凭证全部消化（改用 Claude 原生 + 本地 CSV），Skill 零凭证依赖

---

## 与"逐节点翻译"的区别

n8n-to-skill 不是把 n8n 节点 1:1 翻译成 Skill 步骤，而是理解业务目标后用 Agent 原生方式重新实现：

| 维度 | 逐节点翻译 | n8n-to-skill（目标对等重写） |
|------|-----------|------------------------------|
| 对齐对象 | 节点结构（1:1 映射） | 业务目标（N 节点 → M 能力，M ≪ N） |
| 产物形态 | 臃肿僵硬，照搬 n8n 概念 | 原生简洁，Agent 友好 |
| 凭证处理 | 照搬原 workflow 依赖 | 自动剥离，零泄漏 |
| 验收标准 | 结构相似 | 业务结果对等（同输入双跑比对） |

---

## 许可证

[MIT License](LICENSE)

## 联系方式

**bulus lan**

- **公众号**：新西楼.AI — AI+电商/广告行业实践，人与 AI 协作思考
- **GitHub Issues**：https://github.com/buluslan/n8n-to-skill/issues

---

如果这个项目对您有帮助，请给一个 ⭐️

[![GitHub Stars](https://img.shields.io/github/stars/buluslan/n8n-to-skill?style=social)](https://github.com/buluslan/n8n-to-skill/stargazers)
