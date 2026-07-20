# 凭证安全硬约束

> 命中 credentials 节点（`外部付费数据` / `存储协作` 中带凭证的 httpRequest / `HTTP Auth` / `OAuth` 节点）时读此文件。

## 一、安全红线（不可协商）

n8n workflow 中的所有 credentials / API key / OAuth token / bearer token / client secret，**一律不得写进 skill 明文**。覆盖范围：

- `SKILL.md` 正文与 frontmatter
- `references/` 下任何 `.md`
- `scripts/` 下任何 `.py` 源代码（含硬编码字符串与注释）
- `examples/` 输入输出样例
- 测试用例、配置文件、README

skill 代码库默认可公开、可 git push、可交付第三方。**任何文件中出现明文 key 即视为安全事故**。

### 允许的 key 出现形式（仅限以下四种）

1. `.env.example` 里的**占位符**（等号右侧留空或写 `<your-key>`）
2. `.env` 文件（必须被 `.gitignore` 排除）
3. 运行时从 `os.environ.get()` 读取
4. 凭证文件的**路径**（路径可进代码，文件内容不进）

---

## 二、.env.example 占位规范

### 生成时机

`parse_workflow.py` 命中任何带 credentials 的节点时，在 skill 根目录生成或追加 `.env.example`。

### 命名约定

- 变量名：**全大写 snake_case**，业务可读（`GOOGLE_SHEETS_OAUTH_TOKEN` 优于 `TOKEN1`）
- 一行一个变量，等号右侧**留空**或写占位说明
- 每个变量上方写两行注释：来源节点名 + 用途
- 文件尾追加提示行

### 模板

```dotenv
# 来源节点: googleGemini (节点名 "Gemini 打标")
# 用途: 调 Gemini 给评论打标签
GEMINI_API_KEY=

# 来源节点: httpRequest 调 sheets.googleapis.com (节点名 "写入 Sheet")
# 用途: OAuth2 Bearer Token，写 Google Sheets
GOOGLE_SHEETS_OAUTH_TOKEN=

# 复制 .env.example 为 .env 后填入真值；.env 不纳入 git
```

### .gitignore 强制项

生成 `.env.example` 的同时，在 skill 根目录 `.gitignore` 写入 `.env`。文件已存在则追加（去重），不存在则创建。

---

## 三、运行时读环境变量

### Python 读取模式

```python
import os

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("缺少 GEMINI_API_KEY，请复制 .env.example 为 .env 并填值")
```

- 缺 key 时**显式报错并指明解决路径**，禁止静默跳过（否则触发 premature completion）
- 优先用 `os.environ.get()` 而非 `os.environ["X"]`（后者抛 KeyError，信息不友好）
- 在模块顶部一次性读完，函数内复用变量

### .env 加载

skill 运行入口（`main.py` 或 `run.py`）在最早一步加载 `.env`：

```python
from dotenv import load_dotenv
load_dotenv()
```

`python-dotenv` 写入 `requirements.txt`。

---

## 四、HTTP Auth / OAuth 凭证处理

### 通用规则

token / bearer / client_secret 一律走 env 或凭证文件路径，**不在请求代码中内联**。

两种合规写法：

```python
# 写法一：env
headers["Authorization"] = f"Bearer {os.environ.get('XXX_TOKEN')}"

# 写法二：凭证文件路径（内容由用户本机准备）
CRED_PATH = os.path.expanduser("~/.config/my_skill/credentials.json")
with open(CRED_PATH) as f:
    creds = json.load(f)
```

### n8n credential type → skill 映射

| n8n credential type | skill 处理方式 |
|---|---|
| `httpBasicAuth` | env: `BASIC_USER` / `BASIC_PASS` |
| `httpHeaderAuth` | env: `HEADER_NAME` / `HEADER_VALUE` |
| `oAuth2Api` | env: `OAUTH_TOKEN`；需要 refresh 流程则走凭证文件路径 |
| `googleSheetsOAuth2Api` | 见第六节「目标对等消化」 |
| `googleGeminiApi` | env: `GEMINI_API_KEY`，或目标对等重写后无需（见第六节）；老 workflow 可能用 `googlePalmApi`（PaLM 2），按 `googleGeminiApi` 处理 |

### 示例与文档中的占位

- 示例 curl 用 `$TOKEN` 变量占位：`curl -H "Authorization: Bearer $TOKEN"`
- 文档截图、PR 描述、issue 中粘贴前先脱敏
- OAuth refresh / 令牌续期交由外部工具（如 `gcloud auth application-default login`），skill 主流程不实现 refresh 逻辑（除非这是 skill 的核心能力）

---

## 五、外部 API 调用封装模式

`外部付费数据` 类（dataforseo / keepa / exa 等）的 httpRequest，在 `scripts/` 下**封装成独立函数**，禁止在主流程里裸调 `requests`。

### 封装模板

```python
# scripts/keepa_client.py
import os
import requests

def fetch_product(asin: str):
    key = os.environ.get("KEEPA_API_KEY")
    if not key:
        raise RuntimeError("缺少 KEEPA_API_KEY")
    try:
        resp = requests.get(
            "https://api.keepa.com/product",
            params={"key": key, "asin": asin},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except (requests.HTTPError, requests.Timeout) as e:
        # 降级：返回带错误标记的结构，让上层流程跳过该条而非整体崩溃
        return {"asin": asin, "error": str(e), "degraded": True}
```

### 封装要求

- 每个外部 API 一个文件（`keepa_client.py` / `dataforseo_client.py`），职责单一
- key 在函数内从 env 读，**不进函数签名**（签名传 key 等于把凭证当参数，调用方会持有）
- 调用失败必须有**降级路径**：返回错误结构 / 写日志 / 跳过该条，让上层流程可继续
- 超时、重试参数硬编码在封装层，调用方不感知

---

## 六、目标对等重写的附带价值：消除凭证依赖

**目标对等重写经常让原 workflow 的凭证整体消失**。这是 skill 化最显著的安全收益，每次转换时主动核查并利用。

### 评论分析案例：两个凭证整体消化

原 workflow（18 节点）依赖两个凭证：

| 凭证 | 原用途 | 目标对等重写后 |
|---|---|---|
| `googleGeminiApi`（Gemini；老 workflow 可能标为 `googlePalmApi`） | 2 个生成式 AI 节点：评论打标 + 生成洞察 | skill 直接调用 Claude（skill 运行环境自带 Claude 凭证，用户无需额外配置） |
| `googleSheetsOAuth2Api` | 8 个 Sheets 节点：读写表、调 Sheets API 扩列宽 | skill 改用本地 CSV（读 CSV / 写 CSV / 生成报告 CSV），无表结构、无 OAuth |

### 消除的根因

- **生成式 AI 类**：n8n 调 Gemini 需用户自备 key；skill 跑在 Claude Code 里，LLM 能力直接由 skill 调用 Claude 提供，外部 LLM key 失去存在理由
- **存储协作类**：n8n 的 Sheets / Airtable / Notion 节点都需要 OAuth；目标对等重写把"协作存储"消化成"本地文件"，存储凭证随之消失
- **表结构管理类**：评论分析案例中「取表格元数据 / 提取 SheetId / 扩展列宽至 30 列」3 个节点纯粹是 Sheets 表结构维护，本地文件无此概念，凭证无用武之地

### 转换时的核查动作

在 IR（中间表示）阶段对每个原 credential 做一次判定：

1. 这个 credential 支撑的能力，在目标对等重写后**是否还需要**？
2. 若不再需要 → IR 中标注「凭证已消化」，`.env.example` 不生成对应条目
3. 若仍需要 → 走第二到第五节的 env 规范正常保留
4. 判定结论与理由记录在 IR 的「凭证决策」节

### 例外：用户明确要求保留集成

用户在需求中明确指定保留某个外部集成时（如「洞察报告必须写回我公司的 Google Sheet」），该凭证走 env 规范保留，并在 IR「用户需求对齐」节记录该决策来源。

---

## 七、交付前自检清单

skill 交付前逐项过：

- [ ] 全目录扫描无明文 key：`grep -riE "(api_key|token|password|secret)\s*[:=]\s*['\"][A-Za-z0-9]{8,}"` 无真值命中
- [ ] `.env.example` 所有变量右侧为空或 `<placeholder>`
- [ ] `.gitignore` 包含 `.env`
- [ ] 凭证使用点全部走 `os.environ.get` 或凭证文件路径
- [ ] 已对每个原 credential 做过「是否消化」判定，结论记录在 IR
