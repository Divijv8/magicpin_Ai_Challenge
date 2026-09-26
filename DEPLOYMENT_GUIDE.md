# 🚀 Vera Bot — Deployment & Submission Guide

This document answers your platform questions and gives step-by-step instructions to deploy your bot, get a public HTTPS submission URL, and submit to the magicpin challenge.

---

## 🎯 Is Vercel a Good Choice? (Platform Recommendation)

### Direct Answer:
- **Vercel works**, but **Render.com** or **Railway.app** is **strongly recommended** for this specific challenge.

### Why?
The challenge harness tests your bot over a **60-minute simulated window** where the AI judge pushes contexts and polls `/v1/healthz` every 60 seconds:
1. **Vercel (Serverless)**: Serverless functions spin down after inactivity (cold starts) and have a strict execution timeout (10s on Hobby tier). We have added SQLite persistence (`vera_state.db`) and `vercel.json` so it runs on Vercel, but cold starts can occasionally cause minor latency.
2. **Render.com / Railway.app / Koyeb (Continuous Container — Recommended)**:
   - Runs a 24/7 persistent FastAPI process (`uvicorn bot:app`).
   - Zero cold starts, instant response times (<20ms).
   - Completely free tier.
   - You get a public URL like `https://vera-bot.onrender.com` in 2 minutes.

---

## 🛠️ Option A: Deploy on Render (Recommended — 2 Minutes, Free)

1. Push your repository to **GitHub**:
   ```powershell
   git init
   git add .
   git commit -m "feat: complete Vera AI Assistant with modern frontend and 4-context engine"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/magicpin_Ai_Challenge.git
   git push -u origin main
   ```

2. Go to [render.com](https://render.com) and log in with GitHub.
3. Click **"New +"** → **"Web Service"**.
4. Select your `magicpin_Ai_Challenge` repository.
5. Set the settings:
   - **Name**: `magicpin-vera-bot`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn bot:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
6. Under **Environment Variables**, add:
   - `GEMINI_API_KEY`: `your_gemini_api_key_here` (Optional)
7. Click **"Create Web Service"**.
8. Once deployed, Render gives you a public HTTPS URL (e.g., `https://magicpin-vera-bot.onrender.com`).
   - **Submission URL to paste**: `https://magicpin-vera-bot.onrender.com`

---

## ⚡ Option B: Deploy on Railway (Super Fast — 1 Minute)

1. Go to [railway.app](https://railway.app) and log in with GitHub.
2. Click **"New Project"** → **"Deploy from GitHub repo"**.
3. Select your repository.
4. Railway automatically detects Python, installs `requirements.txt`, and runs `Procfile`.
5. Under **Variables**, add `GEMINI_API_KEY` (optional).
6. Under **Settings** → **Networking**, click **"Generate Domain"** to get your public URL (e.g., `https://magicpin-vera-bot.up.railway.app`).
   - **Submission URL to paste**: `https://magicpin-vera-bot.up.railway.app`

---

## ▲ Option C: Deploy on Vercel

If you prefer Vercel, we have already prepared [`vercel.json`](file:///c:/Users/divij/projects/magicpin_Ai_Challenge/vercel.json) for you:

1. Push to GitHub.
2. Go to [vercel.com](https://vercel.com) and click **"Add New..."** → **"Project"**.
3. Import your GitHub repository.
4. Under **Environment Variables**, add:
   - `GEMINI_API_KEY`: `your_gemini_api_key_here`
5. Click **"Deploy"**.
6. Vercel will deploy your FastAPI app and provide a URL like `https://magicpin-vera-bot.vercel.app`.
   - **Submission URL to paste**: `https://magicpin-vera-bot.vercel.app`

---

## 📝 Filling the Submission Form

In the submission portal (shown in your screenshot):

| Field | Value |
|---|---|
| **Full name** | Your Name |
| **Email** | Your Email |
| **Phone number** | Your Phone Number |
| **Submission URL** | `https://your-app.onrender.com` (or your Railway/Vercel base URL) |
| **LinkedIn URL** | Your LinkedIn Profile (Optional) |

> **Note**: Enter only the **base URL** (e.g. `https://your-app.onrender.com`), without `/v1/context` or trailing slash. The judge harness automatically appends `/v1/context`, `/v1/tick`, `/v1/reply`, `/v1/healthz`, `/v1/metadata`.

---

## 🎨 Interactive Frontend Dashboard

When anyone visits your base URL in a browser (e.g. `https://your-app.onrender.com/`), they will see the **Vera Apex Glassmorphic Web Dashboard**:
- 🟢 **Live System Health & Loaded Context Counters**
- 📱 **Interactive WhatsApp Phone Simulator** with real-time multi-turn chat
- ⚡ **5-Dimension Rubric Scorecard (50/50 Quality Breakdown)**
- 📋 **Canonical 30-Test Set Explorer**
- 📋 **1-Click "Copy Submission URL" button**
