# 🚀 Quick Railway Deployment Guide

## 🎯 Fastest Way to Deploy

### Step 1: Add Railway PostgreSQL Database

1. **Go to Railway Dashboard**
2. **Click "New" → "Database" → "PostgreSQL"**
3. **Railway will automatically set `DATABASE_URL`**

### Step 2: Set Environment Variables

In Railway Variables tab, add these:

```bash
# Server Configuration
HOST=0.0.0.0
PORT=8080
ENVIRONMENT=production

# JWT Configuration (IMPORTANT!)
JWT_SECRET=your-super-secure-jwt-secret-key-here-minimum-32-characters

# Supabase Configuration (for user management)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Logging
LOG_LEVEL=INFO
```

**Note:** `DATABASE_URL` will be set automatically by Railway PostgreSQL service.

### Step 3: Deploy

1. **Connect your GitHub repository**
2. **Select the `deployment` branch**
3. **Railway will auto-deploy**

## 🔧 Alternative: Use External Database

If you want to use Supabase instead:

1. **Get your Supabase connection string:**
   - Go to Supabase Dashboard
   - Settings → Database
   - Copy Connection string

2. **Set in Railway Variables:**
   ```bash
   DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres?sslmode=require
   ```

## 🧪 Test Your Deployment

Once deployed, test these endpoints:

```bash
# Health check
curl https://your-app.railway.app/health

# Test authentication
curl -X POST https://your-app.railway.app/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"email":"your-email@example.com","password":"your-password"}'
```

## 🎉 Done!

Your iOS app backend is now deployed and ready to use!

## 📱 Update Your iOS App

Change your API base URL to:
```swift
let baseURL = "https://your-app.railway.app"
```
