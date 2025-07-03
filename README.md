# Misskey Bot

一个基于 Python 的 Misskey 机器人。

## 功能

- 连接 Misskey API 自动发帖
- 响应其他用户的 @ 操作
- 响应聊天请求
- 使用 DeepSeek API 生成帖子和聊天内容

## 配置

可以通过以下两种方式配置机器人：

### 1. 配置文件

在 `config.yaml` 文件中配置以下内容：

- Misskey API 连接信息（实例 URL 和访问令牌）
- DeepSeek API 密钥和模型名称
- 自动发帖设置（启用状态、发帖间隔、每日最大发帖数量、最大发帖长度）
- 响应设置（是否响应提及和聊天、最大响应长度）
- 笔记可见性设置（默认笔记可见性）
- 系统提示词

参考 `config.yaml.example` 文件了解完整配置选项。

### 2. 环境变量

也可以使用 Docker 环境变量配置机器人：

- `MISSKEY_INSTANCE_URL`: Misskey 实例 URL
- `MISSKEY_ACCESS_TOKEN`: Misskey 访问令牌
- `DEEPSEEK_API_KEY`: DeepSeek API 密钥
- `DEEPSEEK_MODEL`: DeepSeek 模型名称
- `BOT_AUTO_POST_ENABLED`: 是否启用自动发帖
- `BOT_AUTO_POST_INTERVAL`: 发帖间隔（分钟）
- `BOT_AUTO_POST_MAX_PER_DAY`: 每日最大发帖数量
- `BOT_AUTO_POST_MAX_LENGTH`: 最大发帖长度（字符数）
- `BOT_RESPONSE_MENTION_ENABLED`: 是否响应提及
- `BOT_RESPONSE_CHAT_ENABLED`: 是否响应聊天
- `BOT_RESPONSE_MAX_LENGTH`: 最大响应长度
- `BOT_DEFAULT_VISIBILITY`: 默认笔记可见性（public/home/followers/specified）
- `SYSTEM_PROMPT`: 系统提示词

参考 `.env.example` 文件了解完整环境变量选项。

## 部署

### Docker 部署

```bash
# 复制环境变量示例文件并修改
cp .env.example .env
# 编辑 .env 文件，填入你的配置

# 构建 Docker 镜像
docker build -t misskey-bot .

# 运行 Docker 容器
docker run -d --name misskey-bot --env-file .env misskey-bot
```

### 本地部署

```bash
# 复制配置文件示例并修改
cp config.yaml.example config.yaml
# 编辑 config.yaml 文件，填入你的配置

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

## 许可证

MIT