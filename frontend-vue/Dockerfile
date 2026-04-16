FROM docker.m.daocloud.io/library/node:18-alpine

WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# 清理可能存在的 node_modules (虽然 .dockerignore 已排除，但这能防止意外)
RUN rm -rf node_modules

# 安装依赖
RUN npm install

# 复制源代码 (虽然开发时会挂载 volumes，但为了构建流程先复制)
COPY . .

# 暴露端口
EXPOSE 8080

# 启动开发服务器
CMD ["sh", "-c", "npm run deps:ensure && npm run dev"]
