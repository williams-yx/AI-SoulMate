# pull-prod-master.ps1
# Prod: git pull origin master, then docker compose up -d
# Server: root@59.110.238.204  Project: /home/admin/ai-soulmate
# Usage: .\pull-prod-master.ps1
#        .\pull-prod-master.ps1 -SkipDocker
#
# =============================================================================
# 致命重要：以下文件在服务器上曾手动改过，绝不能被仓库版本长期覆盖：
#   deploy/nginx/default.conf
#   clean-docker.sh
#   frontend-vue/vite.config.ts
# 否则可能导致 Nginx/前端构建或部署异常。本脚本策略：
#   1) 先把当前磁盘上的上述文件完整备份到 /tmp（含权限尽量保留）
#   2) pull 前清工作区：先试 git checkout HEAD -- path，失败（未跟踪/HEAD 无此 path）则 rm -f；不用 ls-files，避免与 checkout 判断不一致触发 set -e 退出
#   3) pull 结束后立刻用备份原样覆盖回仓库路径——最终内容与脚本开始时一致
# 绝不依赖 stash merge；最终以 cp 还原为准。
# =============================================================================

param(
    [switch]$SkipDocker
)

$Server = "root@59.110.238.204"
$ProjectDir = "/home/admin/ai-soulmate"

Write-Host ">>> SSH $Server : backup nginx+clean-docker+vite.config -> pull master -> RESTORE (never keep repo copy) ..."

# 避免 here-string 中 `git ... HEAD` 被 PowerShell 误解析为 `$HEAD` 变量（为空时导致 rev-parse 无参数 → fatal）
$GitHeadRef = 'HEAD'

# PowerShell 会展开 $ProjectDir、$GitHeadRef；bash 变量 `$BK_*` / `$f` 须写成 `` `$BK_* ``
$remoteBash = @"
set -e
cd $ProjectDir
BK_NGINX=/tmp/ai-soulmate-prod-preserve.default.conf
BK_DOCKER=/tmp/ai-soulmate-prod-preserve.clean-docker.sh
BK_VITE=/tmp/ai-soulmate-prod-preserve.vite.config.ts
[ -f deploy/nginx/default.conf ] && cp -p deploy/nginx/default.conf "`$BK_NGINX" || true
[ -f clean-docker.sh ] && cp -p clean-docker.sh "`$BK_DOCKER" || true
[ -f frontend-vue/vite.config.ts ] && cp -p frontend-vue/vite.config.ts "`$BK_VITE" || true
git fetch origin
git checkout master
for f in deploy/nginx/default.conf clean-docker.sh frontend-vue/vite.config.ts; do
  git checkout $GitHeadRef -- "`$f" 2>/dev/null || rm -f "`$f"
done
git pull --autostash origin master
[ -f "`$BK_NGINX" ] && mkdir -p deploy/nginx && cp -p "`$BK_NGINX" deploy/nginx/default.conf
[ -f "`$BK_DOCKER" ] && cp -p "`$BK_DOCKER" clean-docker.sh
[ -f "`$BK_VITE" ] && mkdir -p frontend-vue && cp -p "`$BK_VITE" frontend-vue/vite.config.ts
rm -f "`$BK_NGINX" "`$BK_DOCKER" "`$BK_VITE"
echo ">>> HEAD:"
git rev-parse --short $GitHeadRef
"@

# Windows 此处字符串常为 CRLF，经管道喂给远程 bash 时 \r 会导致「set: invalid option」「cd: ...\r」等异常，须先统一为 LF
$remoteBash = $remoteBash -replace "`r`n", "`n" -replace "`r", ""
$remoteBash | ssh $Server "bash -s"

if ($LASTEXITCODE -ne 0) {
    Write-Host ">>> git failed (exit $LASTEXITCODE). Skipping Docker."
    exit $LASTEXITCODE
}

if (-not $SkipDocker) {
    Write-Host ">>> docker compose up -d ..."
    $dockerRemote = "cd $ProjectDir && docker compose up -d && docker ps"
    ssh $Server $dockerRemote
}

Write-Host ">>> Done."
