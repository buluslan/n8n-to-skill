# 产物 SKILL.md 设计说明

> 本文件职责：讲 n8n-to-skill 生成的【产物 skill】的 SKILL.md 该如何设计——段落为什么这样排、每段填写要点、过审自检标准。
> 与 `assets/skill-template.md` 的分工：那里是带占位符的填空骨架，这里只讲设计逻辑与判断标准，不重复骨架内容。
> 读者：n8n-to-skill 自身（Plan & Build 阶段生成产物 SKILL.md 时读本文件做设计决策）。

## 一、frontmatter 设计逻辑

frontmatter 是产物的**路由合同**。决定产物 skill 何时被 Agent 认领、有什么权限、来源可溯。

### name
- 全小写 + 连字符分词（如 `inventory-forecaster` / `review-analyzer`，非 `AmazonReviewAnalyzer`）
- 用**业务领域**命名，禁用工具前缀（`n8n-` / `sheets-` / `gemini-`）——原工具在转换中已下线，前缀即 sediment
- 与产物目录名严格一致（大小写、连字符位置）

### description（路由合同式，硬约束：≤1024 字符、无尖括号）
推荐 3 段式结构（顺序固定）：
1. **能力句**：一句话讲做什么 + 业务价值（先定位能力，再说价值）
2. **触发词清单**：用户实际会说的形态（"当用户提供 X 并说 Y/Z 时调用"）
3. **反触发词清单**：明确排除的相邻场景（"不处理 A / 不负责 B"）

pushy 标准：触发词清单长到 Agent 敢认领；反触发词清单明确到不误伤相邻 skill。两者缺一即边界性失败。

### allowed-tools
- **精确到子权限**：写 `mcp__sorftime__product_detail`，不写泛 `mcp__sorftime`
- **只列真正调用的工具**：不预留"以后可能用"（sprawl 防范）
- 文件操作用 `Read` / `Write` / `Edit`；仅在必须执行命令时才给 `Bash(pattern:*)`
- 凭证读取不列入（`os.environ.get` 是脚本内部行为，不算工具调用）

### metadata（溯源字段，至少含以下三项）
- `source_workflow`：原 n8n workflow 文件名（带扩展名）
- `goal_alignment`：一句话说明对齐了原 workflow 的哪个业务目标
- `conversion_date`：转换日期（ISO 格式 `YYYY-MM-DD`）

## 二、8 段正文结构

固定顺序：定位 → 触发 → 输入 → 输出 → 核心能力 → 流程 → 凭证边界 → 失败降级。

### 设计依据总表

每段对应 skill-creator 的一条防失败要求，少一段即留缺口：

| 段 | 防的失败模式 | 缺失后果 |
|---|---|---|
| 定位 | duplication | 与相邻 skill 边界模糊，Agent 不知该不该认领 |
| 触发 | no-op | Agent 等到用户明示才启动，丢自动化机会 |
| 输入 | Agent 优先非问卷 | 退化为表单式调用，每项必填僵化 |
| 输出 | premature completion | 流程跑完无可观察产物，无法验收 |
| 核心能力 | duplication + 指引路径 | 能力散落各段，重复定义 |
| 流程 | premature completion | 中间无产物，早期终止无感 |
| 凭证边界 | sediment | 残留下线工具的凭证，读者误以为还要配置 |
| 失败降级 | negation + no-op | 错误时无路可走，Agent 卡死或静默失败 |

### 每段填写指引

#### 1. 定位
- 1-2 句：解决什么业务问题 + 给谁用
- 与 description 的关系：description 给 Agent 路由用（紧凑、含触发词）；定位段给人读首屏用（可加业务上下文）
- 常见坑：写成工具功能列表（"读 CSV、调 AI、写文件"）而非业务定位（如"把评论变洞察 / 把订单变补货建议 / 把日志变异常预警"）

#### 2. 触发
- 列用户输入的形态：关键词、文件类型、命令模式
- 写成可执行判断："用户给数据源（例如 CSV 路径 + 含'分析/打标签/出洞察'，或飞书 doc 链接 + 含'抽取/汇总'）时任一关键词命中即启动"
- 常见坑：只写关键词不写输入形态（Agent 不知道要等 CSV 路径）

#### 3. 输入
- 约定式列出：路径、字段名、格式约束、必填/可选
- Agent 优先原则：让 Agent 自行判断缺失项并主动要，而非在 frontmatter 写死"缺字段就报错"
- 常见坑：把所有字段标必填（退化为问卷）

#### 4. 输出
- 每个产物列出：文件名、字段结构、落盘路径
- 产物形态优先选可被下游 Agent 读取验证的（文件 > 日志行）
- 常见坑：只写"生成报告"，不指明格式与路径（下游无法接续）

#### 5. 核心能力
- bullet 清单，每能力一行（动词开头）
- **每条能力只在此段定义一次**（duplication 硬约束）
- 实现细节指向 `references/<具体文件>.md`，不在 SKILL.md 展开
- 常见坑：把能力写成节点清单（"节点 1 做的 / 节点 2 做的"）——这是逐节点翻译的味，违反目标对等

#### 6. 流程
- 顺序号 + 每步的可观察产物（"步骤 N → 产物 X"）
- 每步必须落地一个文件或一行结构化日志（premature completion 硬约束）
- 常见坑：步骤无产物（"调用 AI 处理" → 到底产出了什么？）

#### 7. 凭证边界
- 列每个凭证：环境变量名、用途、读取位置
- **剥离已下线工具的凭证**：目标对等重写后消失的凭证不出现（sediment 硬约束）。判定方法见 `references/credential-safety.md` 第六节
- 常见坑：照抄原 workflow 的 credentials 清单（包含已被目标对等消化的存储类凭证如 `googleSheetsOAuth2Api` / `airtableApi`，或生成式 AI 凭证如 `openAiApi` / `googleGeminiApi`）

#### 8. 失败降级
- 正向表述：用"凭证缺失时跳过该步并标 [SKIPPED]"代替"不要报错"（negation 硬约束）
- 列常见失败 + 降级路径，而非异常处理大全
- 常见坑：只写"出错重试"，不指明重试上限与降级后的最终状态

## 三、与 skill-creator quality-checklist 对应

产物 SKILL.md 上线前的自检对照表。

### 4 轴自检
- **发现性**：description 的触发词清单是否覆盖用户实际提问形态（含口语变体）
- **边界性**：反触发词是否排除相邻 skill 的误认领
- **执行性**：每段指令动词开头、可被 Agent 直接执行（无"视情况而定"的悬空指令）
- **完备性**：核心能力是否覆盖原 workflow 的全部业务目标（用 IO 约定表逐项核）

### 6 失败模式自检（产物段 → 防的失败模式）
- premature completion → 输出段 + 流程段每步有可观察产物
- duplication → 核心能力段每能力单一定义；与 references 不重复
- sediment → 凭证边界段剥离 n8n 残留凭证；name 无工具前缀
- sprawl → SKILL.md <500 行，超出的细节拆 references
- no-op → 每条指令动词开头、有可执行判断标准
- negation → 失败降级段用正向表述（跳过/降级/标记），少用"不要/禁止"

## 四、行数控制与渐进披露

- **硬上限 500 行**（skill-creator sprawl 规范）。超限即拆 references。
- **设计原则：指引路径不写内容**
  - SKILL.md 只写【做什么】+【去哪查】
  - 实现细节、代码模板、复杂校验逻辑 → `references/`
  - 大段脚本、完整示例 → `scripts/` 或 `assets/`
- **渐进披露顺序**：Agent 先读 SKILL.md → 按需读对应 references → 按需读 scripts

拆分判断标准（任一命中即拆出 SKILL.md）：
- 单段内容超过 30 行
- 同一细节会被多处引用
- 内容写给运维而非运行时（如设计上下文、转换决策记录）

## 五、案例填空示范（指针）

完整 frontmatter + 8 段填空示范（以 `amazon-review-analyzer` 为例）见 `examples/example-output/amazon-review-analyzer/CASE_STUDY.md`，本文件不重复展开；填空骨架见 `assets/skill-template.md`。

通用收敛规则：原 n8n **N 个节点 → 产物 M 条核心能力 + K 步流程（无 1:1 关系）**——节点结构不映射，业务目标对齐即可。映射逻辑见 `references/node-mapping.md`，凭证消化判定见 `references/credential-safety.md`。
