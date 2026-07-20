---
name: n8n-to-skill
description: 把已经做好的 n8n 工作流（导出的 JSON / workflow URL / 模板）理解后，重新实现成一个能独立达成同业务目标、符合 skill-creator 规范的 Claude Code skill（转换后 n8n 可下线，不依赖调用原 workflow）。当用户说"把这个 n8n 工作流重写成 skill / 把这个 flow 抽象成可复用能力 / 分析这个 n8n workflow 并生成 skill / 把 n8n 模板变成 Claude skill / n8n 转 skill"时，必须使用本 skill。不要用于"从零写一个 n8n 工作流"或"调试 n8n 节点报错"或"让 skill 调用 n8n"——那是 n8n 构建类 skill 或封装方案的职责。
allowed-tools: Read, Glob, Grep, Bash(python3:*), Bash(python:*), Write, Edit
license: MIT
---

# n8n-to-skill

> 把任意 n8n 工作流，**目标对等**地重写成实现同业务目标的 Claude Code skill。转换后 n8n 可下线。

## 0. 一句话定位

吃进一个 n8n workflow JSON，理解它**在干什么（业务目标）**，产出一个能独立达成同目标、符合 skill-creator 规范的 skill 目录。不是逐节点翻译，不是调用原 workflow。

## 1. ★核心理念：目标对等转换（本 skill 的灵魂）

对齐的是**业务目标和 IO 约定**，不是节点结构：

- **输入对齐**：新 skill 的触发与原 workflow 触发器语义等价。
- **输出对齐**：新 skill 跑完得到与原 workflow 同等业务价值的结果。
- **内部实现自由**：n8n 用节点拼的，skill 用 LLM / 脚本 / 工具以**原生最优方式**重新实现。n8n 的 N 个节点可能收敛成 skill 里的 1 个能力——只要结果对等。

**一句话原则：读懂 workflow 在干什么，不翻译它是怎么干的。**

> 例：评论分析 workflow 用 8 个节点伺候 Google Sheets（读/写/建表/改列宽/取元数据）。目标对等重写成"本地 CSV"实现时，这 8 个节点收敛成 2-3 个文件操作——因为业务目标是"存取评论和报告"，本地文件用更简单的方式等价达成。详见 `references/goal-parity-design.md`。

## 2. 能力分级

- **core（每次转换必做）**：5 步流程、提炼业务目标 + IO 约定、生成的 SKILL.md 合规、目标对等验收、warnings 记录。
- **conditional（命中才加载对应 reference）**：
  - 涉及凭证 / HTTP Auth / 外部付费 API → 读 `references/credential-safety.md`
  - 涉及 Code 节点 JS / n8n 表达式 `={{}}` → 读 `references/workflow-anatomy.md` 的表达式段
  - 业务目标难提炼 / 要设计等价实现 → 读 `references/goal-parity-design.md`

> 不得因 reference 目录下存在某文件就全量加载；也不得因当前任务简单就跳过命中条件时该读的文件。

## 3. 按需读取表（导航）

| 当前阶段 | 读哪个 reference | 何时读 |
|---|---|---|
| Parse 解析 | `references/workflow-anatomy.md` | 跑 `parse_workflow.py` 前后，要理解 n8n JSON 结构 |
| Understand 理解 | `references/node-mapping.md` + `references/goal-parity-design.md` | 归类节点 + 提炼业务目标 + 设计等价实现时 |
| Ask 反问 | `references/step-spec.md` | 把决策亮给用户、写 IO 约定表时 |
| Plan & Build 构建 | `references/output-template.md` + `references/credential-safety.md` | 生成新 skill 的 SKILL.md + 处理凭证时 |
| Verify 验收 | `references/goal-parity-design.md`（验收节） | 做目标对等比对时 |

## 4. 工作流（五步，每步必有可观察输出，禁止跳步）

| 步骤 | 输入 | 可执行动作 | 可观察输出 | 转移条件 |
|---|---|---|---|---|
| **1 Parse** | n8n JSON / URL / 模板 | 跑 `scripts/parse_workflow.py` 提取 nodes/connections/parameters/credentials，构建 WorkflowIR | IR 摘要：节点数 / 类型分布 / 凭证引用 / 子工作流标记 | IR 合法（有 nodes+connections） |
| **2 Understand** | WorkflowIR | ① 用 `node-mapping.md` 的行为分类归每个节点；② 提炼**业务目标一句话**；③ 写**IO 约定**（触发语义/入口参数/产出形态/质量标准）；④ 设计每个业务能力的等价实现 | 业务目标陈述 + IO 约定表 + 节点目标贡献图 + 等价实现方案 | 业务目标与 IO 约定都已明确陈述 |
| **3 Ask** | 目标 + 约定 + 方案 | 反问关键决策：①业务目标理解对不对；②凭证怎么提供（.env 占位）；③触发器是否改一次性命令；④存储类节点本地化还是保留集成；⑤原 workflow 是否留作验收标的 | 用户决策记录 | 用户逐项确认或选"用推荐" |
| **4 Plan & Build** | 决策记录 | ①**先输出 skill 目录结构 + 目标重写方案给用户过目，人没点头前不写代码**；②确认后生成 SKILL.md + references + scripts | skill 目录草稿 + 重写方案对照表 | 用户确认方案 |
| **5 Verify** | 草稿 + 原 workflow | ① 复用 skill-creator 的 `quick_validate.py` 硬校验；② 跑 `scripts/check_skill.py` 的 关键段落校验；③ **目标对等验收**：同一组真实输入，原 workflow 和新 skill 各跑一遍，比对业务结果 | 校验报告 + `warnings.json` + 目标对等比对记录 | 全绿 + 目标对等比对通过 |

> 第 4 步"出方案前不动手写代码"、第 3 步"反问"、第 5 步"目标对等验收"是三个闸门，缺一不可。

## 5. 硬停止（Hard Stops）

出现以下情况必须停下、拒绝或反问，不得继续生成：

1. 用户要求"让 skill 调用原 n8n workflow"——违背目标对等，明确拒绝并说明本 skill 只做重写。
2. workflow 含表达式 `={{}}` 但用户没给数据样例——停下要样例，不强行静态求值。
3. Code 节点引用了未声明的环境变量 / 凭证——停下问清楚，不臆造。
4. 用户把真实 API key / credentials 明文塞进来——拒绝接收明文，改走 `.env.example` 占位。
5. 业务目标无法提炼（反问后仍含糊）——不强行生成，交付"待确认"草稿 + warnings。
6. 没有真实输入数据却要声称转换成功——目标对等验收是硬门槛，没标的只能交 `draft/` + warnings。

## 6. 优雅降级（永远不卡死）

- 未识别节点 → `unknown` 类 → 标"目标贡献待确认" + 原始 JSON 片段存 `references/raw-nodes.md` + 写 `warnings.json`。
- 凭据 → `.env.example` 占位 + 运行时读环境变量。
- n8n 表达式 → 能翻成等价逻辑就翻，不能就注释要求运行时解析。
- 校验失败 → 重试 1 次 → 再失败写 `draft/`。
- 所有未完全转换点统一进 `warnings.json`（**唯一形式，禁止用 warnings.md**）。禁止隐瞒。

## 7. 验证命令

```bash
# 1. 解析 workflow（Parse 阶段）
python3 scripts/parse_workflow.py examples/example-input.json

# 2. 生成的 skill 的 关键段落校验（反"文档壳"）
python3 scripts/check_skill.py <生成的skill目录>

# 3. 复用 skill-creator 的 frontmatter 硬校验
python3 -c "import sys; sys.path.insert(0, '<skill-creator路径>'); from quick_validate import validate; validate('<生成的skill目录>')"
# 或直接用本机 skill-creator skill 的 quality-checklist
```

三层状态语义：①结构校验绿 = 文件齐 + frontmatter 合规；②关键段落校验绿 = 不是空壳；③**目标对等比对通过 = 真的等价**。三层全过才算转换成功。

## 8. 闭环决策（四选一）

每次转换 / 升级后，明确记录属于哪一种，禁止把聊天总结冒充闭环：
- `writeback`：方案/映射表有可复用改进，写回 reference。
- `proposal`：有想法但未验证，记进待办。
- `none-with-reason`：无改进，注明理由。
- `blocked`：被某硬停止卡住，注明卡点。

## 9. 最终报告（交付时给用户）

中文报告，含：①原 workflow 业务目标一句话；②IO 约定表；③节点目标贡献图（哪类节点→新 skill 的哪个能力）；④重写方案对照表（含被"目标对等"消化掉的节点及理由）；⑤目标对等验收记录；⑥`warnings.json` 摘要；⑦闭环决策。

---

**起步**：拿到 n8n workflow JSON → 跑 `scripts/parse_workflow.py` → 读 `references/node-mapping.md` + `references/goal-parity-design.md` 进入 Understand。
