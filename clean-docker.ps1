# 清理 ai-soulmate 原项目相关的 Docker 资源
# 不会影响 ai-soulmate-admin 项目的内容

Write-Host "🚧 开始清理 ai-soulmate 项目 Docker 资源..." -ForegroundColor Yellow

# 1. 停止并删除前台与原后台容器
$containers = "ml-frontend", "ml-backend", "ml-db"
foreach ($container in $containers) {
    if (docker ps -a -q -f name=^/${container}$) {
        Write-Host "🗑️ 删除容器: $container" -ForegroundColor Cyan
        docker rm -f $container 2>&1 | Out-Null
    }
}

# 2. 删除前台与原后台镜像
$images = "ml-frontend:latest", "ml-backend:latest"
foreach ($image in $images) {
    if (docker images -q $image) {
        Write-Host "🗑️ 删除镜像: $image" -ForegroundColor Cyan
        docker rmi -f $image 2>&1 | Out-Null
    }
}

# 3. 清理悬空镜像 (构建失败产生的 <none>)
Write-Host "🧹 清理悬空镜像..." -ForegroundColor Cyan
docker image prune -f

# 4. 共用网络不再在个体项目清理脚本中强制删除，以防止另一个项目瘫痪
Write-Host "🌐 略过网络清理 (ml-network 可能被 admin 共用)..." -ForegroundColor Cyan

Write-Host "✨ ai-soulmate 原项目清理完成！" -ForegroundColor Green
Write-Host "🚀 重新启动请运行: docker-compose up --build -d" -ForegroundColor Cyan
