FROM docker.m.daocloud.io/library/python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    fonts-dejavu-core \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libdbus-1-3 \
    libegl1 \
    libfontconfig1 \
    libgl1 \
    libglib2.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libgstreamer1.0-0 \
    libgtk-3-0 \
    libice6 \
    libjavascriptcoregtk-4.1-0 \
    libnss3 \
    libopengl0 \
    libsm6 \
    libwebkit2gtk-4.1-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb-cursor0 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxkbcommon-x11-0 \
    libxkbcommon0 \
    libxrandr2 \
    libxrender1 \
    libxtst6 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
# 使用阿里云镜像源加速安装 (推荐国内使用)
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 官方源安装命令 (已注释，如需使用请取消注释并注释掉上方命令)
# RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建上传目录
RUN mkdir -p /app/uploads

# 暴露端口
EXPOSE 3000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]
