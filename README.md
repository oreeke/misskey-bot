<div align="center">

<h1>Misskey AI</h1>

一只 Python 实现的 Misskey 机器人<br>
使用 DeepSeek 生成的内容发帖或与用户互动<br>
支持兼容 OpenAI API 架构的其他模型<br>
目前运行在：[oreeke.com/@ai](https://oreeke.com/@ai)

</div>

## 开始

### `1` 克隆仓库

```bash
git clone https://github.com/oreeke/misskey-ai.git
cd misskey-ai
```

### `2` 部署方式

#### `a` 手动安装

> 复制 `config.yaml.example` 为 `config.yaml` 并修改配置
<details>
<summary><kbd>📃 config.yaml</kbd></summary>

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
  system_prompt: |                                  # 系统提示词（支持文件导入："prompts/*.txt"，"file://path/to/*.txt"）
    你是一个可爱的AI助手，运行在Misskey平台上。
    请用简短、友好的方式发帖和回答问题。
  
  auto_post:
    enabled: true                                   # 是否启用自动发帖
    interval_minutes: 180                           # 发帖间隔（分钟）
    max_posts_per_day: 8                            # 每日最大发帖数量（凌晨 0 点重置计数器）
    visibility: "public"                            # 自动发帖可见性（public/home/followers/specified）
    prompt: |                                       # 自动发帖提示词
      生成一篇有趣、有见解的社交媒体帖子。
  
  response:
    mention_enabled: true                           # 是否响应提及（@）
    chat_enabled: true                              # 是否响应聊天消息
    chat_memory: 10                                 # 聊天上下文记忆长度（条）
    polling_interval: 60                            # 消息轮询间隔（秒）

api:
  timeout: 30                                       # API 请求超时时间（秒）
  max_retries: 3                                    # API 请求重试次数

db:
  cleanup_days: 30                                  # SQLite 旧消息保留天数

logging:
  level: "INFO"                                     # 日志级别 (DEBUG/INFO/WARNING/ERROR)
```
</details>

> Python ≥ 3.11
```bash
pip install -r requirements.txt
python run.py
```

> 后台运行（可选）
```bash
nohup python run.py & tail -f logs/misskey_ai.log
```

> 作为服务（可选）

<details>
<summary><kbd>📃 misskey-ai.service</kbd></summary>

```ini
[Unit]
Description=Misskey AI Service
After=network.target

[Service]
Type=exec
WorkingDirectory=/path/to/misskey-ai
ExecStart=/path/to/envs/misskey-ai/bin/python run.py
KillMode=control-group
TimeoutStopSec=5

[Install]
WantedBy=multi-user.target
```
</details>

```bash
systemctl daemon-reload
systemctl start misskey-ai.service
```

#### `b` Docker Compose

> 修改 `docker-compose.yaml` 中的环境变量
<details>
<summary><kbd>📃 docker-compose.yaml</kbd></summary>

```yaml
MISSKEY_INSTANCE_URL=https://misskey.example.com           # Misskey 实例 URL
MISSKEY_ACCESS_TOKEN=your_access_token_here                # Misskey 访问令牌
DEEPSEEK_API_KEY=your_deepseek_api_key_here                # DeepSeek API 密钥
DEEPSEEK_MODEL=deepseek-chat                               # 使用的模型名称
DEEPSEEK_API_BASE=https://api.deepseek.com/v1              # DeepSeek API 基础 URL
DEEPSEEK_MAX_TOKENS=1000                                   # DeepSeek 最大生成 token 数
DEEPSEEK_TEMPERATURE=0.8                                   # DeepSeek 温度参数
BOT_SYSTEM_PROMPT=你是一个可爱的AI助手...                    # 系统提示词（支持文件导入："prompts/*.txt"，"file://path/to/*.txt"）
BOT_AUTO_POST_ENABLED=true                                 # 是否启用自动发帖
BOT_AUTO_POST_INTERVAL=180                                 # 发帖间隔（分钟）
BOT_AUTO_POST_MAX_PER_DAY=8                                # 每日最大发帖数量（凌晨 0 点重置计数器）
BOT_AUTO_POST_VISIBILITY=public                            # 自动发帖可见性（public/home/followers/specified）
BOT_AUTO_POST_PROMPT=生成一篇有趣、有见解的社交媒体帖子。      # 自动发帖提示词
BOT_RESPONSE_MENTION_ENABLED=true                          # 是否响应提及（@）
BOT_RESPONSE_CHAT_ENABLED=true                             # 是否响应聊天消息
BOT_RESPONSE_CHAT_MEMORY=10                                # 聊天上下文记忆长度（条）
BOT_RESPONSE_POLLING_INTERVAL=60                           # 消息轮询间隔（秒）
API_TIMEOUT=30                                             # API 请求超时时间（秒）
API_MAX_RETRIES=3                                          # API 最大重试次数
DB_CLEANUP_DAYS=30                                         # SQLite 旧消息保留天数
LOG_LEVEL=INFO                                             # 日志级别 (DEBUG/INFO/WARNING/ERROR)
```
</details>

```bash
docker compose build
docker compose up -d
```

> [!NOTE]
>
> 自动发帖时 API 请求默认携带时间戳，以绕过 [DeepSeek 缓存](https://api-docs.deepseek.com/zh-cn/news/news0802)
