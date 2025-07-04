# Misskey Bot

一只由 Python 实现的 Misskey 机器人，使用 DeepSeek 生成帖子或与用户聊天。

## 配置

选择其中一种方式配置机器人：

### 1. 配置文件 (config.yaml)

```yaml
# Misskey 配置
misskey:
  instance_url: "https://misskey.example.com"       # Misskey 实例 URL
  access_token: "your_access_token_here"            # Misskey 访问令牌

# DeepSeek 配置
deepseek:
  api_key: "your_deepseek_api_key_here"             # DeepSeek API 密钥
  model: "deepseek-chat"                            # 使用的模型名称
  api_base: "https://api.deepseek.com/v1"           # DeepSeek API 基础 URL
  max_tokens: 1000                                  # 最大生成 token 数
  temperature: 0.7                                  # 生成温度

# 机器人配置
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

# API 超时配置
api:
  timeout: 30                                       # API 请求超时时间（秒）
  max_retries: 3                                    # 最大重试次数
  retry_delay: 1.0                                  # 重试延迟（秒）

# 持久化配置
persistence:
  db_path: "data/bot_persistence.db"                # SQLite 数据库文件路径
  cleanup_days: 7                                   # SQLite 数据保存天数

# 日志配置
logging:
  level: "INFO"                                     # 日志级别 (DEBUG/INFO/WARNING/ERROR)
  path: "logs"                                      # 日志文件路径

# 系统提示词
system_prompt: |
  你是一个友好的AI助手，运行在Misskey平台上。
  请用简短、友好的方式回答问题。
  避免使用过于复杂的术语，保持回答简洁明了。
  如果不确定答案，请诚实地表明你不知道，而不是猜测。
```

### 2. 环境变量 (docker-compose.yaml 或 .env)

```bash
# Misskey 配置
MISSKEY_INSTANCE_URL=https://misskey.example.com           # Misskey 实例 URL
MISSKEY_ACCESS_TOKEN=your_access_token_here                # Misskey 访问令牌

# DeepSeek 配置
DEEPSEEK_API_KEY=your_deepseek_api_key_here                # DeepSeek API 密钥
DEEPSEEK_MODEL=deepseek-chat                               # 使用的模型名称
DEEPSEEK_API_BASE_URL=https://api.deepseek.com/v1          # DeepSeek API 基础 URL
DEEPSEEK_MAX_TOKENS=1000                                   # DeepSeek 最大生成 token 数
DEEPSEEK_TEMPERATURE=0.7                                   # DeepSeek 生成温度

# 机器人配置
BOT_AUTO_POST_ENABLED=true                                 # 是否启用自动发帖
BOT_AUTO_POST_INTERVAL=60                                  # 发帖间隔（分钟）
BOT_AUTO_POST_MAX_PER_DAY=10                               # 每日最大发帖数量
BOT_AUTO_POST_MAX_LENGTH=500                               # 最大发帖长度（字符数）
BOT_AUTO_POST_PROMPT=请生成一篇有趣、有见解的社交媒体帖子。    # 自动发帖提示词
BOT_RESPONSE_MENTION_ENABLED=true                          # 是否响应提及（@）
BOT_RESPONSE_CHAT_ENABLED=true                             # 是否响应聊天消息
BOT_RESPONSE_MAX_LENGTH=500                                # 最大响应长度（字符数）
BOT_DEFAULT_VISIBILITY=public                              # 默认帖子可见性（public/home/followers/specified）

# API 超时配置
API_TIMEOUT=30                                             # API 请求超时时间（秒）
API_MAX_RETRIES=3                                          # API 最大重试次数
API_RETRY_DELAY=1.0                                        # API 重试延迟（秒）

# 持久化配置
PERSISTENCE_DB_PATH=data/bot_persistence.db                # SQLite 数据库文件路径
PERSISTENCE_CLEANUP_DAYS=7                                 # SQLite 数据文件保存天数

# 日志配置
LOG_LEVEL=INFO                                             # 日志级别 (DEBUG/INFO/WARNING/ERROR)
LOG_PATH=logs                                              # 日志文件路径

# 系统提示词
SYSTEM_PROMPT=你是一个友好的AI助手，运行在Misskey平台上。请用简短、友好的方式回答问题。避免使用过于复杂的术语，保持回答简洁明了。如果不确定答案，请诚实地表明你不知道，而不是猜测。
```

## 部署

### 克隆项目

```bash
git clone https://github.com/oreeke/misskey-bot.git
cd misskey-bot
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

### 本地部署

```bash
# 复制示例文件
cp config.yaml.example config.yaml
# 编辑 config.yaml ，填入你的配置

# 安装依赖
pip install -r requirements.txt

# 运行机器人
python run.py
```

## 测试

运行机器人之前，先测试 API 连接是否正常：

```bash
# 测试全部连接
pytest tests/ -v
# 或者

# 测试 Misskey API 连接
python -m tests.test_misskey

# 测试 DeepSeek API 连接
python -m tests.test_deepseek
```