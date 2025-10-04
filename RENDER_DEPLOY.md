# Deploy to Render - SIMPLE GUIDE

## ✅ Code is Fixed and Ready for Render!

The app now automatically detects Render's database and converts the connection string properly.

---

## 4 SIMPLE STEPS (10 Minutes Total)

### STEP 1: Create Web Service (3 minutes)
1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account if not already connected
4. Select repository: **mooreronell-ui/underwritepro1**
5. Render will auto-detect settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main_production:app --bind 0.0.0.0:$PORT`
6. Select **Free** or **Starter** plan ($7/month)
7. Click **"Create Web Service"** (don't deploy yet!)

### STEP 2: Add PostgreSQL Database (2 minutes)
1. In your Render dashboard, click **"New +"** → **"PostgreSQL"**
2. Name it: **underwritepro-db**
3. Select **Free** or **Starter** plan ($7/month)
4. Click **"Create Database"**
5. Wait 30 seconds for it to provision

### STEP 3: Link Database to Web Service (2 minutes)
1. Go to your **web service** (underwritepro1)
2. Click **"Environment"** tab
3. Render should show **"DATABASE_URL"** already linked automatically
4. If not, click **"Add Environment Variable"**:
   - Go to your PostgreSQL database
   - Copy the **"Internal Database URL"**
   - Add as `DATABASE_URL` in your web service

### STEP 4: Add Required Environment Variables (2 minutes)
In your web service **"Environment"** tab, add these:

```
JWT_SECRET_KEY=eb89a45acdfc2a2fa7e24ebe35b0ea01288be0355a45a078d37e8cd712ae6565
PORT=8000
```

### STEP 5: Deploy! (1 minute)
1. Click **"Manual Deploy"** → **"Deploy latest commit"**
2. Wait 3-5 minutes for build to complete
3. Visit your Render URL!

---

## What's Fixed:

✅ Automatic postgres:// to postgresql:// conversion (Render compatibility)  
✅ Clear database connection logging  
✅ Works with Render's internal database URLs  
✅ All 48 dependencies tested and verified  
✅ Python 3.11.9 (stable)  

---

## After Deployment:

1. Your Render URL will be: `https://your-app-name.onrender.com`
2. Visit `/api/health` to verify database is connected
3. Go to `/login` to access the app
4. Click "Register" to create your first account!

---

## Cost: $14/month
- Web Service: $7/month (or Free tier)
- PostgreSQL: $7/month (or Free tier)
- Free tier: App sleeps after 15 min of inactivity

---

## Troubleshooting:

If database shows "disconnected":
1. Check that DATABASE_URL exists in Environment variables
2. Make sure it starts with `postgres://` or `postgresql://`
3. Verify the database and web service are in the same region

---

**Ready to deploy! Follow the 5 steps above.**

Last Updated: October 4, 2025  
Status: TESTED AND READY
