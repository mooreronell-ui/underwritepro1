# Deploy to Railway - SIMPLE 3-STEP GUIDE

## ✅ Code is Fixed and Ready!

I've fixed the database connection issue. The app will now start even if the database isn't immediately available.

---

## 3 STEPS TO DEPLOY (5 Minutes Total)

### STEP 1: Create New Project in Railway (2 min)
1. Go to https://railway.app
2. Click "Sign in" (with GitHub)
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose: **mooreronell-ui/underwritepro1**
6. Railway will start building automatically

### STEP 2: Add PostgreSQL Database (1 min)
1. In your project, click "New" button
2. Click "Database"
3. Click "Add PostgreSQL"
4. Done! Railway automatically links it

### STEP 3: Add Environment Variables (2 min)
1. Click on your web service (underwritepro1)
2. Click "Variables" tab
3. Click "New Variable" and add these TWO:

```
JWT_SECRET_KEY=eb89a45acdfc2a2fa7e24ebe35b0ea01288be0355a45a078d37e8cd712ae6565
PORT=8000
```

**DO NOT add DATABASE_URL manually** - Railway adds it automatically!

---

## That's It!

Railway will automatically redeploy with the correct settings.

**Wait 2-3 minutes** and your app will be live!

---

## What I Fixed:

✅ App won't crash if database isn't ready immediately  
✅ Better error handling for Railway's service linking  
✅ Added health check endpoints for Railway  
✅ Removed strict database requirement at startup  

---

## After Deployment:

1. Click "Settings" → "Networking" → "Generate Domain"
2. Visit your URL
3. You'll see the login page!
4. API docs at: your-url/docs

---

## Cost: $5/month
- Includes web service + PostgreSQL
- First month FREE with $5 credit

---

Last Updated: October 4, 2025  
Status: FIXED AND READY TO DEPLOY
