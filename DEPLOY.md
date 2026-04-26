# Deployment Guide — Vercel + Supabase + Render

> **Architecture**: Next.js frontend → Vercel | FastAPI backend → Render | PostgreSQL database → Supabase

---

## Prerequisites

| Tool | Purpose |
|------|---------|
| [Vercel Account](https://vercel.com) | Frontend hosting |
| [Supabase Account](https://supabase.com) | PostgreSQL database |
| [Render Account](https://render.com) | Backend hosting |
| [Git](https://git-scm.com) | Source control |

---

## Step 1: Push Code to GitHub

Render 和 Vercel 都支持从 Git 仓库自动部署。

```powershell
# 创建仓库并推送
git init
git add .
git commit -m "feat: production-ready with PostgreSQL support"
git branch -M main
git remote add origin https://github.com/<your-username>/kimi-agent-pack.git
git push -u origin main
```

---

## Step 2: Create Supabase PostgreSQL Database

1. 登录 [Supabase Dashboard](https://app.supabase.com)
2. 点击 **New Project**，选择组织，输入项目名称
3. 等待数据库创建完成（约 1-2 分钟）
4. 进入项目 → **Settings** → **Database**
5. 找到 **Connection string** → **URI** 格式：
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxx.supabase.co:5432/postgres
   ```
6. **复制这个字符串**，后面会用到

> **安全提示**：Supabase 默认开启了 **IPv4 Add-on**（付费）。Render 连接 Supabase 需要：
> - 方案 A：在 Supabase Dashboard → Database → IPv4 中启用 add-on（$3.50/月）
> - 方案 B：使用 [Supabase 连接池](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler)（推荐，免费）

---

## Step 3: Deploy Backend to Render

### 3.1 使用 Blueprint 自动部署（推荐）

1. 登录 [Render Dashboard](https://dashboard.render.com)
2. 点击 **Blueprints** → **New Blueprint Instance**
3. 选择你的 GitHub 仓库
4. Render 会自动读取根目录的 `render.yaml`
5. 在环境变量中填入：
   - `DATABASE_URL` = Supabase 连接字符串（步骤 2 复制的）
   - `KIMI_CORS_ORIGINS` = 你的 Vercel 前端域名（步骤 4 完成后回来填写）
6. 点击 **Apply** 部署

### 3.2 手动创建（备用）

如果不想用 Blueprint：

1. Render Dashboard → **New** → **Web Service**
2. 选择 GitHub 仓库
3. 配置：
   - **Name**: `kimi-agent-pack-api`
   - **Runtime**: `Docker`
   - **Dockerfile Path**: `./apps/backend/Dockerfile`
   - **Docker Build Context Directory**: `.`
4. **Environment Variables**：

| Key | Value |
|-----|-------|
| `DATABASE_URL` | `postgresql://postgres:...` |
| `KIMI_CORS_ORIGINS` | `https://your-app.vercel.app` |
| `KIMI_MAX_CONCURRENT_JOBS` | `3` |
| `KIMI_SCRIPT_TIMEOUT` | `300` |

5. 点击 **Create Web Service**
6. 等待部署完成，记录生成的域名，如：
   ```
   https://kimi-agent-pack-api.onrender.com
   ```

---

## Step 4: Deploy Frontend to Vercel

### 4.1 配置 API 地址

修改 `apps/frontend/.env.production`：

```env
NEXT_PUBLIC_API_URL=https://kimi-agent-pack-api.onrender.com
```

提交修改：

```powershell
git add .
git commit -m "chore: set production API URL"
git push
```

### 4.2 Vercel 部署

1. 登录 [Vercel Dashboard](https://vercel.com)
2. 点击 **Add New Project**
3. 导入 GitHub 仓库
4. **Framework Preset**: `Next.js`
5. **Root Directory**: `apps/frontend`
6. **Environment Variables**：

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | `https://kimi-agent-pack-api.onrender.com` |

7. 点击 **Deploy**
8. 等待构建完成（约 1-2 分钟）

### 4.3 配置后端 CORS

拿到 Vercel 域名后（如 `https://kimi-agent-pack.vercel.app`），回到 Render Dashboard：

1. 进入你的 Web Service
2. **Environment** → 添加/修改：
   ```
   KIMI_CORS_ORIGINS = https://kimi-agent-pack.vercel.app
   ```
3. 点击 **Save Changes**，Render 会自动重新部署

---

## Step 5: Verify Deployment

### 5.1 后端健康检查

```powershell
Invoke-RestMethod -Uri "https://kimi-agent-pack-api.onrender.com/health"
```

预期输出：
```json
{
  "status": "healthy",
  "version": "3.0.0",
  "database": "connected",
  "jobs_running": 0
}
```

### 5.2 API 文档

浏览器访问：
```
https://kimi-agent-pack-api.onrender.com/docs
```

### 5.3 前端页面

浏览器访问你的 Vercel 域名，确认能正常加载。

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        用户浏览器                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Vercel (Frontend)                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Next.js 14 — Static + SSR                          │   │
│  │ • /agents, /tasks, /artifacts, /eval, /memory      │   │
│  │ • API Proxy → Backend                              │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS / CORS
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Render (Backend)                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ FastAPI + Uvicorn                                   │   │
│  │ • /api/jobs/run-script  (脚本执行)                  │   │
│  │ • /api/project-state    (项目状态)                  │   │
│  │ • /api/artifacts        (产物管理)                  │   │
│  │ • /health               (健康检查)                  │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │ TCP / SSL
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Supabase (Database)                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ PostgreSQL 15                                       │   │
│  │ • jobs                                              │   │
│  │ • project_state                                     │   │
│  │ • artifacts_index                                   │   │
│  │ • audit_log                                         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Environment Variables Reference

### Backend (`apps/backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | Supabase PostgreSQL 连接字符串 |
| `KIMI_CORS_ORIGINS` | ✅ | Vercel 前端域名，逗号分隔 |
| `KIMI_API_HOST` | | 默认 `0.0.0.0` |
| `KIMI_API_PORT` | | 默认 `8000` |
| `KIMI_MAX_CONCURRENT_JOBS` | | 默认 `3` |
| `KIMI_SCRIPT_TIMEOUT` | | 默认 `300`（秒）|

### Frontend (`apps/frontend/.env.production`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | ✅ | Render 后端域名 |

---

## Troubleshooting

### 后端无法连接数据库

```
connection to server at "db.xxx.supabase.co", port 5432 failed: Connection timed out
```

**原因**：Supabase 默认只允许特定 IP 访问。
**解决**：
1. Supabase Dashboard → **Project Settings** → **Database**
2. **Network Bans** → 添加 Render 的出口 IP 段（或临时设置为 `0.0.0.0/0` 允许所有 IP）
3. 或使用 Supabase Connection Pooler（`db.xxx.supabase.co:6543`）

### 前端 CORS 错误

```
Access to fetch at 'https://...' from origin 'https://...' has been blocked by CORS policy
```

**解决**：确保 `KIMI_CORS_ORIGINS` 包含完整的前端域名（包括 `https://`）。

### 脚本执行超时

Render free tier 有 **15 分钟** 请求超时限制。如果脚本需要更长时间：
- 使用 `/api/jobs/run-script-async` 异步接口
- 或升级到 Render **Standard** 计划

---

## Cost Estimate (Monthly)

| Service | Plan | Cost |
|---------|------|------|
| Vercel (Frontend) | Hobby (Free) | $0 |
| Render (Backend) | Web Service — Free | $0 |
| Supabase (Database) | Free Tier | $0 |
| **总计** | | **$0** |

> 生产环境推荐升级 Render 到 **Starter** ($7/月) 和 Supabase 到 **Pro** ($25/月) 以获得更高性能。
