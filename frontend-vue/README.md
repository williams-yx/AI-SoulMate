# Vue 前端重构（第一阶段：单入口 SPA 骨架）

## 目标
- **登录前/登录后是一套页面逻辑**：只切换状态，不再是两张 HTML。
- 先保证“能跑、能登录、能显示头像/个人中心”，并提供一个 **旧版功能页临时入口**（不丢功能）。
- 后续再把旧版功能（课程/社区/工作流/商城/造梦）逐页迁移成 Vue 组件。

## 目录
- `src/App.vue`: 统一布局（导航 + 登录按钮/头像 + 下拉菜单）
- `src/components/AuthModal.vue`: 登录/注册弹窗（账户/手机号/邮箱）
- `src/stores/auth.ts`: 登录态（Pinia）
- `src/lib/api.ts`: API 客户端（走 `/api`，由 Vite proxy 到后端）
- `src/views/LegacyPage.vue`: 临时嵌入旧页面（iframe）

## 启动方式（开发）
> 需要 Node.js 18+。

在服务器上：

```bash
cd /home/ubuntu/ai-soul-mate/v0.7.0/frontend-vue
npm install
npm run dev
```

- Vue 前端：`http://服务器IP:8081`
- 后端 API：通过 Vite 代理访问 `http://服务器IP:8081/api/...`（实际转发到 `http://localhost:3000`）

## 说明
- 目前样式先用 `tailwindcss` CDN（为了减少安装依赖、让重构更快落地）。
- 等第二阶段开始迁移页面时，再把 Tailwind 切换为本地构建版，并逐步组件化。

