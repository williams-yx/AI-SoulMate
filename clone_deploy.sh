#!/bin/bash

# ================= 配置区域 =================
# 开发侧配置 (Source)
# 从环境变量读取，避免将凭据硬编码进仓库
SOURCE_TOKEN="${SOURCE_TOKEN:-}"
SOURCE_QQ_EMAIL="3273161867@qq.com" 
SOURCE_REPO="gitee.com/xppsec/ai-soulmate.git" 

# 拉取与部署配置
BRANCH="master"  # 确保拉取当前真正修复了 SQL 文件的 master 分支
WORKSPACE="/home/admin"
PROJECT_DIR="ai-soulmate"
# ============================================

# 对邮箱中的 @ 符号进行转义，满足 HTTP Base Auth 格式
ENCODED_SOURCE_EMAIL="${SOURCE_QQ_EMAIL/@/%40}"

# 构建带有私人令牌的免密拉取 URL
SOURCE_URL="https://${ENCODED_SOURCE_EMAIL}:${SOURCE_TOKEN}@${SOURCE_REPO}"

if [ -z "$SOURCE_TOKEN" ]; then
    echo "❌ 未设置 SOURCE_TOKEN 环境变量，已终止。"
    exit 1
fi

echo "1. 进入目标工作目录: $WORKSPACE"
mkdir -p "$WORKSPACE"
cd "$WORKSPACE" || { echo "❌ 无法进入目录 $WORKSPACE，请检查权限。"; exit 1; }

echo "2. 安全起见，为了彻底断绝一切代码冲突的可能，开始清空旧容器与文件..."
if [ -d "$PROJECT_DIR" ]; then
    # -rf 是递归+强制无提示删除目录及子文件
    rm -rf "$PROJECT_DIR"
    echo "   旧目录 $PROJECT_DIR 已被彻底清除。"
fi

echo "3. 正在从服务器直接克隆最新的代码树 (锁定分支: $BRANCH)..."
# 使用私人令牌免密码克隆
git clone -b "$BRANCH" "$SOURCE_URL" "$PROJECT_DIR"

if [ $? -eq 0 ]; then
    echo "✅ 全新代码克隆大功告成！"
else
    echo "❌ 仓库克隆意外中断，请检查 Gitee 的 Token 权限或网络连通状态。"
    exit 1
fi

echo "🎉 强制覆盖式代码拉取任务执行完毕！"
echo "📂 当前最新且纯洁如初的代码存放点: $WORKSPACE/$PROJECT_DIR/ "
