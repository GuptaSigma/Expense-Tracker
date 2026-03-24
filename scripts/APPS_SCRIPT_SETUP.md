# 📧 Google Apps Script Email Setup

## Quick Setup Guide

### Step 1: Deploy Apps Script

1. Open **[Google Apps Script](https://script.google.com)**
2. Click **"+ New project"**
3. Copy code from `scripts/apps-script-email-service.gs`
4. Paste into the Apps Script editor
5. Click **💾 Save** (name it "ExpenseTracker Email Service")

### Step 2: Deploy as Web App

1. Click **Deploy** → **New deployment**
2. Click **⚙️ gear icon** → Select type: **Web app**
3. Settings:
   - **Description:** "OTP Email Service"
   - **Execute as:** "Me"
   - **Who has access:** "Anyone"
4. Click **Deploy**
5. **Authorize** the app (Grant permissions)
6. **Copy** the deployment URL

### Step 3: Configure Flask App

Add to your `.env` file:
```env
APPS_SCRIPT_URL=https://script.google.com/macros/s/AKfycbxi_W6AtfzN4xADyBzbc0PMZ5Inlg30v3bWmvaWYWTisvjxtvBQYY3ZJgUtt8c3-OUj/exec
```
*(Replace with your actual deployment URL)*

### Step 4: Test

1. Restart your Flask server
2. Register a new user
3. Check your email for OTP! 📬

---

## Priority Options

### 🏆 Option 1: Apps Script (Recommended)
- ✅ FREE
- ✅ No API key needed
- ✅ Uses your Gmail account
- ✅ 100 emails/day limit (enough for small projects)
- ⚠️ Requires Google account

### 🎯 Option 2: Dev Mode (For Testing)
Add to `.env`:
```env
OTP_DEV_MODE=true
```
- OTP prints in terminal/console
- No email sent
- Good for local development

### 💰 Option 3: Resend API (Production)
Add to `.env`:
```env
RESEND_API_KEY=re_xxxxxxxxxxxx
RESEND_FROM_EMAIL=noreply@yourdomain.com
```
- Professional service
- Custom sender domains
- Higher limits
- Costs money

---

## Troubleshooting

### Problem: "Authorization required"
**Solution:** Make sure you authorized the script during deployment

### Problem: "Service invoked too many times"
**Solution:** You hit Gmail's daily limit (100 emails). Wait 24 hours or use Resend API

### Problem: Emails going to spam
**Solution:** Gmail emails are trusted. Check your spam folder once and mark "Not Spam"

### Problem: Script not receiving requests
**Solution:** 
1. Make sure deployment is set to "Anyone" can access
2. Check the deployment URL is correct in `.env`
3. Test with the `testSendEmail()` function in Apps Script

---

## Need Help?

Check logs in Apps Script:
1. Go to your Apps Script project
2. Click **Executions** tab (left sidebar)
3. See recent requests and errors
