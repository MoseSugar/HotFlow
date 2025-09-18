# HotFlow

一套围绕淘宝联盟数据抓取与 AI 文案生成的最小可行方案，默认覆盖抽纸、洗衣液、猫粮、狗粮、猫砂五大高频品类。项目提供端到端的流程：

1. 从淘宝联盟开放平台定时拉取热卖商品数据；
2. 将数据存入关系型数据库，方便后续筛选与扩展；
3. 通过 OpenAI 模型生成多平台、多风格的营销文案，并落库备份。

## 快速开始

### 1. 安装依赖

推荐使用 Python 3.10+ 与虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入淘宝联盟与 OpenAI 的密钥：

```bash
cp .env.example .env
# 编辑 .env 文件，写入实际凭据
```

关键环境变量说明：

| 变量 | 说明 |
| --- | --- |
| `TB_APP_KEY` / `TB_APP_SECRET` | 淘宝联盟开放平台凭据 |
| `TB_ADZONE_ID` | 推广位 ID |
| `HOTFLOW_DATABASE_URL` | SQLAlchemy 兼容的数据库地址（MySQL / PostgreSQL / SQLite） |
| `OPENAI_API_KEY` | OpenAI API Key，用于生成文案 |
| `HOTFLOW_KEYWORDS` | （可选）自定义抓取关键词，默认即五大品类 |

### 3. 初始化数据库

```bash
hotflow init-db
```

### 4. 抓取商品数据

```bash
# 默认抓取 .env 中配置的关键词，可通过 --keyword 追加/覆盖
hotflow fetch --pages 2 --page-size 40
```

命令会自动完成签名、调用 `taobao.tbk.dg.material.optional` 接口，并将结果写入 `taoke_items` 表。数据库结构定义在 `hotflow/db.py` 中，可根据实际业务扩展字段。

### 5. 生成 AI 文案

```bash
# 为最新商品生成三种平台文案
hotflow generate-copy --variants 3
```

生成流程：

1. 读取数据库中的商品信息；
2. 使用 `hotflow/prompts.py` 的模板构建 Prompt；
3. 调用 OpenAI Chat Completion 接口，要求返回 JSON 格式的多平台文案；
4. 解析后写入 `creatives` 表，方便后续 A/B 测试或人工审核。

### 6. 查看结果

```bash
# 列出最近的商品
hotflow list-items --limit 5

# 查看生成的文案
hotflow list-creatives --limit 5
```

## 架构概览

- **配置层**：`hotflow/config.py` 从环境变量加载淘宝、数据库、OpenAI 等信息，支持命令行动态覆盖。
- **抓取层**：`hotflow/taobao.py` 封装 `taobao.tbk.dg.material.optional` 的请求签名、参数构建与结果解析。
- **存储层**：`hotflow/db.py` 使用 SQLAlchemy Core 定义 `taoke_items`、`creatives` 两张核心表，提供批量写入与查询能力。
- **AI 文案**：`hotflow/copymaker.py` + `hotflow/prompts.py` 负责 Prompt 渲染、JSON 解析与 `Creative` 实体落库。
- **调度层**：`hotflow/pipeline.py` 打通「抓取 → 入库 → 文案生成」的编排逻辑；`hotflow/cli.py` 提供命令行入口，便于集成到 `cron` 或其他调度系统。

## 后续扩展建议

- 接入 Airflow / Prefect 等工作流框架，实现更复杂的调度与依赖管理；
- 为商品打标签（佣金区间、销量等级、商家类型等），便于后续筛选；
- 文案生成阶段接入 Dify、审核策略或第三方敏感词校验；
- 增加多平台发布适配，比如小红书/微博/知乎的格式化输出或 API 对接。

## 开发调试

- 运行单元测试：

  ```bash
  pytest
  ```

- 代码风格：项目遵循标准 Python 类型注解与模块划分，可视需求引入 Ruff、mypy 等工具。

---

如需进一步定制或扩展更多品类，请在现有模块基础上调整关键词、数据库 schema 以及 Prompt 模板，即可快速复制整个流程。
