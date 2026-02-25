FROM python:3.11-slim

WORKDIR /app

# 防止生成 pyc 文件 + 立即打印日志
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 升级 pip
RUN pip install --no-cache-dir -U pip

# 先复制依赖文件（利用 Docker 缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再复制整个项目
COPY . .

EXPOSE 8000