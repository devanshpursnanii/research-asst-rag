# PaperStack Authentication Guide

## Overview
PaperStack now has token-based authentication to control access. Only users with the correct access token can use the application.

## Current Access Token
**Current Token:** `welcometopaperstack1`

## How It Works

### Backend Protection
- All API endpoints are protected by authentication middleware
- Requests must include: `Authorization: Bearer <token>` header
- Exception endpoints (no auth required):
  - `/auth/validate` - Validates tokens
  - `/` - Root endpoint
  - `/docs`, `/openapi.json`, `/redoc` - API documentation

### Frontend Flow
1. User visits the site → sees greyscale overlay with login modal
2. User enters access token → frontend validates with `/auth/validate`
3. If valid → token stored in localStorage, full access granted
4. All API requests include `Authorization: Bearer <token>` header
5. If backend returns 401 → token cleared, user redirected to login

## Changing the Access Token (Post-Deployment)

### For Railway/Render Deployments

#### Step 1: Update Backend Environment Variable
1. Log into your deployment dashboard (Railway/Render)
2. Navigate to your backend service
3. Go to Environment Variables / Config Vars
4. Update `ACCESS_TOKEN` to your new token value
5. Save changes

#### Step 2: Restart Backend
- **Railway**: Auto-restarts on env var change
- **Render**: May need manual restart (click "Manual Deploy" → "Deploy Latest")

#### Step 3: User Impact
- All existing users will be logged out (their old tokens won't work)
- They'll see the login screen again
- They need to enter the new token to access the app

### For Vercel Frontend
**No changes needed!** The frontend automatically uses whatever token the backend accepts.

### For Local Development
1. Update `.env` file:
   ```bash
   ACCESS_TOKEN=your_new_token_here
   ```
2. Restart backend server:
   ```bash
   cd /Users/apple/Desktop/paperstack
   /Users/apple/Desktop/paperstack/venv/bin/python backend/main.py
   ```

## Testing Authentication

### Test Valid Token
```bash
curl -X POST http://localhost:8000/auth/validate \
  -H "Content-Type: application/json" \
  -d '{"token":"welcometopaperstack1"}'
```
Expected: `{"valid":true,"message":"Token is valid"}`

### Test Invalid Token
```bash
curl -X POST http://localhost:8000/auth/validate \
  -H "Content-Type: application/json" \
  -d '{"token":"wrongtoken"}'
```
Expected: `{"valid":false,"message":"Invalid token"}`

### Test Protected Endpoint Without Token
```bash
curl http://localhost:8000/health
```
Expected: `{"error":"Missing or invalid authorization header","error_type":"unauthorized"}`

### Test Protected Endpoint With Token
```bash
curl http://localhost:8000/health \
  -H "Authorization: Bearer welcometopaperstack1"
```
Expected: `{"error":"Missing or invalid authorization header","error_type":"unauthorized"}` 
(Health endpoint is protected but doesn't return data - just validates auth)

## Security Best Practices

1. **Use Strong Tokens**: Generate random strings, not dictionary words
   ```bash
   # Generate a secure token on macOS/Linux:
   openssl rand -base64 32
   ```

2. **Rotate Tokens Regularly**: Change the token every few months

3. **Keep Tokens Secret**: Never commit tokens to Git
   - Tokens are in `.env` (gitignored)
   - Set tokens via deployment dashboard only

4. **Monitor Access**: Check backend logs for suspicious activity

5. **Different Tokens Per Environment**:
   - Development: Simple token for testing
   - Production: Strong random token
   - Staging: Different token from production

## Token Storage

### Backend
- Stored in environment variable: `ACCESS_TOKEN`
- Loaded at startup via `python-dotenv`
- Located in: `.env` (local) or deployment dashboard (production)

### Frontend
- Stored in browser `localStorage` as `paperstack_token`
- Cleared on logout or 401 errors
- Sent with every API request in `Authorization` header

## Troubleshooting

### Users Can't Log In
1. Check backend logs for errors
2. Verify `ACCESS_TOKEN` is set correctly in deployment
3. Test with curl to isolate frontend vs backend issues

### Backend Returns 401 on All Requests
1. Verify `ACCESS_TOKEN` environment variable is set
2. Check backend logs for "ACCESS_TOKEN not set" warnings
3. Restart backend after setting env vars

### Frontend Stuck on Login Screen
1. Open browser console (F12) → check for errors
2. Verify backend is running and accessible
3. Test `/auth/validate` endpoint directly with curl

### Token Not Working After Update
1. Clear browser localStorage (F12 → Application → Local Storage → Clear)
2. Try logging in with the new token
3. Verify backend restarted after env var change

## Files Modified for Authentication

### Backend
- `.env` - Added `ACCESS_TOKEN=welcometopaperstack1`
- `backend/main.py` - Added auth middleware, `/auth/validate` endpoint

### Frontend
- `frontend/components/AuthGuard.tsx` - New login overlay component
- `frontend/lib/api.ts` - Modified to include `Authorization` header
- `frontend/app/layout.tsx` - Wrapped app with `<AuthGuard>`

### Documentation
- `.env.example` - Added `ACCESS_TOKEN` template
- `AUTH_GUIDE.md` - This guide
