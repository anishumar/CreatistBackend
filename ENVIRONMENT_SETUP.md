# 🔐 Secure Environment Setup

## ⚠️ CRITICAL SECURITY NOTICE

Your `.env` file contains real credentials and should NEVER be committed to version control!

## 🛡️ Immediate Actions Required

1. **Check if .env is in git history:**
   ```bash
   git log --oneline --all -- .env
   ```

2. **If .env was ever committed, immediately:**
   - Change your email password
   - Rotate your JWT_SECRET
   - Update your Supabase keys
   - Remove .env from git history

3. **Ensure .env is in .gitignore:**
   ```bash
   echo ".env" >> .gitignore
   ```

## 📝 Secure Environment Template

Create a `.env` file with this template (replace with your actual values):

```bash
# Server Configuration
HOST="0.0.0.0"
PORT="8080"
ENVIRONMENT="development"

# JWT Configuration (IMPORTANT: Use a strong secret!)
JWT_SECRET="your-super-secret-jwt-key-here-minimum-32-characters"

# Supabase Configuration
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your-supabase-anon-key"

# Database Configuration
DATABASE_URL="postgresql://postgres:password@db.your-project.supabase.co:5432/postgres"

# Email Configuration (Optional)
EMAIL_ADDRESS="your-email@example.com"
EMAIL_PASSWORD="your-email-app-password"
EMAIL_HOST="smtp.gmail.com"
EMAIL_PORT="587"
EMAIL_FROM="Your Name <your-email@example.com>"

# Redis Configuration (Optional)
REDIS_URL="redis://localhost:6379"

# Logging Configuration
LOG_LEVEL="INFO"
```

## 🔒 Security Best Practices

### Email Security
- Use app-specific passwords for Gmail
- Never use your main account password
- Enable 2FA on your email account

### JWT Security
- Use a strong, random JWT_SECRET (32+ characters)
- Different secrets for development/production
- Rotate secrets regularly

### Database Security
- Use connection pooling
- Enable SSL for database connections
- Use strong database passwords

## 🚨 Emergency Response

If credentials are leaked:
1. **Immediately change all passwords**
2. **Rotate all API keys**
3. **Check for unauthorized access**
4. **Review access logs**
5. **Notify affected users if necessary**

## 📋 Security Checklist

- [ ] .env file is in .gitignore
- [ ] .env was never committed to git
- [ ] Strong JWT_SECRET (32+ characters)
- [ ] App-specific email password
- [ ] SSL enabled for database
- [ ] 2FA enabled on email account
- [ ] Regular secret rotation schedule
