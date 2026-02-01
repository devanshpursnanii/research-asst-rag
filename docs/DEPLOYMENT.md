# PaperStack Deployment Guide - Render + Vercel

## ✅ Pre-Deployment Complete

- [x] Rate limiting implemented (slowapi)
- [x] Health check endpoint at `/health`
- [x] Dockerfile created
- [x] render.yaml configured
- [x] DATABASE_TYPE set to postgres
- [x] CORS configured for Vercel

## Environment Variables for Backend

### Required for Render Deployment
```bash
# Database
DATABASE_TYPE=postgres
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# Google API Keys
GOOGLE_API_KEY1=your_gemini_api_key_1
GOOGLE_API_KEY2=your_gemini_api_key_2
GOOGLE_API_KEY3=your_gemini_api_key_3  # Optional, for rotation

# Authentication
ACCESS_TOKEN=your_secure_random_token  # Change from default!

# OpenAI (for RAG embeddings)
OPENAI_API_KEY=your_openai_api_key
```

## Part 1: Deploy Backend to Render (Free Tier)

### Step 1: Create Web Service

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `paperstack-backend`
   - **Root Directory**: Leave empty
   - **Build Command**: `cd backend && pip install -r requirements.txt`
   - **Start Command**: `cd backend && gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120`
   - **Plan**: Free

### Step 2: Set Environment Variables

Add all variables from section above in Render dashboard under "Environment".

**Get Supabase DATABASE_URL:**
1. Supabase Dashboard → Project Settings → Database
2. Copy "Connection String" (URI format)
3. Format: `postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`

### Step 3: Deploy & Verify

1. Click **"Create Web Service"**
2. Wait for "Live" status (5-10 minutes)
3. Test health: `curl https://paperstack-backend.onrender.com/health`

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "api_keys": "configured"
}
```

## Part 2: Deploy Frontend to Vercel

### Step 1: Deploy

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **"Add New..."** → **"Project"**
3. Import your GitHub repo
4. Configure:
   - **Root Directory**: `frontend`
   - **Framework**: Next.js
5. Add Environment Variables:
   - `NEXT_PUBLIC_API_URL` = `https://paperstack-backend.onrender.com`
   - `NEXT_PUBLIC_ACCESS_TOKEN` = `<same_token_as_backend>`
6. Deploy

### Step 2: Update Backend CORS

After getting Vercel URL, update `backend/main.py` CORS origins to include your production URL, then:

```bash
git add .
git commit -m "Update CORS with Vercel production URL"
git push
```

Render auto-deploys.

## Rate Limiting (Already Implemented)

| Endpoint | Limit | Purpose |
|----------|-------|---------|
| `/brain/search` | 10/minute | Prevent API quota abuse |
| `/brain/load` | 5/minute | Protect database writes |
| `/chat/message` | 20/minute | Balance UX & cost |

## Free Tier Limits

**Render:**
- Sleeps after 15 min inactivity
- 30s cold start
- 750 hours/month

**Vercel:**
- 100 GB bandwidth/month
- Serverless functions: 10s timeout

## Troubleshooting

### Backend won't start
- Check Render logs
- Verify all env vars set
- Test DATABASE_URL locally

### CORS errors
- Add Vercel URL to CORS origins
- Redeploy backend

### Rate limiting
- Tracked by IP via `X-Forwarded-For`
- Check logs for rate limit exceeded

## Cost Monitoring

Free tier costs:
- Render: $0
- Vercel: $0
- Supabase: $0 (up to 500 MB)
- OpenAI: ~$0.01/1K tokens
- Google Search: Free (100 queries/day)

---### Railway
1. Dashboard → Your Service → Variables
2. Update `ACCESS_TOKEN` value
3. Auto-redeploys on save

### Render
1. Dashboard → Your Service → Environment
2. Update `ACCESS_TOKEN` value
3. Save → Manual Deploy

### Result
- All users logged out automatically
- Must enter new token to access app

## Database Setup (Supabase)

### Initial Setup
1. Create Supabase project
2. Go to Project Settings → Database
3. Copy connection pooler details (not direct connection!)
4. Run `backend/db/schema_postgres.sql` in SQL Editor
5. Set environment variables (pooler credentials)

### Connection Pooler (Recommended)
- **Host**: `aws-1-ap-south-1.pooler.supabase.com`
- **Port**: `6543`
- **User**: `postgres.<project_ref>`
- **Mode**: Session pooling
- Better for production deployments

## Local Development

### Start Backend
```bash
cd /Users/apple/Desktop/paperstack
/Users/apple/Desktop/paperstack/venv/bin/python backend/main.py
```
Runs on: http://localhost:8000

### Start Frontend
```bash
cd /Users/apple/Desktop/paperstack/frontend
npm run dev
```
Runs on: http://localhost:3000

## Testing Authentication

### Valid Token
```bash
curl -X POST http://localhost:8000/auth/validate \
  -H "Content-Type: application/json" \
  -d '{"token":"welcometopaperstack1"}'
```
Response: `{"valid":true,"message":"Token is valid"}`

### Protected Endpoint
```bash
curl -X POST http://localhost:8000/session/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer welcometopaperstack1" \
  -d '{"initial_query":"test"}'
```

## Security Recommendations

1. **Change Default Token**: Replace `welcometopaperstack1` with secure random token
2. **Generate Secure Token**:
   ```bash
   openssl rand -base64 32
   ```
3. **Rotate Regularly**: Update token every 2-3 months
4. **Never Commit**: Keep `.env` gitignored
5. **Use Different Tokens**: Dev vs Production vs Staging

## Monitoring

### Check Backend Logs
- **Railway**: Dashboard → Deployments → View Logs
- **Render**: Dashboard → Logs

### Check Failed Auth Attempts
Look for: `"Unauthorized access attempt"` in logs

## Troubleshooting

### 401 Errors on All Requests
- Verify `ACCESS_TOKEN` is set in deployment
- Check backend logs for startup errors
- Test `/auth/validate` endpoint directly

### Frontend Not Loading
- Check `NEXT_PUBLIC_API_URL` is correct
- Verify backend is accessible from frontend domain
- Check CORS settings in `backend/main.py`

### Database Connection Errors
- Use session pooler, not direct connection
- Verify Supabase credentials
- Check if database tables exist (run schema_postgres.sql)

## URLs Reference

### Local Development
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Backend Docs: http://localhost:8000/docs

### Production (Example)
- Frontend: https://paperstack.vercel.app
- Backend: https://paperstack-backend.railway.app
- Backend Docs: https://paperstack-backend.railway.app/docs
