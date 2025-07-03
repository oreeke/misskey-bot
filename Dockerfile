# 使用Python 3.11作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置Python环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 首先复制依赖文件，利用Docker缓存
COPY requirements.txt /app/

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . /app/

# 创建日志目录
RUN mkdir -p /app/logs && chmod -R 755 /app/logs

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 健康检查
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
  CMD python -c "import os; exit(0 if os.path.exists('/app/logs/bot.log') else 1)"

# 运行机器人
CMD ["python", "run.py"]