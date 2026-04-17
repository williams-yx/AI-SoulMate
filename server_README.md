

# AI SoulMate

> **注意：此文档是项目的核心说明文档，整合了开发、部署、功能和故障排查等所有关键信息。**

---

## 目录

1.  [项目简介](#1-项目简介)
2.  [快速启动 (Docker)](#2-快速启动-docker)
3.  [本地开发指南](#3-本地开发指南)
4.  [服务器部署与启动脚本](#4-服务器部署与启动脚本)
5.  [账号与认证](#5-账号与认证)
6.  [产品功能特性](#6-产品功能特性)
7.  [部署与运维](#7-部署与运维)
8.  [技术文档索引](#8-技术文档索引)
9.  [常见问题与故障排除](#9-常见问题与故障排除)
10. [项目结构](#10-项目结构)
11. [提交文档规范（本次改动）](#八提交文档规范本次改动)

---

## 1. 项目简介

**版本**: v0.7.0

AI SoulMate 是一个融合 **AIGC（AI生成内容）** 与 **3D打印技术** 的 **STEAM教育平台**，通过"造梦工作室 → 打印履约 → 智能底座"实现从创意到实物、从作品到陪伴的完整闭环体验。

### 核心价值
*   **文生3D**: 一句话生成3D模型（Web/小程序）。
*   **打印履约**: 一键下发打印任务并追踪状态。
*   **智能底座**: 让作品可对话、有记忆、可持续陪伴。

### 技术栈
*   **后端**: Python 3.12 + FastAPI + PostgreSQL + Redis
*   **前端**: Vue 3 + Vite + TypeScript
*   **部署**: Docker + Docker Compose

---

## 2. 快速启动 (Docker)

本项目已全面支持 Docker 容器化部署，这是最推荐的启动方式。

### 2.1 环境要求
*   Docker & Docker Compose
*   Windows / Linux / macOS

### 2.2 启动命令

在项目根目录下，使用 PowerShell 或终端运行：

```bash
# 1. (可选) 清理旧环境
./clean-docker.ps1

# 2. 构建并启动所有服务（后台运行）
docker-compose up -d --build
```

### 2.3 访问地址
启动成功后，访问以下地址：
*   **前端页面**: [http://localhost:8080](http://localhost:8080)
*   **后端 API**: [http://localhost:3000](http://localhost:3000)
    *   **接口文档**: [http://localhost:3000/docs](http://localhost:3000/docs)
*   **管理后台**: [http://localhost:3000/admin](http://localhost:3000/admin)

### 2.4 常用 Docker 操作
```bash
# 查看运行状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## 3. 本地开发指南

如果你想在本地修改代码并实时预览（Hot Reload），Docker 环境已经为你配置好了挂载。

1.  **后端开发**: 修改 `backend/` 目录下的 Python 代码，服务会自动重启。
2.  **前端开发**: 修改 `frontend-vue/` 目录下的 Vue 代码，浏览器会自动刷新。站点标签页图标：`frontend-vue/public/favicon.png`（PNG 带 Alpha，背景透明），由 `frontend-vue/index.html` 的 `<link rel="icon" ... href="/favicon.png" />` 引用。

### 前端国际化（vue-i18n）

* **依赖**：`vue-i18n`（见 `frontend-vue/package.json`）。
* **入口与文案**：`frontend-vue/src/main.ts` 挂载 `i18n`；中英文键值集中在 `frontend-vue/src/locales/index.ts`（`zh-CN` / `en-US`），可按命名空间（如 `authModal`、`studio`）扩展。
* **使用方式**：在组件中 `import { useI18n } from 'vue-i18n'`，`const { t, locale } = useI18n()`，模板与脚本内用 `t('某键')`；顶栏语言切换见 `frontend-vue/src/App.vue`（`toggleAppLocale`）。
* **与业务对齐**：登录/注册弹窗 `AuthModal.vue` 在合并翻译分支后仍保持与后端一致的注册方式（含 `register_via`、账号/手机/邮箱分栏等），文案走 `authModal.*`；造梦页 `StudioPage.vue` 中历史摘要与参考图占位使用 `studio.historyItemSummary.*` 等键。

### 全局表单样式与自动填充（深色输入框）

* **类名**：登录/注册等深色输入框统一使用全局类 `input-dark`（定义在 `frontend-vue/src/App.vue`），背景色与 `AuthModal` 等组件一致。
* **自动填充**：Chrome / Edge 等对已保存凭据会套用 `-webkit-autofill` 高亮，易把背景变成浅色。`App.vue` 中为 `.input-dark` 增加 `:-webkit-autofill` 与标准 `:autofill` 覆盖：用大面积 `inset` `box-shadow` 模拟深色底、`-webkit-text-fill-color` 保持浅色字，focus 时边框与 `input-dark:focus` 一致。

### 环境依赖对照 (手动配置参考)
*   **Python**: 3.12.3
*   **Node.js**: v18.19.1
*   **关键 Python 包**: `fastapi`, `uvicorn`, `bcrypt==3.2.2`, `PyJWT==2.7.0`

---

## 4. 服务器部署与启动脚本

本章节包含用于 Linux 服务器环境（如 Ubuntu）的启动和停止脚本。这些脚本用于在非 Docker 环境下直接运行服务。

### 4.1 启动脚本 (`start-local.sh`)

此脚本用于在服务器上启动后端（FastAPI）和前端（构建后的 Vue 静态文件服务）。

```bash
#!/bin/bash

# AI SoulMate 本地开发版启动脚本（无需 Docker）

echo "🚀 启动 AI SoulMate 项目（本地开发模式）..."
echo ""

# 激活 conda 环境
source ~/miniconda3/etc/profile.d/conda.sh
conda activate ai-soulmate

# 进入项目目录
ROOT_DIR="/home/ubuntu/ai-soul-mate/v0.7.0"
cd "$ROOT_DIR"

# 日志目录（确保存在）
mkdir -p "$ROOT_DIR/logs"

# 检查后端依赖
echo "📦 检查依赖..."
pip install -q fastapi uvicorn asyncpg redis passlib python-jose[cryptography] pydantic PyJWT==2.7.0 bcrypt==3.2.2

# 启动后端（后台运行）
echo "🔧 启动后端服务 (端口 3000)..."
cd backend
nohup uvicorn main:app --host 0.0.0.0 --port 3000 --reload > "$ROOT_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo "   后端 PID: $BACKEND_PID"

# 等待后端启动（简单等待，不再阻塞在健康检查上）
echo "⏳ 等待后端启动..."
sleep 3
echo "ℹ️  已等待 3 秒，后端可能已启动，如有问题请查看 logs/app.log 和 logs/error.log"

# 启动前端（只启动新版 Vue 前端，8080 端口）
echo "🎨 启动新版前端静态站点 (端口 8080)..."
cd ../frontend-vue

# 安装前端依赖并构建（如已安装/已构建会很快略过）
if [ ! -d "node_modules" ]; then
  echo "📦 安装前端依赖 (npm install)..."
  npm install --silent
fi
echo "🔨 构建 Vue 前端..."
npm run build > "$ROOT_DIR/logs/frontend-vue-build.log" 2>&1

cd dist
nohup python3 -m http.server 8080 --bind 0.0.0.0 > "$ROOT_DIR/logs/frontend-vue.log" 2>&1 &
FRONTEND_VUE_PID=$!
echo "   新版前端 PID: $FRONTEND_VUE_PID (python http.server 8080)"

# 保存 PID
echo "$BACKEND_PID" > "$ROOT_DIR/logs/backend.pid"
echo "$FRONTEND_VUE_PID" > "$ROOT_DIR/logs/frontend-vue.pid"

# 等待前端启动
sleep 2

cd ..

echo ""
echo "✅ 项目启动成功！"
echo ""
echo "🌐 访问地址:"
echo "   新版前端: http://localhost:8080  (Vue SPA 静态站点)"
echo "   远程新版: "
echo "   后端 API: http://localhost:3000"
echo "   后端远程: "
echo "   API 文档: "
echo "   管理后台: "
echo ""
echo "📝 进程信息:"
echo "   后端 PID: $BACKEND_PID"
echo "   前端 PID: $FRONTEND_VUE_PID"
echo ""
echo "📋 查看日志:"
echo "   后端日志: tail -f logs/backend.log"
echo "   前端日志: tail -f logs/frontend-vue.log"
echo ""
echo "🛑 停止服务: ./stop-local.sh"
```

### 4.2 停止脚本 (`stop-local.sh`)

此脚本用于优雅地停止所有相关服务进程。

```bash
#!/bin/bash

# AI SoulMate 本地开发版停止脚本

echo "🛑 停止 AI SoulMate 项目..."
echo ""

cd /home/ubuntu/ai-soul-mate/v0.7.0

# 检查 PID 文件
if [ -f logs/backend.pid ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "🔧 停止后端服务 (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
    else
        echo "⚠️  后端进程已停止"
    fi
    rm logs/backend.pid
fi

if [ -f logs/frontend-vue.pid ]; then
    FRONTEND_VUE_PID=$(cat logs/frontend-vue.pid)
    if ps -p $FRONTEND_VUE_PID > /dev/null 2>&1; then
        echo "🎨 停止新版前端服务 (PID: $FRONTEND_VUE_PID)..."
        kill $FRONTEND_VUE_PID
    else
        echo "⚠️  新版前端进程已停止"
    fi
    rm logs/frontend-vue.pid
fi

# 兜底：清理所有 python http.server 8080 进程（避免遗留）
pkill -f "python3 -m http.server 8080" || true

echo ""
echo "✅ 项目已停止！"
echo ""
echo "📝 查看日志: cat logs/backend.log"
echo "🚀 重新启动: ./start-local.sh"
```

---

## 5. 账号与认证

### 5.1 预设账号
项目初始化时会自动创建以下 22 个账号，**无需注册即可直接使用**。

| 角色 | 用户名 | 密码 | 积分 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| **管理员** | `admin` | `admin123` | 10000 | 拥有所有权限 |
| **开发测试** | `dev` | `dev123` | 5000 | 开发者专用 |
| **普通用户** | `user01` | `user123` | 1000 | 标准用户测试账号 |
| ... | ... | ... | ... | ... |
| **普通用户** | `user20` | `user123` | 1000 | (共20个测试号) |

### 5.2 登录方式
1.  **账号密码登录**: 最常用的方式，直接使用上述预设账号。
2.  **验证码登录**: 支持手机/邮箱验证码（开发模式下验证码会直接显示在响应或日志中）。未注册的账号/手机号/邮箱在登录时会返回「该账号尚未完成注册」，需先走注册流程，不再自动建号登录。
3.  **第三方登录**: 支持 GitHub 和 微信登录（测试模式）。
4.  **登录/注册弹窗与界面语言（Vue i18n）**：`locale === 'zh-CN'` 时登录与注册方式 Tab 为 **手机 → 邮箱 → 账号**（默认手机），账号注册可选填绑定手机；`en-US` 时 **隐藏手机号**相关 Tab 与选填手机，仅 **邮箱 → 账号**（默认邮箱）。实现：`frontend-vue/src/components/AuthModal.vue`。

5.  **用户协议必选勾选（Vue）**：主弹窗内**不**默认展示协议细则；在每种登录/注册方式的**验证码（或图形验证码）与主提交按钮之间**展示勾选行，文案由 `authModal.termsCheckboxBeforeLink` + 可点击的 `termsLinkText`（默认「用户协议」）+ `termsCheckboxAfterLink` 组成；点击链接触发**叠层弹窗**展示 `termsPlaceholderBody` 全文（中文正文来自 `frontend-vue/src/legal/userAgreementZh.ts`；英文为摘要并提示以中文版为准，`termsModalTitle` 为「用户服务协议」/ `User Service Agreement`）。全文弹窗实现为独立组件 `frontend-vue/src/components/UserAgreementModal.vue`，`AuthModal.vue` 与首页 `HomePage.vue`（页脚「合规与协议」→「用户协议」）复用同一组件，保证内容与样式一致。未勾选时禁用「发送验证码」、提交与第三方登录，并提示 `authModal.mustAcceptTerms`。关闭认证弹窗或切换「登录 / 注册」Tab 会重置勾选并关闭协议层。

6.  **前端 Token 生命周期（Vue）**：**无操作 15 分钟**后前端自动登出（全局 `pointerdown` / `keydown` / `click` / `wheel` 捕获阶段、切回标签页 `visibilitychange`，以及 `router.afterEach` 切页视为有操作并重置空闲倒计时）。有活动时另经 **节流**（默认约 30 秒至多一次）调用 `GET /api/auth/session/touch`，刷新 Redis 滑动会话 TTL，与后端「无操作窗口」对齐。JWT 由后端 `ACCESS_TOKEN_EXPIRE_MINUTES` 决定**绝对最长有效期**（默认 1440 分钟即 24 小时），前端另设定时器在 `exp` 到达时兜底登出，避免 JWT 仍有效但策略不一致。接口返回 401 时清除 `auth_token` 并通过 `setOnUnauthorized` 回调登出。若在需登录路由上变为未登录，会跳转首页并带 `?login=1`。实现位置：`frontend-vue/src/lib/storage.ts`（`getTokenExpMs`）、`frontend-vue/src/lib/api.ts`（`setOnUnauthorized`、`api.auth.sessionTouch`）、`frontend-vue/src/stores/auth.ts`（`_resetIdleLogoutTimer`、`_scheduleJwtExpiryLogout`、`touchSessionActivity`、`installSessionActivityListeners`）、`frontend-vue/src/main.ts`（`afterEach` + 注册监听）、`frontend-vue/src/App.vue`（`isAuthed` 监听）。

### 5.3 无操作会话（后端与前端对齐）

* **目标**：与前端「无操作 15 分钟登出」一致，在 **Redis 可用** 时，受保护 API 也拒绝已超过空闲窗口的 JWT（键已过期或显式登出已删键），避免仅靠前端清状态、后端仍认 token 的情况。
* **机制**：用户 ID 对应 Redis 键 `session:idle:{user_id}`，值为占位，`TTL = SESSION_IDLE_SECONDS`（默认 `900`，与前端 `IDLE_LOGOUT_MS` 一致，可通过环境变量覆盖）。任意 **签发用户 JWT** 的成功路径（注册、登录、GitHub/微信登录、`/api/admin/login`、`/api/auth/admin/login` 等）会 `SET` 该键并刷新 TTL；依赖 `get_current_user` 的接口在 JWT 校验通过后：若 Redis 已连接且键 **不存在** → **401**（文案含「长时间无操作」）；若存在 → **刷新 TTL**（滑动窗口）。另提供 **`GET /api/auth/session/touch`**（依赖 `get_current_user`），仅用于在用户仅有前端交互、短时间未调用其它业务 API 时刷新滑动 TTL，与前端节流配合。`get_current_user_optional`：带 Bearer 时若键不存在则视为未登录（返回 `None`），存在则刷新 TTL。
* **降级**：Redis **未连接**时不做上述校验，行为与改造前一致（仅 JWT `exp` 约束）。
* **显式登出**：`POST /api/auth/logout`，可选 `Authorization: Bearer`；若 token 可解析则删除对应 `session:idle:{sub}`。前端 `auth.logout()` 会先调用 `api.auth.logoutServer()`（独立 `fetch`，避免走通用 `request` 的 401 回调链），再清除本地 token。
* **实现文件**：`backend/core/session_idle.py`、`backend/config.py`（`SESSION_IDLE_SECONDS`）、`backend/api/dependencies.py`、`backend/api/auth.py`、`backend/api/admin.py`；前端 `frontend-vue/src/lib/api.ts`、`frontend-vue/src/stores/auth.ts`。
* **部署注意**：上线后**已持有旧 JWT、但从未写入滑动键**的会话，首次打受保护接口会得到 401，需重新登录一次。

### 5.4 GitHub 身份标识一致性与个人中心绑定列表

* **问题背景**：账号登录后绑定 GitHub，再用 GitHub 登录应为**同一 `users` 行**，个人中心 `GET /api/auth/identities` 应列出全部绑定。若各入口对 GitHub `/user` 的 `id` 处理不一致（或开发占位符不一致），会写入不同 `user_identities.identifier`，导致登录命中「另一用户」或前端未及时重拉列表，表现为「单向」或缺绑定。
* **后端**：`backend/api/auth.py` 使用 `_github_oauth_identifier_from_api` 将 GitHub 返回的 `id` **统一为十进制字符串**；OAuth 失败/无真实 id 时占位符由 **`Config.DEV_GITHUB_OAUTH_IDENTITY`**（环境变量同名，默认 `dev_github_local_oauth_user`）提供，**绑定与 GitHub 登录共用同一串**——若曾用「每次 `code` 前 12 位」生成占位，则两次 OAuth 的 code 不同会写入两行身份、换登录方式后像新账号。换票时传入 **`redirect_uri`**；`_lookup_user_id_by_github_identifier` 用于解析已绑定用户。
* **前端**：`auth` store 派发 `auth-session-changed` 且 `ProfilePage` **watch `auth.token`**；`frontend-vue/src/lib/githubOAuth.ts` 在跳转 GitHub 前从授权 URL 解析并 **localStorage 暂存 `redirect_uri`**，回调换票时优先使用，与后端 `redirect_uri` 对齐。
* **升级注意**：若库里已有 `provider=github` 且 `identifier` 形如 `dev_github_` + 随机片段的旧数据，部署本规则后请在测试环境 **重新绑定一次 GitHub**，或将占位行统一改为当前 `DEV_GITHUB_OAUTH_IDENTITY`（注意避免多用户冲突）。
* **禁止「假绑定」分裂用户**：当 **已配置** `GITHUB_CLIENT_ID` + `GITHUB_CLIENT_SECRET` 时，`POST /api/auth/bind-github` 若换票失败或无法解析 `/user` 的 `id`，返回 **400** 且**不写入**占位 `identifier`（历史上静默写入会导致账号端显示 `dev_***`、GitHub 登录却命中真实数字 id 的另一用户）。注册流程中带 `github_code` 时同理；`POST /api/auth/github-login` 在已配置 OAuth 时遇异常不再回退开发占位登录。
* **合并逻辑（占位 GitHub + 真实 GitHub）**：`_merge_other_user_into_current` 在删除「对方」与当前冲突的 provider 之前，若双方均有 `provider=github` 且 `identifier` 不同，先将当前用户的 GitHub 行更新为对方的真实 id；若合并后对方已无身份行，仍执行积分合并并删除对方用户，避免「删掉真实 GitHub 行后提前 return」导致账号仍显示占位且两用户并存。
* **前端换票只发起一次**：回调页带 `bind=github` 时，**仅** `App.vue` 的 `onMounted` 应调用 `POST /api/auth/bind-github`；`ProfilePage.vue` 若再调用会与 App 并发两次换票，`githubOAuth.ts` 中 `takeGithubOAuthRedirectUri()` 消费后第二次缺少与授权一致的 `redirect_uri`，表现为换票失败。
* **OAuth state 与多标签**：同页「GitHub 登录」的 `state`（及 redirect stash）应使用 **sessionStorage**，避免与其它标签页或个人中心绑定流程写入的 **localStorage** 互相覆盖导致回调校验失败、用户回到首页却未登录且无提示。
* **绑定回调读 storage 顺序**：`bind=github` 的回调多在 **popup** 内执行，`readGithubOAuthState` / `takeGithubOAuthRedirectUri` 须 **优先 localStorage**（opener 写入）；若仍优先 sessionStorage，popup 内残留会话数据会导致 state 与 URL 不一致，表现为与登录相同的「校验失败」。

7.  **顶栏用户菜单收起（Vue）**：登录后顶部「菜单」展开的下拉，在**点击菜单区域外**（含主内容区、顶栏其它按钮等）时自动收起；**路由切换**时也会收起，避免残留展开态。实现：`frontend-vue/src/App.vue` 中对 `menuOpen` 的监听，在 `document` 上以捕获阶段注册 `click`，并用 `queueMicrotask` 延后注册，避免用户点击菜单按钮打开时同一次点击立刻触发「外部点击」而误关。登出或 `isAuthed` 变为 false 时会关闭菜单并移除监听。**已登录菜单触发按钮**使用 `frontend-vue/public/images/user-menu-icon.png`（线稿人像、透明底），以 **CSS mask-image** 叠 `background-color` 显示为浅色线稿（避免对透明 PNG 使用 `filter` 导致整格变白块）。

8.  **登录/注册图形验证码不串页（Vue）**：手机/邮箱发码前的图形验证码在登录与注册间共用状态；切换登录方式（手机 ↔ 邮箱）、从注册回到登录、从账号登录切到手机/邮箱时，会重新拉取图形验证码并清空已填内容，避免旧输入与新图不一致。**发码成功**后不再自动刷新图形验证码与输入框；仅在发码接口返回图形验证码相关错误时再 `fetchSendCodeCaptcha()`（见 `shouldRefreshSendCodeCaptchaAfterError`）。实现：`frontend-vue/src/components/AuthModal.vue` 中 `watch` 与 `sendPhoneCode` / `sendEmailCode`。

---

## 6. 产品功能特性

### 6.1 核心功能模块
1.  **造梦工作室 (Studio)**
    *   **文生3D**: 输入提示词（如“一只可爱的皮卡丘”），选择风格（Q版/机甲等），消耗积分生成3D模型。
    *   **图生3D**: 上传图片生成对应的3D模型。
    *   **提示词/上传合规悬浮提示（前端）**：在文生图/文生3D 的「提示词」、图生3D 的「上传图片」、本地预览的「上传3D模型」标签旁新增 hover 提示（`title`），提炼展示平台对明显侵权/违法内容的审查与侵权通知处理义务，以及用户对输入/输出侵权行为自担责任的边界说明。实现：`frontend-vue/src/views/StudioPage.vue`；文案：`frontend-vue/src/locales/index.ts` 的 `studio.complianceHover`（中英）。
    *   **提示词编辑锁定（前端）**：文生图在同步生成请求进行中、文生3D在右侧为「加载中」视图期间（含异步任务轮询至完成），提示词输入为只读，翻译/AI 优化按钮禁用；避免用户误以为修改提示词会影响已提交任务。文生3D/图转3D 提交失败时将视图重置为 `empty`，避免长期卡在 loading。实现：`frontend-vue/src/views/StudioPage.vue`（`promptInputLocked`）。
2.  **IP社区 (Community)**
    *   浏览他人分享的作品，支持点赞、下载、Fork（二创）。
3.  **硬件商城 (Market)**
    *   购买3D打印机、智能底座、耗材等。支持购物车和模拟支付流程。
4.  **课程中心 (Courses)**
    *   提供 L1/L2/L3 分级课程，支持项目制学习 (PBL)。
5.  **教师工作台**
    *   可视化搭建 AI 工作流（类似 ComfyUI），管理班级和学生作品。
6.  **首页页脚（前端）**
    *   首页底部为多栏布局：关于我们（公司简介摘要）、探索平台（造梦 / 社区 / 商城）、合规与协议（「用户协议」点击打开 `UserAgreementModal`，与登录弹窗内协议全文一致）、联系我们（含「投诉与维权」悬停展示邮箱 `williamsyx@foxmail.com`、手机 `13436419828`）。
    *   底栏展示版权与备案号「京ICP备2026012143号」（链至工信部备案查询站）。
    *   实现：`frontend-vue/src/views/HomePage.vue`；文案：`frontend-vue/src/locales/index.ts` 的 `home.footer.*` 与 `home.complaint.*`（中英）。

### 6.2 数据模型简述
*   **Users**: 用户信息、积分、角色。
*   **Assets**: 用户生成的3D资产数据。
*   **Orders**: 商城订单。
*   **Workflows**: 教师创建的教学工作流数据。

### 6.3 Studio 3D 接入更新（近期）
以下为当前已落地的 Studio 3D 接入行为：

0.  **fix-print 合并：输出格式与打印入口（2026-3-28）**
    *   **API / Schema**：`StudioGenerate`、`StudioImageTo3D` 的 `result_format` 约定为 **GLB 或 STL**（`backend/schemas/asset.py`）；前端 `api.ts` 类型同步。
    *   **造梦页**：文生/图生下拉仅 GLB（不可打印）与 STL（可打印）；图生 `buildImage3DParamsPayload` 始终传 `result_format`。**文生3D**：选 STL（可打印）时前端「彩色带纹理」禁用（仅白色几何体）。**图生3D**：选 STL 时生成类型仅三种白模（AUTO/LOWPOLY/SKETCH 的 *_WHITE），彩色选项禁用。`StudioPage.vue` + `studio.text23d.*` / `studio.image23d.*`。
    *   **一键下单**：仅当结果模型链接扩展名为 **stl** 时展示（与积分侧「STL 加价」一致）。
    *   **后端**：`backend/services/hunyuan3d.py` 为 fix-print 版简化降级；`backend/main.py` 保留 master 上图生3D 的 `source_ref` / `reference_image_url` / `_complete_studio_job_if_done` 事务与历史写入，并合并 fix-print 的 `_normalize_single_file_studio_history_params`、`_resolve_studio_model_links`、`_extract_gcode_source_from_status_result`（stl→obj→amf）等辅助逻辑。

1.  **图生3D参数展示修复**
    *   图生3D接口逻辑为“仅图片输入”（提示词不作为必填输入）。
    *   页面底部在图生3D模式下显示为 `图片：` + 输入图的小图预览，不再错误显示全局提示词文案。
    *   `prompt` 仍保留为页面全局状态，文生图/文生3D可继续使用。

2.  **3D API 打通**
    *   文生3D、图生3D均已可调用后端接口并返回有效结果。
    *   页面先使用接口返回的 `preview_url` 做结果预览占位。
    *   页面保留 `查看模型链接` 按钮，可直达/下载真实 `model_url`，用于后续前端渲染链路验证。

3.  **3D结果区接入 EmbeddedViewer**
    *   Studio 3D 结果区已接入 `EmbeddedViewer`，使用 `model_url` 进行可交互渲染（旋转/缩放/查看）。
    *   原有流程和按钮保持不变：生成、发布、打印、查看模型链接均可继续使用。
    *   当模型渲染失败时，自动回退到 `preview_url` 图片并给出错误提示。
    *   页面卸载或模式切换时会销毁 viewer 实例，避免内存泄漏和重复挂载。

4.  **模型代理（解决第三方存储 CORS）**
    *   新增后端代理接口：`GET /api/studio/model-proxy`（及带文件名路由）。
    *   前端 viewer 通过代理地址加载模型，避免浏览器直接请求 COS 时的 CORS 拦截。
5.  **本地上传文件预览**
    *   Studio 顶部新增“本地预览”栏位，支持直接加载本地3D文件并进行交互预览。
    *   支持多文件组合加载（如 OBJ + MTL + 贴图），并在加载失败/超时时返回明确提示，便于用户快速重试。
    *   本地预览为前端侧加载流程，不消耗生成积分，也不触发在线生成任务。

### 6.4 免费积分双轨与个人中心刷新提示

#### 6.4.1 双轨积分规则简述

- **免费积分**：新用户初始 **60**；当本轮**首次使用免费积分**时开始 24 小时计时（写入 `free_points_refreshed_at`），满 24 小时后若免费积分未满 60 则自动刷新为 **60**。刷新后会将 `free_points_refreshed_at` 置空，等待下一轮首次使用再重新计时。常量在 `backend/core/points.py` 的 `FREE_POINTS_REFRESH_AMOUNT`。
- **计时锚点修复**：若 `0 < free_points < 60` 且 `free_points_refreshed_at IS NULL`（历史迁移或异常路径未写入锚点），`maybe_refresh_free_points` 会补写 `free_points_refreshed_at = now()`，使个人中心能展示 24h 倒计时；无法还原真实首扣时刻，仅避免「永不显示倒计时」。
- **付费积分**：充值订单中「实付对应」的基础积分（`amount`），不刷新。
- **赠送积分**：充值活动赠送部分（`credit_recharges.bonus_amount`），入账到 `users.gift_points`，在个人中心与付费积分分列展示；合并账号时累加对方的 `gift_points`。解绑身份时仍按 `free_contributed` / `paid_contributed` 拆分，赠送积分留在主账号（不按身份行拆分）。
- **扣费顺序**：先扣免费（不足则先扣光免费积分），再扣赠送，最后扣付费（`deduct_points` 与 `main.py` 内 `_deduct_points_in_tx` 一致）。

#### 6.4.2 个人中心「免费积分」悬停提示功能

- **位置**：个人中心基础信息中「免费积分（说明）」整格。
- **触发**：鼠标移入该格时显示小弹框，移出后隐藏。
- **弹框内容**：
  1. **规则**：强调从**第一次消耗免费积分**的时刻起算 **24 小时**（不是「先等满 24 小时再开始另一段倒计时」）；满 24 小时后若仍不足 60 则恢复为 60，计时点清空。
  2. **倒计时**：当 `free_points_refreshed_at` 已写入且当前免费积分 **&lt; 60** 时，显示本轮终点时间与大约剩余小时/分钟；已到期则提示下次拉取用户信息时会刷新。

#### 6.4.3 后端实现要点

- **依赖与接口**：
  - `backend/core/points.py`：`maybe_refresh_free_points`、`deduct_points`、`total_points`。
  - `backend/api/dependencies.py`：`get_current_user` 查询用户时带上 `free_points`、`paid_points`、`gift_points`、`free_points_refreshed_at`，并在满足条件时调用 `maybe_refresh_free_points`；返回给前端的用户对象中增加 `free_points_refreshed_at`（ISO 字符串，无则 `None`）及 `gift_credits`（由 `gift_points` 映射）。刷新后再次查询用户时 SELECT 中同样包含上述列。
  - `backend/main.py`：`GET /api/user/profile` 的返回体中包含 `free_credits`、`paid_credits`、`gift_credits`、`free_points_refreshed_at`。
  - `backend/api/auth.py`：`_user_response` 含 `gift_credits`；`free_points_refreshed_at` 从 user_row 取并转 ISO。所有返回完整用户信息的 SELECT（登录、注册、绑定等）均包含 `gift_points`、`free_points_refreshed_at`。

- **数据库**：`users` 表字段 `free_points`、`paid_points`、`gift_points`、`free_points_refreshed_at`（启动时在 `main.py` 的 `init_database` 中做迁移）。

#### 6.4.4 前端实现要点

- **类型与接口**（`frontend-vue/src/lib/api.ts`）：
  - `UserInfo` 增加 `free_points_refreshed_at?: string | null`、`gift_credits?: number`。
  - `api.user.getProfile()` 的返回类型增加 `free_credits`、`paid_credits`、`gift_credits`、`free_points_refreshed_at`。

- **个人中心**（`frontend-vue/src/views/ProfilePage.vue`）：
  - 进入页面时在 `onMounted` 中调用 `api.user.getProfile()`，将返回结果与当前 `auth.user` 合并并写回，保证展示与弹框使用到最新的 `free_points_refreshed_at` 和积分。
  - **「积分查看」独立区块**：标题与「显示名称设置」「已绑定账号」「绑定与解绑」同级（`text-sm font-medium`）；内含免费 / 赠送 / 付费三栏布局（左列免费+赠送、右列付费+充值按钮，`md` 及以上两列栅格），其下为 `profile.creditsNote` 说明。文案键：`profile.creditsSection.title` / `desc`。
  - 「免费积分（说明）」所在格为 `relative` 容器，整格绑定 `@mouseenter` / `@mouseleave` 控制弹框显隐。
  - 弹框为绝对定位小框：规则说明 + 当 `free_points_refreshed_at != null` 且免费积分 &lt; 60 时，用 `free_points_refreshed_at + 24h` 显示本轮终点与剩余时间文案。文案键：`profile.freeCreditsRules.title` / `body` / `countdown.*`（`zh-CN` 与 `en-US` 各一套，随顶栏语言切换）。

#### 6.4.5 Studio / 打印积分校验

- **积分校验统一**：文生图、文生3D、图转3D、打印等接口的「至少需要 10 积分」校验，以及 `GET /api/user/profile` 返回的 `credits`，均使用 `total_points(current_user)`（即 **免费 + 付费 + 赠送**），不再单独用 `current_user.get('credits', 0)`，避免未正确汇总时误报「积分不足」。实现位置：`backend/main.py` 引入 `total_points`，相关判断与 profile 的 `credits` 字段改为 `total_points(current_user)`。

### 6.5 造梦历史与侧边栏

- **表**：`studio_history`（id, user_id, mode, prompt, params, preview_url, asset_id, created_at）；每用户最多 500 条，超出自动删最旧。建库语句见 `README.md` 中「数据库建库语句变化」。
- **写入时机**：文生图/文生3D（`/api/studio/generate`）、图生3D（`/api/studio/image-to-3d`）成功写入 asset 后插入一条；异步任务（`/api/studio/submit-text-3d`、`/api/studio/submit-image-3d`）在 **`_complete_studio_job_if_done`** 中写入 asset 与 `studio_jobs` 后同样调用 **`_insert_studio_history`**（此前遗漏会导致侧栏任务结束后历史列表无记录）。
- **接口**：`GET /api/studio/history`（分页，需登录）、`DELETE /api/studio/history/:id`（仅本人可删）；造梦相关接口均需 Token 校验。历史列表对 **`mode=image23d`** 的 **`prompt`** 会优先用 **`params`（generation_params / with_texture）** 重算参数摘要（与侧栏进行中一致），避免库内 `prompt` 为空时前端只能显示「参考图」。
- **前端**：造梦页左侧可折叠侧边栏展示历史（类型标签 + 缩略图 + 短 prompt + 时间 + 删除）；点击某条弹出层显示完整参数与预览图。未登录时造梦主内容区显示「请先登录」。结果页 **发布到社区** 成功后自动跳转 **`/community`**（`StudioPage.vue` 的 `publishToCommunity`）。
- **异步 3D 进度条一致**：进行中任务的 **`transient_progress`** 由侧栏定时器与轮询共同维护；右侧「加载中」预览区在绑定 **`selectedTransientJobId`** 时，进度百分比与条宽直接读取该侧栏项的 **`transient_progress`**（`unifiedAsyncJobProgress`），避免与左侧双轨计算不一致。
- **历史条「多久以前」语义**：侧栏中 **进行中** 的异步任务不显示相对提交时间的「X 分钟前」，而显示与状态一致的「生成中」类文案；**已结束** 的临时条目优先用任务详情里的 **`finished_at`** 作为锚点。已从服务端拉取的 **`studio_history`** 行：其 `created_at` 在插入时已对应成功落库时刻，相对时间仍以该字段为准（`StudioPage.vue`：`historyRelativeTimeLabel`、`formatElapsedSince`，文案键 `studio.timeAgo` / `studio.transientStatus.processing`）。
- **图生3D（image23d）展示与封面**：`studio_history.prompt` 与 **`assets.prompt`** 写入 **用户侧参数摘要**（由 `Model` / `GenerateType` / 彩白模 / 面数 / PBR / 输出格式等拼接），不再依赖易被误读的占位或上游文案；**`assets.image_url`** 与历史 **`preview_url`** 优先使用提交时上传并落 OSS 的 **参考原图**，便于社区列表/详情与左侧缩略图识别「我传的是哪张图」；若存在 3D 结果预览，可记在 **`params.generated_preview_url`**。`POST /api/studio/submit-image-3d` 返回 **`display_prompt`**；`GET /api/studio/sidebar-jobs`、`GET /api/studio/job/{job_id}`、**`GET /api/studio/job-notifications`** 对图生3D 的 **`prompt`** 字段与摘要一致。实现：`backend/utils/studio_display.py`（`format_hunyuan_image23d_display_prompt` 等）、`backend/main.py` 中 `_studio_job_api_display_prompt` 及相关写入路径。
- **社区接口补全**：`GET /api/assets`（列表）与 **`GET /api/assets/{asset_id}`**（详情）在能关联到 **`studio_history`**（同 `asset_id`、取最新一条）且 `mode=image23d` 时，用历史 **`params`** 再次生成上述摘要并覆盖响应中的 **`prompt`**，保证发布后社区卡片与「生成提示词」区域一致展示图生3D 配置（不依赖 `assets.prompt` 是否曾被旧逻辑写空）。实现：`backend/api/assets.py` 调用 `utils.studio_display.prompt_from_studio_history_row`。
- **图生3D 参考图**：详情接口在上述条件下额外返回 **`studio_mode`: `"image23d"`** 与 **`reference_image_url`**（优先对历史 **`preview_url`**（原图 OSS）做预签名，否则回退 **`assets.image_url`**），供前端在「生成提示词」区块内展示用户上传的参考照片。

### 6.6 积分充值系统（2026-2-24）

#### 6.6.1 充值功能概述

积分充值系统允许用户通过在线支付购买积分，支持"充多送多"机制，鼓励用户充值更多。

**核心特点**：
- 5档固定充值档位，不支持自定义金额
- 充值档位可后台配置，包括充值金额、赠送比例、描述等
- 充值成功后：`paid_points += amount`（实付对应积分），`gift_points += bonus_amount`（赠送积分）；支付宝异步通知与内部 `recharge_callback`（`backend/api/credits.py`）逻辑一致
- 充值订单与商品订单统一管理，但类型不同

#### 6.6.2 充值档位配置

**默认充值档位**（存储在 `recharge_tiers` 表）：

| 档位 | 充值积分 | 赠送比例 | 赠送积分 | 实际到账 | 价格（元） |
|------|----------|----------|----------|----------|-----------|
| 1档 | 100 | 0% | 0 | 100 | 10.00 |
| 2档 | 500 | 5% | 25 | 525 | 50.00 |
| 3档 | 1000 | 10% | 100 | 1100 | 100.00 |
| 4档 | 5000 | 15% | 750 | 5750 | 500.00 |
| 5档 | 10000 | 20% | 2000 | 12000 | 1000.00 |

**充值档位表结构**（`recharge_tiers`）：
```sql
CREATE TABLE IF NOT EXISTS recharge_tiers (
    id SERIAL PRIMARY KEY,
    min_amount INTEGER NOT NULL,           -- 充值基础积分
    bonus_rate DECIMAL(5, 2) NOT NULL DEFAULT 0,  -- 赠送比例（百分比）
    bonus_fixed INTEGER DEFAULT 0,         -- 固定赠送积分（暂未使用）
    description VARCHAR(255),              -- 档位描述
    is_active BOOLEAN DEFAULT TRUE,        -- 是否启用
    sort_order INTEGER DEFAULT 0,          -- 排序
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**配置说明**：
- 充值档位可通过数据库直接修改 `recharge_tiers` 表
- 修改档位后无需重启服务，前端会自动获取最新配置
- 赠送比例以百分比形式存储（如 10.00 表示赠送10%）
- 实际赠送积分 = 充值积分 × 赠送比例

**如何修改充值档位**：

1. **修改积分与金额的兑换比例**：
   - 打开 `backend/api/credits.py` 文件
   - 找到 `get_recharge_tiers` 函数中的 `CREDIT_TO_YUAN_RATE` 常量
   - 修改该值即可（默认 0.1，即 10积分=1元）
   - 示例：改为 0.01 则变成 100积分=1元

2. **修改充值档位的赠送比例**：
   - 方式一：直接修改数据库
     ```sql
     -- 修改1000积分档位的赠送比例为15%
     UPDATE recharge_tiers 
     SET bonus_rate = 15.00 
     WHERE min_amount = 1000;
     ```
   - 方式二：修改初始化SQL文件（仅对新部署生效）
     - 编辑 `backend/migrations/005_add_recharge_tiers.sql`
     - 修改 INSERT 语句中的 bonus_rate 值

3. **添加新的充值档位**：
   ```sql
   INSERT INTO recharge_tiers (min_amount, bonus_rate, bonus_fixed, description, sort_order) 
   VALUES (2000, 12, 0, '充值2000积分，赠送12%', 6);
   ```

4. **禁用某个档位**：
   ```sql
   UPDATE recharge_tiers 
   SET is_active = FALSE 
   WHERE min_amount = 100;
   ```

**注意事项**：
- 修改数据库后，前端会立即生效，无需重启服务
- 积分兑换比例修改后，前端会自动根据后端返回的数据计算显示金额
- 建议在测试环境先验证修改效果，再应用到生产环境

#### 6.6.3 充值订单表

**充值订单表结构**（`credit_recharges`）：
```sql
CREATE TABLE IF NOT EXISTS credit_recharges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,               -- 充值基础积分
    bonus_amount INTEGER DEFAULT 0,        -- 赠送积分
    total_amount INTEGER NOT NULL,         -- 总积分（充值+赠送）
    amount_yuan DECIMAL(10, 2) NOT NULL,   -- 支付金额（元）
    payment_method VARCHAR(50) NOT NULL,   -- 支付方式
    payment_id VARCHAR(255),               -- 支付平台订单号
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- 订单状态
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    paid_at TIMESTAMP WITH TIME ZONE       -- 支付完成时间
);
```

**订单状态**：
- `pending`：待支付（创建订单后的初始状态）
- `paid`：已支付（支付成功后）
- `failed`：支付失败
- `cancelled`：已取消

#### 6.6.4 充值相关接口

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/credits/recharge-tiers` | 获取充值档位列表 | 需登录 |
| POST | `/api/credits/recharge` | 创建充值订单 | 需登录 |
| GET | `/api/credits/recharge-history` | 获取充值历史 | 需登录 |

**创建充值订单请求体**：
```json
{
  "tier_id": 3,                    // 充值档位ID
  "payment_method": "alipay"       // 支付方式
}
```

**返回数据**：
```json
{
  "recharge_id": "uuid",
  "amount": 1000,
  "bonus_amount": 100,
  "total_amount": 1100,
  "amount_yuan": 100.00,
  "payment_url": "https://..."     // 支付跳转URL
}
```

#### 6.6.5 充值流程

1. **用户打开充值弹窗**：个人中心点击"充值"按钮，弹出充值档位选择
2. **选择档位和支付方式**：显示5个档位按钮，格式为"充值+赠送"（如：1000+100 积分）
3. **创建充值订单**：调用 `/api/credits/recharge` 接口，后端创建充值订单记录
4. **跳转支付**：前端跳转到支付平台（如支付宝）完成支付
5. **支付回调**：支付平台异步通知后端，后端验证签名后：
   - 更新充值订单状态为 `paid`
   - 增加用户 `paid_points`（使用 `total_amount`，包含赠送）
   - 记录 `paid_at` 时间
6. **返回个人中心**：支付完成后跳转回个人中心，显示充值成功提示

#### 6.6.6 支付回调处理

**支付回调统一处理**（`backend/api/payments.py`）：
```python
# 支付宝异步通知
@router.post("/alipay/notify")
async def alipay_notify(request: Request):
    # 1. 验证签名
    # 2. 获取订单号（out_trade_no）
    # 3. 判断订单类型：
    #    - 如果是充值订单（recharge_开头）：
    #      a. 更新 credit_recharges 表状态
    #      b. 增加用户 paid_points
    #    - 如果是商品订单：
    #      a. 更新 orders 表状态
    # 4. 返回 "success"
```

**订单号格式**：
- 商品订单：直接使用订单UUID
- 充值订单：`recharge_{充值订单UUID}`（便于区分）

#### 6.6.7 前端组件

**充值弹窗** (`RechargeModal.vue`)：
- 显示5个充值档位按钮，每个按钮显示"充值+赠送"格式
- 支持选择支付方式（支付宝/Stripe）
- 响应式布局：移动端单列，桌面端双列
- 点击充值后跳转到支付页面

**充值回调页面** (`RechargeCallbackPage.vue`)：
- 支付完成后的落地页
- 显示充值结果（成功/失败）
- 3秒后自动跳转到个人中心

**个人中心** (`ProfilePage.vue`)：
- 显示免费积分和付费积分
- 充值按钮打开充值弹窗
- 充值成功后自动刷新积分显示
- 检测URL参数 `recharge_success=1`，显示充值成功提示

#### 6.6.8 数据库迁移文件

**建表SQL文件**：
- `backend/migrations/004_add_credit_recharges_table.sql`：充值订单表及索引（第2-24行）
- `backend/migrations/005_add_recharge_tiers.sql`：充值档位表及索引（第2-18行）

**插入默认数据**：
- `backend/migrations/005_add_recharge_tiers.sql`：插入5档默认充值档位（第21-26行）

**Docker初始化**：
- `backend/main.py` 的 `init_database` 函数中包含相同的建表和插入逻辑

#### 6.6.9 常见问题

**Q: 如何修改充值档位？**
A: 直接修改数据库 `recharge_tiers` 表，修改后无需重启服务。

**Q: 充值订单和商品订单如何区分？**
A: 充值订单的订单号以 `recharge_` 开头，商品订单直接使用UUID。

**Q: 充值失败如何处理？**
A: 支付失败时订单状态保持 `pending`，用户可以重新支付或取消订单。

**Q: 赠送积分如何计算？**
A: 赠送积分 = 充值积分 × 赠送比例，例如充值1000积分，赠送比例10%，则赠送100积分，实际到账1100积分。

---

## 7. 部署与运维

### 7.1 生产环境部署建议
*   **使用 Docker**: 推荐使用 `docker-compose.yml` 进行一键部署。
*   **反向代理**: 使用 Nginx 处理 HTTPS 和静态资源（配置参考 `nginx.conf`，如有）。
*   **持久化**: 确保数据库和上传文件的目录已挂载到宿主机（如 `./data`）。

### 7.2 日志管理
*   **后端日志**: `logs/backend.log`
*   **前端构建日志**: `logs/frontend-vue-build.log`
*   **前端运行日志**: `logs/frontend-vue.log`

---

## 8. 技术文档索引

为了保持 README 的简洁，详细的技术文档请参考 `docs/` 目录下的文件：

*   **API 接口文档**: `docs/API.md` (包含所有端点说明、请求示例)
*   **后端开发指南**: `docs/backend-development-guide.md` (架构、模块说明、开发规范)
*   **前端代码架构**: `docs/frontend-code-organization.md` (前端重构与目录结构)
*   **部署详细指南**: `docs/DEPLOYMENT.md` (详细的服务器配置与环境变量说明)
*   **测试指南**: `docs/testing-guide.md` (前后端测试流程)
*   **发布指南**: `docs/GITHUB-发布指南.md`
*   **重构总结**: `docs/项目重构总结.md` (以及 `docs/frontend-refactoring-summary.md`、`docs/backend-test-report.md`)

---

## 9. 常见问题与故障排除

### 9.1 前端登录无反应 / IP 地址变更
*   **问题**: 点击登录按钮无反应，或请求一直挂起。
*   **原因**: 前端配置中的 API 地址可能硬编码了旧 IP。
*   **修复**: 前端代码已更新为动态获取 API 地址。
    *   **开发环境**: 自动使用相对路径 `/api`（通过 Vite 代理）。
    *   **生产环境**: 自动使用当前访问的域名/IP + 3000 端口。
    *   **操作**: 如果更换了服务器 IP，请运行 `npm run build` 重新构建前端，或重启 Docker 容器。

### 9.2 登录验证码问题
*   **问题**: 提示需要验证码，但界面上不知道在哪看。
*   **修复**: 预设账号登录**不需要**验证码。如果界面提示验证码错误，请确保只输入了用户名和密码。开发模式下，验证码会直接在 API 响应或日志中返回。

### 9.3 数据库连接失败 / 认证错误
*   **问题**: 启动时报错 `bcrypt` 相关错误或数据库连接被拒绝。
*   **修复**:
    *   确保 `requirements.txt` 中使用了 `bcrypt==3.2.2` 和 `PyJWT==2.7.0`。
    *   确保 PostgreSQL 服务已启动并初始化完成（首次启动可能需要几秒钟）。

## 10,数据库设计备份

~~~postgresql
--
-- PostgreSQL database dump
--

\restrict zsqr2f84kKGauyToN23x7SUGekv09mH2lOwkN8gDqDhHmMJmskYyJIArZwEHPgC

-- Dumped from database version 16.11 (Ubuntu 16.11-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.11 (Ubuntu 16.11-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: addresses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.addresses (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    name character varying(50) NOT NULL,
    phone character varying(20) NOT NULL,
    province character varying(50) NOT NULL,
    city character varying(50) NOT NULL,
    district character varying(50) NOT NULL,
    address text NOT NULL,
    is_default boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.addresses OWNER TO postgres;

--
-- Name: assets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.assets (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    author_id uuid,
    image_url text NOT NULL,
    model_url text NOT NULL,
    prompt text NOT NULL,
    base_model character varying(50) NOT NULL,
    seed integer,
    steps integer,
    sampler character varying(50),
    tags jsonb DEFAULT '[]'::jsonb,
    stats jsonb DEFAULT '{"likes": 0, "downloads": 0}'::jsonb,
    is_published boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.assets OWNER TO postgres;

--
-- Name: courses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.courses (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    title character varying(200) NOT NULL,
    description text,
    level character varying(10) NOT NULL,
    price numeric(10,2) NOT NULL,
    duration_hours integer NOT NULL,
    content jsonb,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.courses OWNER TO postgres;

--
-- Name: devices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.devices (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    device_id character varying(100) NOT NULL,
    char_prompt text,
    last_sync_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.devices OWNER TO postgres;

--
-- Name: operation_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.operation_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    admin_id uuid,
    action character varying(50) NOT NULL,
    resource_type character varying(50) NOT NULL,
    resource_id uuid,
    details jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.operation_logs OWNER TO postgres;

--
-- Name: orders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.orders (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    items jsonb NOT NULL,
    total_amount numeric(10,2) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    address_id uuid,
    payment_method character varying(50),
    shipping_address jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.orders OWNER TO postgres;

--
-- Name: print_jobs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.print_jobs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    asset_id uuid,
    status character varying(20) DEFAULT 'pending'::character varying,
    credits_used integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.print_jobs OWNER TO postgres;

--
-- Name: projects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.projects (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    title character varying(200) NOT NULL,
    description text,
    prompt text NOT NULL,
    style_model character varying(50) NOT NULL,
    status character varying(20) DEFAULT 'draft'::character varying,
    model_url text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.projects OWNER TO postgres;

--
-- Name: user_courses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_courses (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    course_id uuid,
    enrolled_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    progress integer DEFAULT 0
);


ALTER TABLE public.user_courses OWNER TO postgres;

--
-- Name: user_model_configs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_model_configs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    name character varying(100) NOT NULL,
    api_endpoint text NOT NULL,
    api_key text,
    auth_type character varying(50) DEFAULT 'api_key'::character varying,
    model_name character varying(100),
    provider character varying(50),
    parameters jsonb DEFAULT '{}'::jsonb,
    is_active boolean DEFAULT true,
    is_default boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.user_model_configs OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    username character varying(50) NOT NULL,
    email character varying(100),
    password_hash character varying(255),
    phone character varying(20),
    credits integer DEFAULT 60,
    avatar text,
    role character varying(20) DEFAULT 'student'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_active boolean DEFAULT true,
    openid character varying(100),
    github_id character varying(100)
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: workflow_executions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.workflow_executions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    workflow_id uuid,
    user_id uuid,
    status character varying(20) DEFAULT 'running'::character varying,
    input_data jsonb,
    output_data jsonb,
    execution_log jsonb,
    error_message text,
    started_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp without time zone
);


ALTER TABLE public.workflow_executions OWNER TO postgres;

--
-- Name: workflows; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.workflows (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    creator_id uuid,
    graph_data jsonb NOT NULL,
    is_published boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    description text,
    version integer DEFAULT 1,
    tags jsonb DEFAULT '[]'::jsonb,
    execution_count integer DEFAULT 0,
    last_executed_at timestamp without time zone
);


ALTER TABLE public.workflows OWNER TO postgres;

--
-- Name: addresses addresses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.addresses
    ADD CONSTRAINT addresses_pkey PRIMARY KEY (id);


--
-- Name: assets assets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT assets_pkey PRIMARY KEY (id);


--
-- Name: courses courses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_pkey PRIMARY KEY (id);


--
-- Name: devices devices_device_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_device_id_key UNIQUE (device_id);


--
-- Name: devices devices_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_pkey PRIMARY KEY (id);


--
-- Name: operation_logs operation_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operation_logs
    ADD CONSTRAINT operation_logs_pkey PRIMARY KEY (id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: print_jobs print_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.print_jobs
    ADD CONSTRAINT print_jobs_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: user_courses user_courses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_courses
    ADD CONSTRAINT user_courses_pkey PRIMARY KEY (id);


--
-- Name: user_courses user_courses_user_id_course_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_courses
    ADD CONSTRAINT user_courses_user_id_course_id_key UNIQUE (user_id, course_id);


--
-- Name: user_model_configs user_model_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_model_configs
    ADD CONSTRAINT user_model_configs_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_github_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_github_id_key UNIQUE (github_id);


--
-- Name: users users_openid_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_openid_key UNIQUE (openid);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: workflow_executions workflow_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflow_executions
    ADD CONSTRAINT workflow_executions_pkey PRIMARY KEY (id);


--
-- Name: workflows workflows_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflows
    ADD CONSTRAINT workflows_pkey PRIMARY KEY (id);


--
-- Name: idx_assets_author; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_assets_author ON public.assets USING btree (author_id);


--
-- Name: idx_assets_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_assets_created ON public.assets USING btree (created_at);


--
-- Name: idx_assets_published; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_assets_published ON public.assets USING btree (is_published);


--
-- Name: idx_user_model_configs_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_model_configs_active ON public.user_model_configs USING btree (user_id, is_active);


--
-- Name: idx_user_model_configs_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_model_configs_user ON public.user_model_configs USING btree (user_id);


--
-- Name: idx_workflow_executions_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_workflow_executions_user ON public.workflow_executions USING btree (user_id);


--
-- Name: idx_workflow_executions_workflow; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_workflow_executions_workflow ON public.workflow_executions USING btree (workflow_id);


--
-- Name: addresses addresses_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.addresses
    ADD CONSTRAINT addresses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: assets assets_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT assets_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.users(id);


--
-- Name: devices devices_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: operation_logs operation_logs_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operation_logs
    ADD CONSTRAINT operation_logs_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public.users(id);


--
-- Name: orders orders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: print_jobs print_jobs_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.print_jobs
    ADD CONSTRAINT print_jobs_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id);


--
-- Name: print_jobs print_jobs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.print_jobs
    ADD CONSTRAINT print_jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: projects projects_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_courses user_courses_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_courses
    ADD CONSTRAINT user_courses_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id);


--
-- Name: user_courses user_courses_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_courses
    ADD CONSTRAINT user_courses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_model_configs user_model_configs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_model_configs
    ADD CONSTRAINT user_model_configs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: workflow_executions workflow_executions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflow_executions
    ADD CONSTRAINT workflow_executions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: workflow_executions workflow_executions_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflow_executions
    ADD CONSTRAINT workflow_executions_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.workflows(id) ON DELETE CASCADE;


--
-- Name: workflows workflows_creator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workflows
    ADD CONSTRAINT workflows_creator_id_fkey FOREIGN KEY (creator_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

\unrestrict zsqr2f84kKGauyToN23x7SUGekv09mH2lOwkN8gDqDhHmMJmskYyJIArZwEHPgC


~~~



# 项目更新详细文档

## 一、认证与登录

### 1.1 图形验证码（账号登录）

- **功能**：账号密码登录前必须正确输入右侧 6 位图形验证码；点击图片可刷新。
- **流程**：前端请求 `GET /api/auth/captcha` 获取图片与 `captcha_id`；登录时提交 `username`、`password`、`login_code`、`captcha_id`；后端先校验验证码再校验密码。验证码一次性使用，校验后即失效。
- **前端刷新**：每次打开登录弹窗且为账号登录时、以及从手机/邮箱切回账号登录时，均会请求新验证码；避免退出再登录时界面仍显示旧图而后端已失效导致「验证码错误」。
- **安全**：连续 5 次失败按 IP 锁定 15 分钟；失败时提示「图形验证码错误，还有 X 次机会」，锁定后提示「请15分钟后再试」。发送手机/邮箱验证码前也需先通过图形验证码。
- **存储**：优先 Redis（key `captcha:{captcha_id}`），否则内存；失败次数与锁定用 `captcha_fail:{ip}`。
- **依赖**：后端需 Pillow 生成图片；字符集去除易混淆字符（0/O、1/l 等）。

### 1.2 账号 / 手机 / 邮箱登录（含一次性 token）

- **流程**：所有会签发 JWT 的登录方式均采用「先拿一次性 token（OTT）、再提交验证」；验证成功返回用户 JWT，验证失败返回**新的** OTT（便于前端重试，且不泄露 JWT）。
- **账号登录**：第一步 `POST /api/auth/login/account-request` 传 `username`、`captcha_id`、`captcha_code`，通过图形验证后返回 `one_time_token`；第二步 `POST /api/auth/login` 传 `username`、`password`、`one_time_token`。成功→用户 JWT；失败→401 且 body 含新 `one_time_token`。
- **账号密码安全等级**：账号密码登录会校验密码安全等级，要求密码至少 6 位，且至少包含两类字符（大写/小写/数字/符号）；不满足返回 400 与明确提示文案。
- **手机登录**：`POST /api/auth/send-code` 发短信后返回 `one_time_token`；`POST /api/auth/login` 传 `phone`、`phone_code`、`one_time_token`。仅已注册手机号可登录；未注册返回 401 与「该账号尚未完成注册」（并返回新 `one_time_token`）。
- **邮箱登录**：`POST /api/auth/send-email-code` 发邮件后返回 `one_time_token`；`POST /api/auth/login` 传 `email`、`email_code`、`one_time_token`。仅已注册邮箱可登录；未注册返回 401 与「该账号尚未完成注册」（并返回新 `one_time_token`）。
- **登录弹窗交互**：改为「欢迎回来」登录态 + 「创建新账号」注册态双页切换；登录页底部提供「还没有账号？创建账号」，注册页提供「已有账号？立即登录」。注册页采用与登录一致的三栏布局（账号注册 / 手机号注册 / 邮箱注册），仅账号注册含“选填绑定（手机/邮箱）”能力。
- **注册身份模型**：`register_via=phone/email` 时仅写入对应身份（`phone` 或 `email`），不写入 `account` 身份；`register_via=account` 时按原流程写入账号身份（可选再绑定手机/邮箱）。
- **OTT**：JWT 格式，`type=one_time`，`purpose=sms_login|email_login|account_login`，`sub=手机号/邮箱/用户名`，有效期 10 分钟；由 `AuthManager.create_one_time_token` 签发、`verify_one_time_token` 校验。

### 1.3 GitHub 登录与绑定

- **登录流程**：点击「GitHub 登录」→ 请求 `GET /api/auth/github-auth-url?redirect_uri=前端首页` 得到授权 URL → 跳转 GitHub 授权 → 回调带 `code` → 前端请求 `POST /api/auth/github-login`，Body `{"code":"xxx"}` → 后端用 code 换 token、拉取用户信息，按 `github_id` 查/建用户并返回 JWT。
- **绑定流程**：个人中心「绑定 GitHub」在新窗口打开；`redirect_uri` 含 `bind=github` 时，`GET /api/auth/github-auth-url` 返回的授权 URL 会加 `prompt=select_account`，便于用户选择要绑定的 GitHub 账号。回调落地任意页（如 `/` 或 `/profile`）时，前端**必须**走绑定分支：根据 URL 中 `bind=github` 判定为绑定（`isBindGithubCallback()` 同时读 `route.query` 与 `window.location.search`），只请求 `POST /api/auth/bind-github`（带当前用户 Token），**绝不**请求 `POST /api/auth/github-login`，以保证保持当前登录用户、仅增加 GitHub 关联。成功后前端派发 `github-bound`，个人中心监听并刷新已绑定列表。
- **配置**：必须在 GitHub 创建 OAuth App，配置 **Authorization callback URL** 与前端回调一致；环境变量 `GITHUB_CLIENT_ID`、`GITHUB_CLIENT_SECRET`。缺任一则 503，无假登录。
- **多用户**：任意 GitHub 用户均可使用；以 `github_id` 区分本站用户。

### 1.4 微信扫码登录（OAuth 不变）

- **流程**：点击「微信登录」→ 请求 `GET /api/auth/wechat-auth-url?redirect_uri=前端回调页` → 弹窗 iframe 展示微信二维码 → 用户扫码授权 → 微信重定向到本站 `/wechat-callback?code=xxx` → 回调页取 code 调 `POST /api/auth/wechat-login`，后端用 code 换 openid，按 openid 查/建用户并返回 JWT → 回调页通过 `postMessage` 通知父窗口完成登录。
- **配置**：微信开放平台创建**网站应用**，配置授权回调域；环境变量 `WECHAT_APPID`、`WECHAT_SECRET`。本地无域名时无法配置回调域，仅能联调或使用开发占位。

---

## 二、注册功能

- **现状**：注册已开启，不再返回 403「注册功能暂时关闭」。
- **规则**：必填用户名、密码、确认密码（至少 6 位、两次一致，且注册密码至少包含三类字符：大写/小写/数字/符号）；选填手机号+手机验证码、邮箱+邮箱验证码；若填写手机/邮箱则必须填写对应验证码并通过校验。
- **流程**：校验通过后写入 `users` + `user_identities`（account、可选 email/phone），生成 JWT 并返回，前端写入 token 与用户信息即完成注册并登录。

---

## 三、用户表与身份体系

### 3.1 表结构（USERS + USER_IDENTITIES）

- **users**：`id`、`nickname`、`avatar`、`primary_email`、`primary_phone`、`points`、`role`、`is_active`、`created_at`。
- **user_identities**：`user_id`、`provider`、`identifier`、`credential`（JSONB）、`linked_at`、`credits_contributed`、`free_contributed`、`paid_contributed`（合并时该身份带入的积分，解绑时按此拆出）；约束 `UNIQUE(provider, identifier)`、`UNIQUE(user_id, provider)`。
- **provider**：account / email / phone / wechat / github；account 的 credential 存 `password_hash`。

### 3.2 对接要点

- **get_current_user**：查 `users` 表，对外兼容 `username=nickname`、`email=primary_email`、`phone=primary_phone`、`credits=points`，前端无需改字段名。
- **登录/注册/绑定**：全部按 `user_identities` 查/插；账号密码登录查 `provider='account'`，手机/邮箱/微信/GitHub 分别对应各自 provider。
- **迁移**：`backend/scripts/migrate_users_to_identities.py` 将旧 users 迁入新结构；预设用户与 admin 初始化在 `main.py` 中按新表写入。

---

## 四、用户绑定与合并

### 4.1 功能概述

- **已绑定账号**：个人中心展示当前用户已绑定的登录方式（账号/邮箱/手机/微信/GitHub），脱敏显示。
- **绑定更多**：支持在登录状态下绑定手机、邮箱、微信、GitHub、**账号**（用户名+密码）。若该方式已绑定其他用户，则自动**合并**到当前用户（对方身份并入当前账号，对方用户记录删除）。
- **合并选项**：请求体可带 `use_other_nickname`，合并后是否采用被合并账号的显示名。
- **显示名称**：可自定义昵称，或从已绑定身份中选择同步（如邮箱前缀、手机尾号、账号名等）。**全站唯一**：`users.nickname` 作为展示名，与任意其他用户比较为**不区分大小写**且**忽略首尾空格**后不得相同；个人中心保存时若冲突则接口返回 400；新用户（注册、手机/邮箱首登、GitHub/微信首登、解绑拆户等）若默认生成的昵称已存在，则自动追加随机后缀。实现见 `backend/api/auth.py` 中 `_normalize_profile_nickname`、`_profile_display_name_taken_by_other`、`_allocate_unique_display_nickname_for_new_user` 与 `PATCH /api/auth/profile`。

### 4.2 绑定接口（均需登录）

| 接口 | 说明 |
|------|------|
| `GET /api/auth/identities` | 获取已绑定身份列表 |
| `PATCH /api/auth/profile` | 更新昵称或从某身份同步显示名 |
| `POST /api/auth/bind-phone` | 绑定手机（需短信验证码；发短信前需图形验证码） |
| `POST /api/auth/bind-email` | 绑定邮箱（需邮箱验证码；发验证码前需图形验证码） |
| `POST /api/auth/bind-account` | 绑定账号（用户名+密码；若该账号属其他用户则合并） |
| `POST /api/auth/bind-wechat` | 绑定微信（传 OAuth code） |
| `POST /api/auth/bind-github` | 绑定 GitHub（传 OAuth code） |

### 4.3 合并逻辑

- **绑定账号**时，若该账号已属于另一用户 B：将 B 并入当前用户 A（见下条），积分按免费/付费分别相加，并为每个迁入身份记录 `free_contributed`、`paid_contributed`，解绑时按身份拆分（见 4.5）。
- **绑定 GitHub**时，若该 GitHub 已属于另一用户 B：同样将 B 并入当前用户 A（与 bind-account 一致），积分相加并记录各身份带入的免费/付费。
- 合并步骤：将 B 的所有 `user_identities` 的 `user_id` 改为 A；免费/付费积分分别加到 A；为每个迁入身份写入 `credits_contributed`、`free_contributed`、`paid_contributed`（对方积分按身份数均分）；若 `use_other_nickname` 为 true 则更新 A 的昵称；将 B 的主邮箱/主手机（若 A 为空）补到 A；删除用户 B。

### 4.4 按当前登录方式隐藏解绑按钮

- **需求**：个人中心「登录方式绑定」栏中，**当前登录方式不可解绑**，仅可解绑其他方式。当前会话所用登录方式不显示解绑按钮，并显示「（当前登录方式，不可解绑）」提示；后端解绑时校验至少保留一种登录方式。
- **实现思路**：登录成功时在前端记录「当前登录方式」并持久化；个人中心读取该值，对「已绑定 xxx」行仅当「当前登录方式 ≠ 该 provider」时才渲染解绑按钮，否则显示灰色提示文案。
- **前端实现**：
  - **存储**（`frontend-vue/src/lib/storage.ts`）：`LOGIN_VIA`、`getLoginVia()`、`setLoginVia(v)`、`clearLoginVia()`。
  - **登录时写入**（`frontend-vue/src/stores/auth.ts`）：`login`/`loginWithOTT` 根据 payload 设 account/phone/email；`register` 设 account；`githubLogin` 设 github；`wechatLogin` 设 wechat；`logout` 时 `clearLoginVia()`。微信回调页单独 `setLoginVia('wechat')`。
  - **个人中心**（`frontend-vue/src/views/ProfilePage.vue`）：`canUnbind(provider) = (loginVia !== provider)`；五处解绑按钮 `v-if="canUnbind(...)"`，当前登录方式处显示「（当前登录方式，不可解绑）」；区块说明文案为「当前登录方式不可解绑，仅可解绑其他方式」。
- **弹窗绑定后主窗口同步**：绑定 GitHub 在新窗口完成时，弹窗成功后 `postMessage({ type: 'github-bound' })` 给 `window.opener` 并关闭；`App.vue` 监听 `message` 后派发 `github-bound`，个人中心监听该事件执行 `loadIdentities()` 与 `refreshProfileAndNickname()`；个人中心另监听 `visibilitychange`，切回标签时重新拉取，避免看到旧数据。
- **兼容**：未记录登录方式时 `canUnbind` 恒为 true，仍显示所有解绑按钮；后端会拒绝「解绑后无任何身份」的请求。

### 4.5 积分合并与解绑拆分

- **需求**：账号 A 与账号 B 绑定时积分按免费/付费分别相加；解绑时该身份只带走「合并时自己带入的」免费/付费，不把主账号的付费误分走。
- **表**：`user_identities` 有 `credits_contributed`（总带入）、`free_contributed`、`paid_contributed`（该身份合并时带入的免费/付费）。`00_init_schema.sql` 建表含三列；已有库由 `main.py` 的 `init_database` 执行 `ADD COLUMN IF NOT EXISTS free_contributed/paid_contributed`。
- **合并**（`_merge_other_user_into_current`）：当前用户免费/付费分别加上对方；从对方迁入的每个身份，按均分写入 `free_contributed`、`paid_contributed`（及 `credits_contributed` = 二者之和）。
- **解绑**（`_unbind_identity_to_new_user`）：读取该身份的 `free_contributed`、`paid_contributed`；从当前用户扣减时「免费扣免费、付费扣付费」，新用户得到对应的免费/付费；可扣量不超过当前用户现有免费/付费。无带入记录时（旧数据）仅从免费拆或给默认 60 免费（与 FREE_POINTS_REFRESH_AMOUNT 一致）。
- **绑定 GitHub**：个人中心「绑定 GitHub」在新窗口打开授权；`redirect_uri` 含 `bind=github` 时授权 URL 加 `prompt=select_account` 以尽量显示账号选择页；若未出现可提示无痕或先退出 GitHub。

---

## 五、验证码与配置

### 5.1 图形验证码

- 获取：`GET /api/auth/captcha`，返回 `image`（data URL）、`captcha_id`。
- 失败策略：同一 IP 连续 5 次失败锁定 15 分钟；提示「还有 X 次机会」或「请15分钟后再试」。
- 用于：账号登录、发送手机验证码、发送邮箱验证码前均需通过图形验证码。

### 5.2 手机短信验证码

- **发送**：`POST /api/auth/send-code?phone=xxx`，需同时传 `captcha_id`、`captcha_code`（图形验证码）。校验手机号 11 位、1 开头、第二位 3–9；生成 6 位数字验证码，有效期 5 分钟，存 Redis 或内存。
- **配置**：阿里云短信需配置 `ALIYUN_ACCESS_KEY_ID`、`ALIYUN_ACCESS_KEY_SECRET`、`SMS_SIGN_NAME`、`SMS_TEMPLATE_CODE`；可选安装 `alibabacloud_dysmsapi20170525` 等。未配置时接口仍返回 `code` 供测试。

### 5.3 邮箱验证码

- **发送**：`POST /api/auth/send-email-code?email=xxx`，需同时传 `captcha_id`、`captcha_code`。生成 6 位验证码，有效期 15 分钟；若配置 SMTP 则真实发信。
- **配置**：`.env` 中配置 `SMTP_HOST`、`SMTP_PORT`、`SMTP_USER`、`SMTP_PASSWORD`（授权码非登录密码）；QQ 邮箱/163 等需在邮箱设置中开启 SMTP 并生成授权码。未配置时接口返回说明及 `code` 供测试。

---

## 六、API 接口汇总

### 6.1 图形验证码

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/auth/captcha` | 获取图形验证码图片与 captcha_id；锁定期内返回 403 |

### 6.2 登录与注册

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 账号(含 captcha_id/login_code)/手机/邮箱登录 |
| POST | `/api/auth/register` | 注册（可选手机/邮箱+验证码） |

### 6.3 验证码发送（需图形验证码）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/send-code` | 发送手机验证码，Query: phone, captcha_id, captcha_code |
| POST | `/api/auth/send-email-code` | 发送邮箱验证码，Query: email, captcha_id, captcha_code |

### 6.4 第三方登录

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/auth/github-auth-url` | Query: redirect_uri，返回 GitHub 授权 URL |
| POST | `/api/auth/github-login` | Body: { code } |
| GET | `/api/auth/wechat-auth-url` | Query: redirect_uri，返回微信扫码页 URL |
| POST | `/api/auth/wechat-login` | Body: { code } |

### 6.5 身份与绑定（需登录）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/auth/identities` | 已绑定身份列表 |
| PATCH | `/api/auth/profile` | 更新昵称或 display_name_from |
| POST | `/api/auth/bind-phone` | Body: phone, phone_code, use_other_nickname? |
| POST | `/api/auth/bind-email` | Body: email, email_code, use_other_nickname? |
| POST | `/api/auth/bind-account` | Body: username, password, use_other_nickname? |
| POST | `/api/auth/bind-wechat` | Body: code, use_other_nickname? |
| POST | `/api/auth/bind-github` | Body: code, use_other_nickname? |

---

## 七、涉及文件索引

| 模块 | 文件 | 说明 |
|------|------|------|
| 认证路由 | `backend/api/auth.py` | 注册/登录/图形验证码/发送验证码/绑定/合并逻辑 |
| 认证依赖 | `backend/api/dependencies.py` | get_current_user 查 users 并做字段兼容 |
| 配置 | `backend/config.py` | SMTP、短信、GitHub、微信、验证码有效期等 |
| 建库与预设 | `backend/main.py` | users、user_identities 建表，预设用户与 admin 初始化 |
| 迁移 | `backend/scripts/migrate_users_to_identities.py` | 旧 users 迁入新结构 |
| 管理后台 | `backend/api/admin.py` | 管理员登录、系统统计（`/api/admin/stats`，需 `get_admin_user` 鉴权）、用户列表/导出、操作日志 |
| 前端 API | `frontend-vue/src/lib/api.ts` | 认证相关请求封装 |
| 前端存储 | `frontend-vue/src/lib/storage.ts` | token、用户信息、当前登录方式 login_via（用于个人中心隐藏当前方式的解绑按钮） |
| 认证状态 | `frontend-vue/src/stores/auth.ts` | 登录/注册/登出、登录时写入 setLoginVia |
| 登录弹窗 | `frontend-vue/src/components/AuthModal.vue` | 账号/手机/邮箱/注册、图形验证码、第三方登录；账号密码与注册密码使用 `PasswordInput.vue`（右侧眼睛切换显示/隐藏，`authModal.showPassword` / `hidePassword`） |
| 个人中心 | `frontend-vue/src/views/ProfilePage.vue` | 已绑定列表、显示名称、绑定/解绑、按 loginVia 隐藏当前方式解绑按钮 |
| 微信回调 | `frontend-vue/src/views/WechatCallbackPage.vue` | 微信授权回调、postMessage 通知父窗口、登录成功后 setLoginVia('wechat') |

---

## 八、提交文档规范（本次改动）

### 8.1 积分充值功能（2026-2-24）

以下按「提交文档规范」填写积分充值功能的改动说明。

#### 1. 依赖（Dependencies）

| 项 | 说明 |
|----|------|
| **1、是否添加依赖** | **否**。本次未新增任何第三方库或依赖。 |
| **2、依赖写在了哪个文件、什么位置（第几行）** | 不适用。 |

#### 2. 数据库改动（Database Modifications）

| 项 | 说明 |
|----|------|
| **3、是否改动数据库** | **是**。新增 `credit_recharges` 表（充值订单记录）和 `recharge_tiers` 表（充值档位配置）。 |
| **4、改动数据库的 SQL 语句及所在位置** | ① `backend/migrations/004_add_credit_recharges_table.sql`（第2-24行）：建 `credit_recharges` 表及索引，包含 `bonus_amount`（赠送积分）、`total_amount`（总积分）字段。<br>② `backend/migrations/005_add_recharge_tiers.sql`（第2-18行）：建 `recharge_tiers` 表及索引。<br>③ `backend/migrations/005_add_recharge_tiers.sql`（第21-26行）：插入5档默认充值档位（100/500/1000/5000/10000积分，赠送比例0%/5%/10%/15%/20%）。<br>④ `backend/main.py` 的 `init_database` 函数（第244-327行）：包含相同的建表和插入逻辑，Docker 启动时自动执行。 |

#### 3. 本次改动涉及的文件与内容摘要

| 文件 | 改动摘要 |
|------|----------|
| `backend/api/credits.py` | ① 新增 `GET /api/credits/recharge-tiers` 接口：获取充值档位列表（仅返回启用的档位，按 sort_order 排序）。<br>② 新增 `POST /api/credits/recharge` 接口：创建充值订单，根据档位ID计算充值积分、赠送积分、总积分和支付金额，调用支付网关生成支付URL。<br>③ 新增 `GET /api/credits/recharge-history` 接口：查询用户充值历史，支持分页，返回充值金额、赠送积分、支付状态等信息。 |
| `backend/api/payments.py` | ① 修改 `POST /api/payments/alipay/notify` 接口：支付回调统一处理，根据订单号前缀区分充值订单（`recharge_` 开头）和商品订单。<br>② 充值订单回调处理：更新 `credit_recharges` 表状态为 `paid`，增加用户 `paid_points`（使用 `total_amount`，包含赠送），记录 `paid_at` 时间。<br>③ 订单号格式：充值订单使用 `recharge_{UUID}`，商品订单直接使用UUID。 |
| `backend/main.py` | ① `init_database` 函数（第244-327行）：新增 `credit_recharges` 表和 `recharge_tiers` 表的建表逻辑。<br>② 插入默认充值档位：如果 `recharge_tiers` 表为空，插入5档默认配置。<br>③ 为 `credit_recharges` 表添加 `bonus_amount` 和 `total_amount` 字段（ALTER TABLE IF NOT EXISTS）。<br>④ 修复 `GET /api/user/profile` 接口：`free_credits` 应映射 `free_points`，`paid_credits` 应映射 `paid_points`（之前字段映射错误导致付费积分显示为0）。<br>⑤ 删除第329行的 Git 冲突标记 `>>>>>>> develop3`。 |
| `backend/migrations/004_add_credit_recharges_table.sql` | 新增文件。建 `credit_recharges` 表（第2-20行）：包含 `id`、`user_id`、`amount`（充值基础积分）、`bonus_amount`（赠送积分）、`total_amount`（总积分）、`amount_yuan`（支付金额）、`payment_method`、`payment_id`、`status`、`created_at`、`paid_at` 等字段。<br>建索引（第22-24行）：`idx_credit_recharges_user_id`、`idx_credit_recharges_status`、`idx_credit_recharges_created_at`。 |
| `backend/migrations/005_add_recharge_tiers.sql` | 新增文件。建 `recharge_tiers` 表（第2-16行）：包含 `id`、`min_amount`（充值基础积分）、`bonus_rate`（赠送比例）、`bonus_fixed`（固定赠送积分）、`description`、`is_active`、`sort_order`、`created_at`、`updated_at` 等字段。<br>建索引（第18行）：`idx_recharge_tiers_active`、`idx_recharge_tiers_min_amount`。<br>插入默认档位（第21-26行）：5档充值配置。 |
| `frontend-vue/src/components/RechargeModal.vue` | 新增文件。充值弹窗组件：<br>① 显示5个充值档位按钮，格式为"充值+赠送"（如：`1000+100 积分`，价格 `¥100.00`）。<br>② 支持选择支付方式（支付宝/Stripe，当前仅支付宝可用）。<br>③ 响应式布局：移动端单列（`grid-cols-1`），桌面端双列（`sm:grid-cols-2`）。<br>④ 点击充值后调用 `api.credits.recharge()` 创建订单，跳转到支付页面。<br>⑤ 加载状态和错误提示。 |
| `frontend-vue/src/views/RechargeCallbackPage.vue` | 新增文件。充值回调页面：<br>① 支付完成后的落地页，显示充值结果（成功/失败）。<br>② 3秒后自动跳转到个人中心。<br>③ 提供"立即返回"按钮手动跳转。 |
| `frontend-vue/src/views/ProfilePage.vue` | ① 个人中心添加"充值"按钮，点击打开充值弹窗。<br>② 检测URL参数 `recharge_success=1`，显示充值成功提示并清除URL参数。<br>③ 充值成功后调用 `api.user.getProfile()` 刷新积分显示。<br>④ 显示免费积分和付费积分（修复后正确显示）。 |
| `frontend-vue/src/views/OrdersPage.vue` | ① 订单列表页面检测充值订单（订单号以 `recharge_` 开头）。<br>② 充值订单自动跳转到个人中心，不显示在订单列表中。<br>③ 响应式优化：订单号使用 `break-all` 防止溢出，订单信息支持移动端布局（`flex-col sm:flex-row`）。 |
| `frontend-vue/src/lib/api.ts` | ① 新增 `api.credits.recharge()` 接口：创建充值订单。<br>② 新增 `api.credits.getRechargeHistory()` 接口：获取充值历史。<br>③ 新增 `api.credits.getRechargeTiers()` 接口：获取充值档位列表。 |
| `frontend-vue/src/router/routes.ts` | 新增路由 `/recharge-callback`：充值回调页面路由配置。 |

#### 4. 功能说明

**核心功能**：
- 用户可通过个人中心的"充值"按钮购买积分
- 支持5档固定充值档位，不支持自定义金额
- 充值档位可后台配置，包括充值金额、赠送比例、描述等
- 充值成功后增加用户的 `paid_points`（付费积分）
- 充值订单与商品订单统一管理，但类型不同（订单号前缀区分）

**充值档位**（默认配置）：
- 1档：100积分，赠送0%，实际到账100积分，价格¥10.00
- 2档：500积分，赠送5%，实际到账525积分，价格¥50.00
- 3档：1000积分，赠送10%，实际到账1100积分，价格¥100.00
- 4档：5000积分，赠送15%，实际到账5750积分，价格¥500.00
- 5档：10000积分，赠送20%，实际到账12000积分，价格¥1000.00

**充值流程**：
1. 用户打开充值弹窗，选择档位和支付方式
2. 创建充值订单，后端生成支付URL
3. 跳转到支付平台（如支付宝）完成支付
4. 支付平台异步通知后端，验证签名后更新订单状态并增加用户积分
5. 返回个人中心，显示充值成功提示

**响应式优化**：
- 充值弹窗支持移动端自适应（单列/双列布局切换）
- 订单列表页面响应式优化（订单号换行、金额布局调整）

**Bug修复**：
- 修复 `backend/main.py` 中 `get_profile` 接口字段映射错误：`free_credits` 应映射 `free_points`，`paid_credits` 应映射 `paid_points`
- 删除 `backend/main.py` 第329行的 Git 冲突标记 `>>>>>>> develop3`

---

### 8.2 认证与验证码功能（历史改动）

以下按「提交文档规范」填写认证/验证码/解绑/配置相关改动的说明。

#### 1. 依赖（Dependencies）

| 项 | 说明 |
|----|------|
| **1、是否添加依赖** | **否**。本次未新增任何第三方库或依赖。 |
| **2、依赖写在了哪个文件、什么位置（第几行）** | 不适用。 |

#### 2. 数据库改动（Database Modifications）

| 项 | 说明 |
|----|------|
| **3、是否改动数据库** | **是**。`user_identities` 增加 `free_contributed`、`paid_contributed`（INTEGER DEFAULT 0 NOT NULL），用于合并时记录该身份带入的免费/付费积分，解绑时按此拆出。 |
| **4、改动数据库的 SQL 语句及所在位置** | `00_init_schema.sql` 中 `CREATE TABLE user_identities` 增加两列；已有库由 `backend/main.py` 的 `init_database` 执行 `ALTER TABLE user_identities ADD COLUMN IF NOT EXISTS free_contributed/paid_contributed ...`。 |

#### 3. 本次改动涉及的文件与内容摘要

| 文件 | 改动摘要 |
|------|----------|
| `frontend-vue/src/App.vue` | ① GitHub 回调严格区分登录/绑定：`isBindGithubCallback()` 同时读 `route.query` 与 `window.location.search`。② URL 带 `bind=github` 时只调 `api.auth.bindGitHub`，不调 `githubLogin`，保持当前用户；成功后清理 URL、更新 auth、提示「GitHub 已绑定，当前仍为原账号」并派发 `github-bound`。<br>③ **缓存幽灵登录拦截**：回调阶段校验 URL `state` 与 `localStorage`，防篡改或缓存重定向，校验后即焚。 |
| `frontend-vue/src/components/AuthModal.vue` | ① 发短信/发邮箱验证码：**成功**后不刷新图形验证码；**失败**且错误与图形验证码相关时再 `fetchSendCodeCaptcha()`。② 打开登录弹窗时清空账号登录的 `one_time_token`；**同时清空**手机/邮箱登录的短信验证码、`loginPhone`/`loginEmail` 的 OTT、注册侧 `reg.phoneCode`/`reg.emailCode`（避免无操作登出后再打开仍显示上次验证码）。③ 每次打开登录弹窗且为账号登录时、以及从手机/邮箱切回账号登录时均拉取新图形验证码。<br>④ GitHub跳转登录前随机 `state` 存入 `localStorage` 以供防幽灵回流校验。<br>⑤ 密码输入：`PasswordInput.vue`（Lucide `eye`/`eye-off`，`title` 悬停说明，点击切换 `type`）。 |
| `frontend-vue/src/views/ProfilePage.vue` | ① 绑定 GitHub 改为按钮，新窗口打开授权；绑定回调与保存显示名后均调用 `refreshProfileAndNickname()` 刷新积分与名称。② 显示名保存失败时展示 `profileSaveError`。③ 监听 `github-bound` 事件并执行 `loadIdentities()`、`refreshProfileAndNickname()` 以刷新已绑定列表。<br>④ 弹窗前写入 `state` 防护值到 `localStorage`。 |
| `backend/api/auth.py` | ① 合并时为每个迁入身份写入 `free_contributed`、`paid_contributed`（对方免费/付费按身份数均分）。② 解绑时按该身份 `free_contributed`/`paid_contributed` 从当前用户免费/付费分别扣减，新用户得到对应免费/付费。③ bind-github 在 GitHub 已属其他用户时执行合并（与 bind-account 一致）。④ 授权 URL 在 bind=github 时加 `prompt=select_account`。⑤ 合并时 `paid_points` 用 `COALESCE(paid_points, points, 0)` 避免 legacy 付费被清零。 |
| `backend/api/dependencies.py` | `free_credits`/`paid_credits` 区分 0 与 NULL（`if ... is not None else ...`），避免重置账号后误将付费当免费显示。 |
| `backend/main.py` | `init_database` 中为 `user_identities` 增加 `free_contributed`、`paid_contributed` 列迁移。 |
| `00_init_schema.sql` | `user_identities` 表定义增加 `free_contributed`、`paid_contributed`。 |
| `backend/database.py` | 新增 `fetchval` 方法（历史改动）。 |
| `docker-compose.yml` | backend 增加 `env_file: .env`（历史改动）。 |
| `backend/.env.example` | 环境变量示例（历史改动）。 |
