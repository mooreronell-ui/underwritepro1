# UnderwritePro SaaS - Production Deployment Guide

## ✅ Production-Ready Deployment

This guide will deploy your UnderwritePro SaaS platform to production in **10 minutes**.

---

## Prerequisites

- GitHub account with repository: `mooreronell-ui/underwritepro1`
- Render account (free): https://render.com
- 10 minutes of time

---

## Deployment Steps

### Step 1: Clean Up Old Deployments (2 minutes)

1. Go to https://dashboard.render.com
2. Delete any existing "underwritepro" services
3. Delete any existing "underwritepro-db" databases
4. Start fresh

### Step 2: Deploy Using Blueprint (5 minutes)

1. Click **"New +"** → **"Blueprint"**
2. Connect GitHub → Select `mooreronell-ui/underwritepro1`
3. Select branch: **`production-clean`**
4. Render will detect `render-production.yaml`
5. Click **"Apply"**

Render will automatically:
- Create web service
- Create PostgreSQL database
- Link them together
- Deploy the application

### Step 3: Verify Deployment (3 minutes)

Wait 3-5 minutes for build to complete, then:

1. **Check Health:**
   - Visit: `https://your-app.onrender.com/api/health`
   - Should show: `{"status":"healthy","database":"connected"}`

2. **Access Login:**
   - Visit: `https://your-app.onrender.com/login`
   - Should see the login page

3. **Create Account:**
   - Click "Register"
   - Fill in your details
   - Create your account

4. **Access Dashboard:**
   - Log in with your credentials
   - Explore the UnderwritePro dashboard

---

## Environment Variables

The following are automatically configured:

- `DATABASE_URL` - Auto-linked from PostgreSQL database
- `JWT_SECRET_KEY` - Auto-generated secure key
- `PORT` - Set to 10000 (Render default)
- `PYTHON_VERSION` - Set to 3.11.9

---

## Optional: Add AI Features

To enable AI bots (Cassie, Sage, Axel), add:

```
OPENAI_API_KEY=your_openai_api_key_here
```

Get your key from: https://platform.openai.com/api-keys

---

## Optional: Add Payment Processing

To enable Stripe payments, add:

```
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
```

Get your keys from: https://dashboard.stripe.com/apikeys

---

## Application URLs

After deployment, your app will be available at:

- **Main App:** `https://underwritepro-saas.onrender.com`
- **API Health:** `/api/health`
- **API Docs:** `/docs`
- **Login:** `/login`
- **Dashboard:** `/dashboard`

---

## Cost

**Free Tier:**
- Web Service: Free (sleeps after 15 min inactivity)
- PostgreSQL: Free (1GB storage, expires after 90 days)

**Paid Tier ($14/month):**
- Web Service: $7/month (always on)
- PostgreSQL: $7/month (persistent, backups)

---

## Support

For issues or questions:
- Check deployment logs in Render dashboard
- Review `/api/health` endpoint for status
- Contact: moore.ronell@gmail.com

---

## Technical Stack

- **Backend:** FastAPI (Python 3.11)
- **Database:** PostgreSQL 17
- **Frontend:** React (served as static files)
- **Hosting:** Render.com
- **Authentication:** JWT tokens
- **API Docs:** OpenAPI/Swagger

---

## Features

✅ User authentication and authorization  
✅ Loan application management  
✅ Document upload and parsing (PDF, Word, Excel)  
✅ Financial analysis and underwriting  
✅ AI-powered bots (optional, requires OpenAI API)  
✅ Payment processing (optional, requires Stripe)  
✅ Real-time notifications  
✅ Multi-user collaboration  
✅ Role-based access control  
✅ Audit logging  
✅ RESTful API  

---

## Next Steps After Deployment

1. **Create your admin account**
2. **Invite team members**
3. **Configure organization settings**
4. **Upload company logo**
5. **Set up payment processing** (if needed)
6. **Enable AI features** (if needed)
7. **Start processing loan applications!**

---

## Maintenance

- **Backups:** Automatic daily backups (paid tier)
- **Updates:** Push to `production-clean` branch to deploy
- **Monitoring:** Check `/api/health` endpoint
- **Logs:** Available in Render dashboard

---

**Your UnderwritePro SaaS platform is now live and ready to serve your clients!** 🎉
