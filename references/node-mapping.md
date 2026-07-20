# 节点 → 目标贡献分析表

## 核心认知（读懂这一段再往下看）

这张表是「节点 → 它为业务目标贡献什么」的分析，**不是**「节点 → skill 段落」的翻译映射。

这是本 skill 与逐节点翻译派的根本区别：
- 逐节点翻译派：n8n 有 N 个节点 → skill 有 N 个段落（机械 1:1，产物臃肿）
- 目标贡献派：读懂每个节点贡献什么能力 → 决定新 skill 要复刻哪些能力、用什么方式复刻（N → M，M 通常远小于 N）

分析两步走：
1. 先问「这个节点为业务目标贡献了什么能力？」（不是「这个节点在 n8n 里叫什么 type」）
2. 再问「新 skill 要不要复刻这个贡献？如果要，用 Claude/脚本/集成的哪种方式实现最自然？」

节点 type 的行为分类规则见 `scripts/parse_workflow.py` 的 `classify()`，本文件只负责**等价实现的判断骨架**。

---

## 节点行为分类详表

> ⚠️ 下表【落点】列里的路径（如 `references/xxx`、`scripts/`）均指**产物 skill 的目录**（转换时按需创建），不是本 skill（n8n-to-skill）自己的目录。

### 1_触发器
| 典型 n8n 节点 type | 它为业务目标贡献什么 | 新 skill 中的等价实现思路 | 落点 |
|---|---|---|---|
| formTrigger / webhook / manualTrigger / scheduleTrigger / cronTrigger | 定义 workflow 的输入约定：何时触发、接受什么形态的输入 | 转成 skill 的触发词与输入参数。表单→用户输入；schedule→定时任务说明；webhook→列出被谁调用、payload 形态 | SKILL.md frontmatter description（触发词）+ 正文「输入约定」段 |

### 2_生成式AI
| 典型 n8n 节点 type | 它为业务目标贡献什么 | 新 skill 中的等价实现思路 | 落点 |
|---|---|---|---|
| `@n8n/n8n-nodes-langchain.*` / googleGenerativeAI / openAi / agent | 产出内容或决策的核心能力（分类、生成、总结、判断） | 用 Claude/Codex 原生能力顶替。提示词从原节点参数提取，重写成 skill 的指令或独立 prompt 文件 | `references/prompts/` + SKILL 正文「能力定义」段 |

**案例（评论 workflow 的 2 个生成式 AI 节点）**：
- Gemini 打标节点（给每条评论打标签）：贡献=分类决策能力 → skill 等价实现=写一个评论打标 prompt 文件，让 Claude 在循环中逐条调用
- Gemini 洞察节点（生成洞察报告）：贡献=长文本生成能力 → skill 等价实现=写一个洞察生成 prompt 文件，喂入标签统计结果

### 3_爬虫 HTTP 无认证
| 典型 n8n 节点 type | 它为业务目标贡献什么 | 新 skill 中的等价实现思路 | 落点 |
|---|---|---|---|
| httpRequest（无凭证、调公开 URL） | 从公开网络抓取数据 | 用 WebFetch / curl / Python requests 实现。URL 列表与解析逻辑迁移到脚本 | `scripts/` + `references/integration-notes.md` |

### 4_外部付费数据
| 典型 n8n 节点 type | 它为业务目标贡献什么 | 新 skill 中的等价实现思路 | 落点 |
|---|---|---|---|
| httpRequest（带凭证调 dataforseo / keepa / exa 等付费数据 API） | 接入付费数据源 | 优先查找现成 MCP server 或 skill 复用；否则封装成独立调用脚本，凭证从 env 读取。保留或替换问用户 | 产物 skill 的 `scripts/`（每 API 一文件） |

### 5_存储协作
| 典型 n8n 节点 type | 它为业务目标贡献什么 | 新 skill 中的等价实现思路 | 落点 |
|---|---|---|---|
| googleSheets / notion / gmail / slack / httpRequest（调 googleapis / notion / gmail / slack API） | 持久化、协作、通知 | 本地化（写文件）或保留集成（MCP / skill），由用户决定 | `references/integration-notes.md`（记录用户决策）+ SKILL 正文「集成」段 |

**案例（评论 workflow 的 8 个存储协作节点 = 4 个 googleSheets + 4 个 httpRequest 调 Google Sheets/Drive API）**：
- 读评论表 / 读取所有已打标数据 / 写标签表 / 写洞察表（4 个 googleSheets）：贡献=数据持久化 → 本地化等价=读 CSV / 写 CSV / 生成报告文件
- 取表格元数据 / 初始化标签列头 / 创建洞察报告表 / 扩展列宽至 30 列（4 个 httpRequest 调 Sheets/Drive API）：贡献=Sheets 表结构管理（平台特有概念）→ 本地文件无此概念，目标对等直接消化掉，新 skill 不需要任何对应实现

### 6_数据转换
| 典型 n8n 节点 type | 它为业务目标贡献什么 | 新 skill 中的等价实现思路 | 落点 |
|---|---|---|---|
| code (JS/Python) / set / editFields / aggregate / splitOut | 数据清洗、字段映射、聚合、拆分、格式转换 | 抓业务意图，用 Python 脚本重写。原 code 的业务意图 > 具体语法 | `scripts/` + `references/logic-notes.md`（记录每段转换的真实意图） |

**案例（评论 workflow 的 6 个数据转换节点：5 code + 1 set）**：
- 不需要逐字翻译每个 code 节点。读懂每段在做什么转换（例如「把 Gemini 输出的 JSON 解析成表行」），在 `scripts/` 用 Python 实现等价逻辑
- 关键是抓「业务意图」：原 code 可能处理 n8n item 结构（`json` / `binary` / `pairedItem`），新 skill 完全不需要这些 n8n 私有概念，只实现真正的数据变换

### 7_控制流
| 典型 n8n 节点 type | 它为业务目标贡献什么 | 新 skill 中的等价实现思路 | 落点 |
|---|---|---|---|
| splitInBatches / if / merge / loop / switch | 批处理、分支、合并、循环 | 用 Python 脚本的 for/if 实现，或用 skill 工作流的多步骤表达。splitInBatches → `for chunk in batches` | `scripts/` + SKILL 正文「流程」段 |

**案例（评论 workflow 的 1 个 splitInBatches 节点）**：贡献=循环逐条处理 → skill 等价实现=Python 脚本的 for 循环，每条评论调用一次 Claude 打标。

### 8_人工审批
| 典型 n8n 节点 type | 它为业务目标贡献什么 | 新 skill 中的等价实现思路 | 落点 |
|---|---|---|---|
| wait / form（审批表单） | 在关键节点暂停等待人工决策 | 用 skill 的「向用户提问」能力实现，或拆成两阶段 skill | SKILL 正文「人工介入点」段 |

### 9_子工作流
| 典型 n8n 节点 type | 它为业务目标贡献什么 | 新 skill 中的等价实现思路 | 落点 |
|---|---|---|---|
| executeWorkflow | 复用其他 workflow 的能力 | 提取被调用 workflow 的核心能力，作为独立 skill 或脚本函数复用 | `references/sub-skill-map.md`（如有）+ SKILL 正文「依赖」段 |

### 10_错误处理
| 典型 n8n 节点 type | 它为业务目标贡献什么 | 新 skill 中的等价实现思路 | 落点 |
|---|---|---|---|
| errorTrigger / errorWorkflows | 失败时的兜底、重试、通知 | 用脚本的 try/except + 重试逻辑 + 失败时的用户提示实现 | `scripts/` + SKILL 正文「异常处理」段 |

### 11_文档
| 典型 n8n 节点 type | 它为业务目标贡献什么 | 新 skill 中的等价实现思路 | 落点 |
|---|---|---|---|
| noOp / stickyNote（注解） | workflow 内的注释、说明、占位 | 转成 skill 文档的设计上下文记录，作为新 skill 的背景信息 | `references/design-context.md` |

---

## unknown 类兜底

遇到 `classify()` 无法归类的节点，按四步处理：

1. 在 WorkflowIR 的 `nodes[]` 里标记 `"category": "?_未归类", "status": "needs_review"`
2. 完整保留该节点的原始 JSON 进 `references/raw-nodes.md`（不省略任何参数）
3. 在 `warnings.json` 追加一条：节点名 + type + 无法归类原因
4. 在 Understand 阶段结尾的总结中显式列出 unknown 节点，问用户：「这个节点对业务目标贡献是什么？应该归到哪一类？」

在静默中跳过 unknown 节点是高风险动作——它的业务贡献可能恰好是 workflow 的关键环节。

---

## 关键认知收尾

**N 个节点可收敛成 1 个能力。**

这是目标贡献分析最重要的产出。机械逐节点翻译会得到 N 个段落的臃肿 skill；目标贡献分析能识别「这 N 个节点其实在贡献同一个能力」，从而收敛成 M 个能力（M 通常远小于 N）。

最典型的例子：评论 workflow 的 8 个存储协作节点（4 googleSheets + 4 httpRequest），业务目标上只是「读评论 + 写结果」一个能力，新 skill 用 2-3 个文件操作就等价实现。

收敛原则：
- 同类贡献（都是数据读取、都是数据写入、都是 AI 决策）合并成一个能力
- n8n 特有的胶水节点（表结构管理、item 转换、字段重命名）通常没有独立业务贡献，被主能力消化掉
- 收敛后的能力清单 = 新 skill 的能力骨架，直接对应 SKILL.md 的「能力定义」段
