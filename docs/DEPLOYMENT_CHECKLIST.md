# Deployment Checklist

Copy this checklist and mark items as you complete them.

## Pre-Deployment (Already Done ✅)
- [x] Add rate limiting with slowapi
- [x] Create health check endpoint
- [x] Create Dockerfile
- [x] Create render.yaml
- [x] Update DEPLOYMENT.md
- [x] Fix bugs (chat_message parameters)
- [x] Push to GitHub

## Backend Deployment (Render)

### Setup
- [ ] Create Render account at https://dashboard.render.com/
- [ ] Click "New +" → "Web Service"
- [ ] Connect your GitHub repository
- [ ] Select `main` branch

### Configuration
- [ ] Name: `paperstack-backend` (or your choice)
- [ ] Runtime: Python 3
- [ ] Build Command: `cd backend && pip install -r requirements.txt`
- [ ] Start Command: `cd backend && gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120`
- [ ] Plan: Free

### Environment Variables
Add these in Render dashboard:
- [ ] `DATABASE_TYPE` = `postgres`
- [ ] `DATABASE_URL` = `postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`
  - Get from Supabase: Dashboard → Settings → Database → Connection String
- [ ] `GOOGLE_API_KEY1` = your Google API key 1
- [ ] `GOOGLE_API_KEY2` = your Google API key 2
- [ ] `GOOGLE_API_KEY3` = your Google API key 3 (optional)
- [ ] `OPENAI_API_KEY` = your OpenAI API key
- [ ] `ACCESS_TOKEN` = create a secure random token (not "welcometopaperstack1"!)

### Deploy & Verify
- [ ] Click "Create Web Service"
- [ ] Wait for "Live" status (~5-10 minutes)
- [ ] Copy your backend URL: `https://paperstack-backend.onrender.com`
- [ ] Test health check:
  ```bash
  curl https://paperstack-backend.onrender.com/health
  ```
- [ ] Verify response shows `"status": "healthy"` and `"database": "connected"`

## Frontend Deployment (Vercel)

### Setup
- [ ] Create Vercel account at https://vercel.com/dashboard
- [ ] Click "Add New..." → "Project"
- [ ] Import your GitHub repository
- [ ] Framework preset: Next.js
- [ ] Root directory: `frontend`

### Environment Variables
Add these in Vercel:
- [ ] `NEXT_PUBLIC_API_URL` = `https://paperstack-backend.onrender.com` (your Render URL)
- [ ] `NEXT_PUBLIC_ACCESS_TOKEN` = same token you set in Render backend

### Deploy & Verify
- [ ] Click "Deploy"
- [ ] Wait for deployment (~2-3 minutes)
- [ ] Copy your frontend URL: `https://paperstack.vercel.app`
- [ ] Open URL in browser
- [ ] Enter your access token
- [ ] Verify login works

## Post-Deployment

### Update Backend CORS
- [ ] Open `backend/main.py`
- [ ] Find `allow_origins` list (around line 160)
- [ ] Verify your Vercel URL is included
- [ ] If not, add it:
  ```python
  "https://paperstack.vercel.app",  # Your production URL
  ```
- [ ] Commit and push:
  ```bash
  git add backend/main.py
  git commit -m "Update CORS with production Vercel URL"
  git push
  ```
- [ ] Wait for Render auto-deploy (~2 minutes)

### Test Complete Flow
- [ ] Go to your Vercel URL
- [ ] Enter access token and log in
- [ ] Test Paper Brain search
- [ ] Test loading papers
- [ ] Test Paper Chat

### Monitor
- [ ] Check Render logs for errors
- [ ] Check Vercel deployment logs
- [ ] Test rate limiting (try > 10 searches in a minute)
- [ ] Verify health endpoint still returns healthy

## Troubleshooting

### Backend Issues
If backend won't start:
- [ ] Check Render logs for errors
- [ ] Verify all environment variables are set
- [ ] Test DATABASE_URL connection locally:
  ```bash
  psql "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
  ```
- [ ] Check Supabase project is not paused

### Frontend Issues
If frontend shows CORS errors:
- [ ] Verify Vercel URL is in backend CORS origins
- [ ] Check backend is running (visit /health)
- [ ] Verify API_URL in Vercel env vars is correct

### Rate Limiting Issues
If getting 429 errors too often:
- [ ] Check Render logs for rate limit messages
- [ ] Adjust limits in backend/main.py if needed
- [ ] Redeploy backend

## Final Checks
- [ ] Health check returns healthy: `/health`
- [ ] Can search papers
- [ ] Can load papers
- [ ] Can chat with papers
- [ ] Rate limiting works (blocks after limit)
- [ ] Logs are being saved
- [ ] No errors in Render/Vercel dashboards

## Cost Monitoring

Track these monthly:
- [ ] Render: 750 hours used (check dashboard)
- [ ] Vercel: Bandwidth usage (check dashboard)
- [ ] Supabase: Database size (check dashboard)
- [ ] OpenAI: Token usage (check usage page)
- [ ] Google: Search API calls (check console)

## Done! 🎉

Your app is live at:
- Backend: `https://paperstack-backend.onrender.com`
- Frontend: `https://paperstack.vercel.app`

---

**Need Help?**
- Render docs: https://render.com/docs
- Vercel docs: https://vercel.com/docs
- See DEPLOYMENT.md for detailed troubleshooting
