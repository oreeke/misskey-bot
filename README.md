# Misskey Bot

一只由 Python 实现的 Misskey 机器人，使用 DeepSeek 生成帖子或与用户聊天。

## 配置

选择其中一种方式配置机器人：

### 1. 配置文件 (config.yaml)

```yaml
misskey:
  instance_url: "https://misskey.example.com"       # Misskey 实例 URL
  access_token: "your_access_token_here"            # Misskey 访问令牌

deepseek:
  api_key: "your_deepseek_api_key_here"             # DeepSeek API 密钥
  model: "deepseek-chat"                            # 使用的模型名称

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
  
system_prompt: |
  你是一个友好的AI助手，运行在Misskey平台上。
  请用简短、友好的方式回答问题。
  避免使用过于复杂的术语，保持回答简洁明了。
  如果不确定答案，请诚实地表明你不知道，而不是猜测。
```

### 2. 环境变量 (.env)

```bash
MISSKEY_INSTANCE_URL=https://misskey.example.com           # Misskey 实例 URL
MISSKEY_ACCESS_TOKEN=your_access_token_here                # Misskey 访问令牌
DEEPSEEK_API_KEY=your_deepseek_api_key_here                # DeepSeek API 密钥
DEEPSEEK_MODEL=deepseek-chat                               # 使用的模型名称
BOT_AUTO_POST_ENABLED=true                                 # 是否启用自动发帖
BOT_AUTO_POST_INTERVAL=60                                  # 发帖间隔（分钟）
BOT_AUTO_POST_MAX_PER_DAY=10                               # 每日最大发帖数量
BOT_AUTO_POST_MAX_LENGTH=500                               # 最大发帖长度（字符数）
BOT_AUTO_POST_PROMPT=请生成一篇有趣、有见解的社交媒体帖子。    # 自动发帖提示词
BOT_RESPONSE_MENTION_ENABLED=true                          # 是否响应提及（@）
BOT_RESPONSE_CHAT_ENABLED=true                             # 是否响应聊天消息
BOT_RESPONSE_MAX_LENGTH=500                                # 最大响应长度（字符数）
BOT_DEFAULT_VISIBILITY=public                              # 默认帖子可见性（public/home/followers/specified）
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
# 编辑 docker-compose.yml 修改环境变量：
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

在运行机器人之前，先测试 API 连接是否正常：

```bash
# 测试全部连接
pytest tests/ -v
# 或者

# 测试 Misskey API 连接
python -m tests.test_misskey

# 测试 DeepSeek API 连接
python -m tests.test_deepseek
```