# Railway Deployment Guide

## 🚀 Production Deployment Checklist

### 1. Environment Variables Setup

Set these environment variables in your Railway project:

#### Required Variables:
```bash
# Server Configuration
HOST=0.0.0.0
PORT=8080
ENVIRONMENT=production

# JWT Configuration (IMPORTANT: Use a strong secret!)
JWT_SECRET=your-super-secure-jwt-secret-key-here-minimum-32-characters

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Database Configuration
DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres

# Logging
LOG_LEVEL=INFO
```

#### Optional Variables:
```bash
# Email Configuration (if using email features)
EMAIL_ADDRESS=your@email.com
EMAIL_PASSWORD=your-email-app-password
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_FROM=Your Name <your@email.com>

# Redis Configuration (if using Redis)
REDIS_URL=redis://localhost:6379
```

### 2. Railway Deployment Steps

1. **Connect Repository:**
   - Go to Railway Dashboard
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `CreatistBackend` repository
   - Select the `deployment` branch

2. **Configure Environment Variables:**
   - Go to your project settings
   - Add all the environment variables listed above
   - **IMPORTANT:** Use a strong JWT_SECRET (minimum 32 characters)

3. **Deploy:**
   - Railway will automatically detect the Python project
   - It will use the `railway.json` configuration
   - The app will start with the command: `uvicorn src.app:app --host 0.0.0.0 --port $PORT --workers 1`

### 3. Health Check Configuration

The app includes a health check endpoint at `/health` that Railway will use to monitor the deployment.

### 4. Production Optimizations

#### CORS Configuration:
- iOS apps don't require CORS configuration
- CORS is only needed for web browsers
- Minimal CORS enabled for development/testing tools

#### Logging:
- Production logging is optimized for performance
- Log level can be controlled via `LOG_LEVEL` environment variable
- Logs are rotated to prevent disk space issues

#### Security:
- JWT tokens expire after 15 minutes (access) and 7 days (refresh)
- CORS is restricted to specific domains in production
- Environment variables are used for all sensitive configuration

### 5. Monitoring and Debugging

#### Railway Dashboard:
- Monitor deployment status
- View logs in real-time
- Check resource usage

#### Health Check:
```bash
curl https://your-railway-app.railway.app/health
```

#### Test Authentication:
```bash
# Test signin
curl -X POST https://your-railway-app.railway.app/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"email":"anishumar01@gmail.com","password":"abcd123"}'
```

### 6. Troubleshooting

#### Common Issues:

1. **Environment Variables Missing:**
   - Check Railway environment variables
   - Ensure all required variables are set

2. **Database Connection Issues:**
   - Verify `DATABASE_URL` is correct
   - Check Supabase connection

3. **CORS Issues:**
   - iOS apps don't have CORS restrictions
   - CORS is only relevant for web browsers

4. **JWT Issues:**
   - Ensure `JWT_SECRET` is set and strong
   - Check token expiration times

#### Logs:
- Check Railway logs for detailed error messages
- Use `LOG_LEVEL=DEBUG` for more verbose logging during troubleshooting

### 7. Post-Deployment

1. **Test all endpoints:**
   - Health check: `/health`
   - Authentication: `/auth/signin`, `/auth/refresh`, `/auth/fetch`
   - Other API endpoints

2. **Update iOS app configuration:**
   - Point your iOS app to the new Railway URL
   - Update API base URL in your iOS app

3. **Monitor performance:**
   - Check Railway metrics
   - Monitor response times
   - Watch for errors in logs

### 8. Security Checklist

- [ ] Strong JWT_SECRET (32+ characters)
- [ ] CORS disabled for iOS app (not needed)
- [ ] Environment variables for all sensitive data
- [ ] HTTPS enabled (Railway handles this)
- [ ] Database connection secured
- [ ] Logging level set to INFO or higher in production

### 9. Scaling

Railway supports automatic scaling based on traffic. You can:
- Adjust the number of replicas in `railway.json`
- Monitor resource usage in the Railway dashboard
- Set up auto-scaling rules if needed

## 🎉 Deployment Complete!

Your CreatistBackend API is now deployed and ready for production use!
