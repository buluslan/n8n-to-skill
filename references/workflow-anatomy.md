# workflow-anatomy — n8n workflow JSON 结构解析知识

> Parse 阶段读。读完能回答："这份 JSON 里每个字段是什么含义？connections 怎么读出拓扑？表达式 `={{}}` 怎么处理？parameters 为何不能静态穷举？"
>
> **本文件单一职责**：workflow JSON 的**静态结构**知识。不讲节点如何归类（见 `node-mapping.md`）、不讲业务目标如何提炼或等价实现如何设计（见 `goal-parity-design.md`）。

---

## 1. 顶层结构

一个 n8n workflow 导出 JSON 的顶层字段：

| 字段 | 类型 | 是否确定字段 | 作用 |
|---|---|---|---|
| `name` | string | ✅ | workflow 名称，Parse 写进 `workflow_name` |
| `active` | bool | ✅ | 是否处于激活（定时/Webhook 生效）状态 |
| `nodes` | array | ✅ | 全部节点，详见 §2 |
| `connections` | object | ✅ | 边定义，key 是源节点 name，详见 §3 |
| `settings` | object | ⚠️ | `executionOrder`（v0/v1，影响执行序）、`callerPolicy`、`saveManualExecutions` 等。转换时只读 `executionOrder` 判断是否启用 v1 显式序 |
| `versionId` / `id` | string | ⚠️ | n8n 内部 ID。转换时丢弃，新 skill 不依赖 |
| `staticData` | object | ⚠️ | workflow 的持久化键值存储（跨执行保留）。**遇到非空必须停下**：里面存的是原 workflow 的状态（游标、已处理 ID），目标对等重写时要确认业务上是否需要等价状态 |
| `pinData` | object | ⚠️ | 画布调试用的"固定输入"。转换时丢弃 |
| `meta` / `tags` | object/array | ⚠️ | 元信息/标签。转换时丢弃 |

Parse 阶段只把 `name` / `active` / `nodes` / `connections` 抽进 WorkflowIR，其余字段若**非空且非默认值**要进 `warnings`（尤其 `staticData` 非空）。

---

## 2. nodes[] 单节点字段表

每个 `nodes[i]` 的字段：

| 字段 | 类型 | 是否确定字段 | 作用 / 注意点 |
|---|---|---|---|
| `id` | string | ✅ | 节点 UUID。画布引用用，转换时**不保留**（新 skill 用语义名） |
| `name` | string | ✅ | 画布显示名，**唯一**，也是 `connections` 的 key。是人和 LLM 读懂 workflow 的主要线索 |
| `type` | string | ✅ | 节点类型全限定名，如 `n8n-nodes-base.code` / `@n8n/n8n-nodes-langchain.googleGemini`。**分类的唯一依据**（节点分类详表见 `node-mapping.md`，判定规则在 `scripts/parse_workflow.py` 的 `classify()`） |
| `typeVersion` | number | ✅ | 类型版本。同名节点不同版本，parameters schema 会变（如 `googleSheets` v4.5 vs v4.7 的 `columns.mappingMode` 行为差异）。归档老 workflow 时要留意 |
| `parameters` | object | ❌ **动态** | 节点的配置。**schema 由 `type`+`typeVersion` 决定，n8n 无公开 JSON Schema**，字段是黑盒。Parse 原样保留交 LLM，详见 §5 |
| `credentials` | object | ✅ 有则敏感 | 引用的凭证。结构 `{credsKey: {id, name}}`。Parse 抽 key 列表（如 `googleSheetsOAuth2Api`），**id/name 丢弃**（走 `.env.example` 占位，见 `credential-safety.md`） |
| `disabled` | bool | ✅ | 画布禁用标记。disabled 节点在原 workflow 不执行——Parse 保留标记，Understand 阶段决定是否对应跳过 |
| `position` | [x,y] | ⚠️ | 画布坐标。转换时丢弃，**但若需按 position 推断"同列串联顺序"作 fallback**（connections 缺失时才用） |
| `executeOnce` | bool | ⚠️ | 仅在首轮执行。语义关键——常见于 splitInBatches 循环**后**的汇总节点（例如读取全量已处理数据做统计）：表示循环结束后**只读一次**全量数据，不随循环重复 |
| `webhookId` / `formTrigger` 等触发器特有 | 各种 | ⚠️ | 触发器附加字段，按需读 |
| `notes` / `notesInFlow` | string | ⚠️ | 画布注释。有就读（业务线索），不强制保留 |

**Parse 输出每个节点的**：`id` / `name` / `type` / `category`（classify 结果）/ `has_credentials` / `credentials`(key 列表) / `params_summary`（关键字段摘要）/ `disabled`。parameters 原文也保留在 IR 里供 Understand 阶段取用。

---

## 3. connections 对象详解

结构：`connections[源节点name] = { "main": [[{node,type,index}, ...], ...] }`

拆解三层：
- **第 1 层**（key）：源节点的 `name`（**不是 id**）
- **第 2 层**（`main`）：输出类型。绝大多数节点是 `main`；LangChain AI 节点可能额外有 `ai_languageModel` / `ai_tool` / `ai_memory` / `ai_outputParser` / `ai_vectorStore` 等（详见 §3.3）
- **第 3 层**（`main[port]`，数组）：**输出端口**，端口索引有语义（见 §3.1）
- **第 4 层**（`main[port][branch]`，对象）：分支上的具体连边，`{node: 目标节点name, type: "main", index: 目标节点的输入端口}`

### 3.1 多输出端口节点（port 的语义）

| 节点类型 | port=0 | port=1 | port=2..N |
|---|---|---|---|
| 普通节点（Code/Set/HTTP/Sheets 等） | 唯一输出 | — | — |
| `IF` | `true`（条件满足） | `false`（条件不满足） | — |
| `Switch` | rule[0] 命中 | rule[1] 命中 | rule[i] 命中 |
| `Merge` | 合并输出 | — | — |
| **`splitInBatches`** | **`done`**（全部批次跑完） | **`loop`**（每批次执行体） | — |

**最容易看错的是 `splitInBatches`**：它的 port=0 是"循环结束"分支，port=1 是"循环体"分支。和 IF 的 true/false 直觉相反。读 connections 时务必按 `type` 节点类型反查语义，别按端口数字猜。

### 3.2 splitInBatches 的标准回环范式

```
"批处理节点": {                       // type = n8n-nodes-base.splitInBatches
  "main": [
    [ {"node": "汇总节点",   "type":"main","index":0} ],   // port=0 → done：全部批次跑完出循环
    [ {"node": "循环体首节点","type":"main","index":0} ]    // port=1 → loop：每批次执行体入口
  ]
},
"循环体末端节点": {                    // 批内最后一步（写回 / 落库 / 标记等）
  "main": [
    [ {"node": "批处理节点", "type":"main","index":0} ]    // 回环边：末端 → splitInBatches 自身，触发下一批
  ]
}
```

读出来的拓扑：循环体末端节点**回到 splitInBatches 自身**触发下一批（隐式回环，`from==to`）；全部批次结束后从 port=0 进入汇总节点。这是判断"循环体回环 + 完成分支"的通用模式。例如评论分析 workflow 的 `循环处理评论 → Gemini打标 → 解析 → 写回 → 回到循环处理评论` 即此范式（完整推演见 `examples/example-output/amazon-review-analyzer/CASE_STUDY.md`）。

### 3.3 LangChain AI 节点的非 main 连接

`@n8n/n8n-nodes-langchain.*` 系列节点（Agent / Chain / Tool / Memory / OutputParser 等）除了 `main` 主数据流，还会有**组件挂载连接**：

- `ai_languageModel`：挂载 LLM（如 `googleGemini` / `openAi` / `chatOpenAi`）
- `ai_tool`：挂载工具
- `ai_memory`：挂载记忆
- `ai_outputParser`：挂载输出解析器
- `ai_vectorStore` / `ai_embedder`：RAG 场景

**这类连接表达"组合"关系**，不是数据流。例：`Agent` 节点的 `ai_languageModel` 端口连到 `Google Gemini` 节点，意思是"这个 Agent 用 Gemini 作 LLM"——转换时把它当作 Agent 的一个**配置参数**（`model=gemini`），不当作独立能力节点。

Parse 目前只扁平化 `main` 边（见 `parse_workflow.py` 的 edges 抽取循环）；Understand 阶段处理 LangChain workflow 时，**要单独扫 `ai_*` 类型连接**重建"Agent 用了哪些组件"。

---

## 4. n8n 表达式 `={{ }}`

### 4.1 识别

- 语法：字符串字面量以 `=` 开头，整段是 `={{ ... }}` 或嵌在更长字符串里（如 `"前缀 {{ $json.name }} 后缀"`）
- 出现位置：嵌在 `parameters` 的**字符串值**里（`url` / `jsCode` / `prompt` / `jsonBody` 等任意字段）
- 求值时机：**运行时**。静态 JSON 里只能看到模板，看不到值

### 4.2 常见表达式形态

| 形态 | 含义 |
|---|---|
| `{{ $json.field }}` | 当前节点输入项的 `field` 字段 |
| `{{ $('节点名').item.json.字段名 }}` | **跨节点引用**：取名为"节点名"的节点的输出（例如 `{{ $('提取洞察内容').item.json.insightText }}` 取上一步生成的洞察文本） |
| `{{ $json['_rowIndex'] }}` | 当前项的行号（业务字段） |
| `{{ new Date().toLocaleString(...) }}` | 内嵌 JS |
| `{{ JSON.stringify($json.fieldStats, null, 2) }}` | 内嵌 JS 函数 |

### 4.3 转换器处理策略（按顺序）

1. **能翻等价就翻**：表达式映射到的新 skill 实现里，用对应变量/函数替换。例：`{{ $json.name }}` → 新实现里的 `row["name"]`；`{{ $('节点名').item.json.字段名 }}` → 上一步的 Python 变量（例如 `{{ $('提取洞察内容').item.json.insightText }}` → `insight_text`）。
2. **无法静态判定就停下要样例数据**：表达式依赖运行时数据形状（如 `{{ $json[someDynamicKey] }}`），**不要臆造求值结果**。按 SKILL.md 的 Hard Stop #2：停下向用户要一份真实输入样例，再决定等价实现。
3. **JS 内嵌表达式进 warnings**：所有含 `={{` 的字段计入 `expression_count`，逐条进 `warnings.json`，禁止隐瞒。

Parse 阶段对表达式只**计数**（`raw.count("={{")`），**不求值**。求值是 Understand/Build 阶段在拿到样例数据后做的事。

---

## 5. 无官方 JSON Schema 的事实与应对

### 5.1 事实

- n8n `parameters` 字段的 schema 由 `type` + `typeVersion` 在运行时从节点定义文件动态生成，**没有公开的 JSON Schema 文档**
- 同一 `type` 不同 `typeVersion` 的 parameters 字段会变（字段增删、默认值改、嵌套结构调整）
- 第三方/自建节点的 parameters 完全自定义

### 5.2 应对原则

**parameters 是最大不确定源**——Parse 阶段不试图穷举解析，只做两件事：

1. **抽确定字段**（§2 表中 ✅ 的那些）：`id` / `name` / `type` / `typeVersion` / `credentials` / `disabled`。这些字段跨所有节点稳定。
2. **parameters 原样保留 + 关键字段摘要**：`parse_workflow.py` 的 `_params_summary()` 只抽 `url` / `model` / `operation` / `resource` / `promptType` / `prompt` / `jsCode` / `conditions` / `batchSize` / `keepOnlySet` / `assignments` / `mode` / `method` 这几个跨类型常见的线索字段（截断到 80 字符），其余原样留 IR。

**parameters 的深度理解交给 LLM（Understand 阶段）**：LLM 拿到节点 `type` + `parameters` 原文 + `typeVersion`，结合 `node-mapping.md` 的分类判定，逐节点判断业务贡献。脚本不做这件事——脚本做会漂移。

### 5.3 边界情况

| 情况 | 处理 |
|---|---|
| `type` 在 `classify()` 里命中 `?_未归类` | 进 `warnings` + 原始 JSON 存 `references/raw-nodes.md`，Understand 阶段单独看 |
| `parameters` 含 `={{}}` 但用户没给样例 | Hard Stop #2，停下要样例 |
| `credentials` 引用了未在 n8n 注册的类型 | 进 `warnings`，Ask 阶段问用户凭证从哪来 |
| `typeVersion` 很老（如 v1） | 进 `warnings` 提示"老版本节点 parameters 结构可能与现版不同" |

---

## 6. 拓扑读法示范

> 本节演示**怎么从 connections 读出 workflow 拓扑**（workflow-anatomy 的职责）。从同一拓扑**提炼业务目标**的走法见 `goal-parity-design.md`，两处视角不同、不重复。
>
> **完整 workflow 拓扑范例**（含 18 节点框图、边统计、回环边标注）已迁至 `examples/example-output/amazon-review-analyzer/CASE_STUDY.md`，本节只抽离通用读法。其中表结构管理类节点（建表 / 改列宽 / 取 SheetId 等）是否保留，由 `goal-parity-design.md` 的目标对等判断，workflow-anatomy 不预设去留。

### 6.1 读拓扑的标准 4 步

拿到一份 connections，按这 4 步读：

1. **找入口**：`entry_nodes` = `classify=="1_触发器"` 的节点（如表单触发 / Cron / Webhook）。
2. **顺主链**：从入口沿 `main[0][0].node` 一直走到底，先只走 port=0 这一条主线，分叉支路单独记。
3. **识别多端口节点**：遇到 `IF` / `Switch` / `splitInBatches`，按 §3.1 查端口语义（splitInBatches 的 port=0=done、port=1=loop；IF 的 port=0/1=true/false，**直觉相反别看错**）。
4. **识别回环**：找 `from==to` 的隐式回环（典型是 splitInBatches 的循环体末端回到自己，范式见 §3.2）。

读完拓扑，下一步去 `goal-parity-design.md` 设计等价实现（那里有从拓扑提炼业务目标的推演方法），而不是逐节点翻译。多端口节点和循环结构是读拓扑的两个高频坑，按 §3.1 / §3.2 的范式判定即可。

---

## 附：与 `parse_workflow.py` 的字段对照

| WorkflowIR 字段 | 来源 |
|---|---|
| `workflow_name` / `active` | 顶层 `name` / `active` |
| `node_count` | `len(nodes)` |
| `nodes[].id/name/type/category/credentials/disabled` | §2 确定字段 + `classify()` |
| `nodes[].params_summary` | `_params_summary()` 抽的关键字段 |
| `edges[]` | connections 扁平化（**只取 main 类型**，`ai_*` 不进 edges） |
| `category_distribution` | `Counter(cats)` |
| `credentials_referenced` | 全表 credentials key 去重 |
| `subworkflow_count` | `type` 含 `executeWorkflow` 的节点数 |
| `expression_count` | `raw.count("={{")` |
| `entry_nodes` | classify == `1_触发器` 的 name 列表 |
| `warnings` | 未归类节点 + 子工作流 + 表达式计数 |

**Understand 阶段需要但 IR 没抽的**：parameters 原文（IR 有摘要但常不够）、`ai_*` 连接（LangChain workflow）、`executeOnce` 等执行标记、`staticData`。这些**直接回原 JSON 取**，IR 是索引不是全量快照。
