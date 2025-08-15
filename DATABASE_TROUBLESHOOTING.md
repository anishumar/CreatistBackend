# 🗄️ Database Connection Troubleshooting

## 🚨 Common Railway Database Issues

### Issue: "Network is unreachable" Error

This error occurs when Railway can't connect to your database. Here are the most common causes and solutions:

## 🔧 Step-by-Step Fix

### 1. Check Environment Variables

In your Railway project dashboard, verify these variables:

```bash
# Required Database Variables
DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres

# Other Required Variables
HOST=0.0.0.0
PORT=8080
ENVIRONMENT=production
JWT_SECRET=your-super-secure-jwt-secret-key-here-minimum-32-characters
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
LOG_LEVEL=INFO
```

### 2. Verify DATABASE_URL Format

Your DATABASE_URL should look like this:
```
postgresql://username:password@host:port/database?sslmode=require
```

**For Supabase:**
```
postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres?sslmode=require
```

### 3. Test Database Connection

You can test your database connection using:

```bash
# Test with psql (if you have it installed)
psql "postgresql://postgres:password@db.your-project.supabase.co:5432/postgres?sslmode=require"

# Or test with curl (if your database allows HTTP connections)
curl -X GET "https://your-project.supabase.co/rest/v1/" \
  -H "apikey: your-supabase-anon-key" \
  -H "Authorization: Bearer your-supabase-anon-key"
```

### 4. Common Issues and Solutions

#### Issue: DATABASE_URL not set
**Solution:** Add DATABASE_URL to Railway environment variables

#### Issue: Wrong database credentials
**Solution:** 
1. Check your Supabase dashboard
2. Go to Settings → Database
3. Copy the connection string
4. Update Railway environment variables

#### Issue: Network connectivity
**Solution:**
1. Check if your Supabase project is active
2. Verify the database host is correct
3. Ensure SSL is enabled (`?sslmode=require`)

#### Issue: Database doesn't exist
**Solution:**
1. Check if your Supabase database is created
2. Verify the database name in the URL
3. Check if you have the correct permissions

### 5. Railway-Specific Solutions

#### Use Railway's PostgreSQL Service

1. **Add PostgreSQL to your Railway project:**
   - Go to Railway dashboard
   - Click "New" → "Database" → "PostgreSQL"
   - Railway will automatically set `DATABASE_URL`

2. **Connect your app to Railway's PostgreSQL:**
   - Railway will provide a `DATABASE_URL` automatically
   - No need to configure external database

#### Use External Database (Supabase)

1. **Ensure your Supabase project is active**
2. **Check database connection settings**
3. **Verify network access from Railway**

### 6. Debugging Steps

#### Check Railway Logs
```bash
# View deployment logs in Railway dashboard
# Look for database connection errors
```

#### Test Locally
```bash
# Test with your local .env file
python -c "
import os
import asyncpg
import asyncio

async def test_db():
    try:
        pool = await asyncpg.create_pool(os.environ['DATABASE_URL'])
        print('✅ Database connection successful')
        await pool.close()
    except Exception as e:
        print(f'❌ Database connection failed: {e}')

asyncio.run(test_db())
"
```

### 7. Environment Variable Checklist

- [ ] `DATABASE_URL` is set correctly
- [ ] Database credentials are valid
- [ ] Database host is reachable
- [ ] SSL is enabled (`?sslmode=require`)
- [ ] Database exists and is accessible
- [ ] User has proper permissions

### 8. Quick Fix Commands

```bash
# If using Railway's PostgreSQL, add this service:
# Railway Dashboard → New → Database → PostgreSQL

# If using Supabase, verify your connection string:
# Supabase Dashboard → Settings → Database → Connection string
```

## 🎯 Most Likely Solution

For Railway deployment, the easiest solution is to:

1. **Use Railway's PostgreSQL service** (recommended)
2. **Or ensure your Supabase DATABASE_URL is correct**
3. **Add all required environment variables**
4. **Redeploy your application**

The updated code now includes better error handling and logging to help identify the exact issue.
