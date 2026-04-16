#!/bin/bash
# 清理 ai-soulmate 原项目相关的 Docker 资源
# 不会影响 ai-soulmate-admin 项目的内容

echo -e "\e[33m🚧 开始清理 ai-soulmate 项目 Docker 资源...\e[0m"

# 1. 停止并删除前台与原后台容器
for container in ml-frontend ml-backend ml-db; do
    if [ "$(docker ps -a -q -f name=^/${container}$)" ]; then
        echo -e "\e[36m🗑️  删除容器: $container\e[0m"
        docker rm -f $container >/dev/null 2>&1
    fi
done

# 2. 删除前台与原后台镜像
for image in ml-frontend:latest ml-backend:latest; do
    if [ "$(docker images -q $image)" ]; then
        echo -e "\e[36m🗑️  删除镜像: $image\e[0m"
        docker rmi -f $image >/dev/null 2>&1
    fi
done

# 3. 清理悬空镜像 (构建失败产生的 <none>)
echo -e "\e[36m🧹 清理悬空镜像...\e[0m"
docker image prune -f

# 4. 共用网络不再在个体项目清理脚本中强制删除，以防止另一个项目瘫痪
echo -e "\e[36m🌐 略过网络清理 (ml-network 可能被 admin 共用)...\e[0m"

echo -e "\e[32m✨ ai-soulmate 原项目清理完成！\e[0m"
echo -e "\e[36m🚀 重新启动请运行: docker compose up -d --build\e[0m"
