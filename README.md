# Misskey AI

一只 Python 实现的 Misskey 机器人，使用 DeepSeek 自动发帖或与用户聊天。<br>
修改配置中的 `model` 和 `api_base`，以选择任何兼容 Openai API 的其他模型。

---

## 配置

> 选择一个配置文件：

<details>
<summary>📃 config.yaml</summary>

```yaml
misskey:
  instance_url: "https://misskey.example.com"       # Misskey 实例 URL
  access_token: "your_access_token_here"            # Misskey 访问令牌

deepseek:
  api_key: "your_deepseek_api_key_here"             # DeepSeek API 密钥
  model: "deepseek-chat"                            # 使用的模型名称
  api_base: "https://api.deepseek.com/v1"           # DeepSeek API 基础 URL
  max_tokens: 1000                                  # 最大生成 token 数
  temperature: 0.8                                  # 温度参数

bot:
  auto_post:
    enabled: true                                   # 是否启用自动发帖
    interval_minutes: 60                            # 发帖间隔（分钟）
    max_posts_per_day: 10                           # 每日最大发帖数量
    max_post_length: 500                            # 最大发帖长度（字符数）
    prompt: "请生成一篇有趣、有见解的社交媒体帖子。"    # 自动发帖提示词
  
  response:
    mention_enabled: true                           # 是否响应提及（@）
    chat_enabled: true                              # 是否响应聊天消息
    max_response_length: 500                        # 最大响应长度（字符数）
  
  visibility:
    default: "public"                               # 默认帖子可见性（public/home/followers/specified）

api:
  timeout: 30                                       # API 请求超时时间（秒）
  max_retries: 3                                    # 最大重试次数
  retry_delay: 1.0                                  # 重试延迟（秒）

persistence:
  db_path: "data/bot_persistence.db"                # SQLite 数据库文件路径
  cleanup_days: 7                                   # SQLite 数据库文件保存天数

logging:
  level: "INFO"                                     # 日志级别 (DEBUG/INFO/WARNING/ERROR)
  path: "logs"                                      # 日志文件路径

system_prompt: |
  你是一个可爱的AI助手，运行在Misskey平台上。
  请用简短、友好的方式发帖和回答问题。
```

</details>

<details>
<summary>📃 docker-compose.yaml 或 .env</summary>

```bash
MISSKEY_INSTANCE_URL=https://misskey.example.com           # Misskey 实例 URL
MISSKEY_ACCESS_TOKEN=your_access_token_here                # Misskey 访问令牌

DEEPSEEK_API_KEY=your_deepseek_api_key_here                # DeepSeek API 密钥
DEEPSEEK_MODEL=deepseek-chat                               # 使用的模型名称
DEEPSEEK_API_BASE=https://api.deepseek.com/v1              # DeepSeek API 基础 URL
DEEPSEEK_MAX_TOKENS=1000                                   # DeepSeek 最大生成 token 数
DEEPSEEK_TEMPERATURE=0.8                                   # DeepSeek 温度参数

BOT_AUTO_POST_ENABLED=true                                 # 是否启用自动发帖
BOT_AUTO_POST_INTERVAL=60                                  # 发帖间隔（分钟）
BOT_AUTO_POST_MAX_PER_DAY=10                               # 每日最大发帖数量
BOT_AUTO_POST_MAX_LENGTH=500                               # 最大发帖长度（字符数）
BOT_AUTO_POST_PROMPT=请生成一篇有趣、有见解的社交媒体帖子。    # 自动发帖提示词
BOT_RESPONSE_MENTION_ENABLED=true                          # 是否响应提及（@）
BOT_RESPONSE_CHAT_ENABLED=true                             # 是否响应聊天消息
BOT_RESPONSE_MAX_LENGTH=500                                # 最大响应长度（字符数）
BOT_DEFAULT_VISIBILITY=public                              # 默认帖子可见性（public/home/followers/specified）
SYSTEM_PROMPT=你是一个可爱的AI助手，运行在Misskey平台上。请用简短、友好的方式发帖和回答问题。

API_TIMEOUT=30                                             # API 请求超时时间（秒）
API_MAX_RETRIES=3                                          # API 最大重试次数
API_RETRY_DELAY=1.0                                        # API 重试延迟（秒）

PERSISTENCE_DB_PATH=data/bot_persistence.db                # SQLite 数据库文件路径
PERSISTENCE_CLEANUP_DAYS=7                                 # SQLite 数据库文件保存天数

LOG_LEVEL=INFO                                             # 日志级别 (DEBUG/INFO/WARNING/ERROR)
LOG_PATH=logs                                              # 日志文件路径
```

</details>

---

## 部署

```bash
# 克隆仓库
git clone https://github.com/oreeke/misskey-ai.git
cd misskey-ai
```

> 选择一种部署方式：

### 本地部署

```bash
# 需要 Python 3.11 或更高版本

# 复制并重命名示例文件
cp config.yaml.example config.yaml
# 编辑 config.yaml ，填入你的配置

# 安装依赖
pip install -r requirements.txt

# 运行机器人
python run.py
```

### Docker Compose

```bash
# 编辑 docker-compose.yaml 修改环境变量：
# - MISSKEY_INSTANCE_URL: 你的 Misskey 实例 URL
# - MISSKEY_ACCESS_TOKEN: 你的 Misskey 访问令牌
# - DEEPSEEK_API_KEY: 你的 DeepSeek API 密钥
# - 其他根据需要调整

# 构建镜像
docker compose build

# 启动容器
docker compose up -d
```

> \[!TIP]
>
> 程序启动后首先查询本地历史消息，防止重复响应。<br>
> 接着发起轮询，每分钟 1 次，收到新消息则生成回复。<br>
> 运行 1 分钟后，根据设置进入自动发帖循环。

---

## 测试

> 给机器人做个体检：

### Pytest

```bash
# 安装依赖
pip install -r requirements-dev.txt

# 运行所有测试
pytest tests/ -v

# 跳过慢速测试
pytest tests/ -m "not slow" -v

# 运行集成测试
pytest tests/ -m "integration" -v

# 运行特定测试文件
pytest tests/test_build.py -v
```
