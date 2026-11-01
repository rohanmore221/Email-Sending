# Full-Stack Job Application Mailer - Architecture & Deployment Guide

This document outlines the full-stack architecture, API design, frontend components, and deployment steps to turn the Python Job Application Mailer into a modern web application hosted on cloud platforms.

---

## 1. System Architecture

```
┌────────────────────────────────────────────────────────┐
│               FRONTEND (React / Next.js)              │
│               Hosted on Vercel (Free)                  │
├────────────────────────────────────────────────────────┤
│  • Drag & Drop Excel Sheet (.xlsx / .csv)              │
│  • Drag & Drop Resume PDF (with preview)               │
│  • Interactive Template & Role Editor                  │
│  • One-Click "Send Test Email"                         │
│  • Live Campaign Dispatcher & Real-Time Progress Bar   │
│  • Real-Time Activity Logs & Sent History Table        │
└───────────────────────────┬────────────────────────────┘
                            │ HTTPS / REST API / SSE
                            ▼
┌────────────────────────────────────────────────────────┐
│                 BACKEND (FastAPI / Python)             │
│            Hosted on Render / Railway (Free)           │
├────────────────────────────────────────────────────────┤
│  • /api/upload/excel     - Parses & validates contacts │
│  • /api/upload/resume    - Stores & validates PDF      │
│  • /api/preview          - Live Jinja2 preview         │
│  • /api/test-email       - Dispatches test to self     │
│  • /api/campaign/start   - Async background sender     │
│  • /api/campaign/status  - Live progress & logs stream │
│  • /api/history          - Delivery logs audit table   │
└────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

| Layer | Technology | Hosting / Platform |
| :--- | :--- | :--- |
| **Frontend** | React (Vite) / Next.js, Tailwind CSS, Lucide Icons | **Vercel** (Free Tier with automated CI/CD) |
| **Backend** | Python, FastAPI, Uvicorn, Jinja2, openpyxl | **Render.com** or **Railway.app** (Free Web Service) |
| **SMTP Delivery**| Gmail SMTP (SSL 465 / TLS 587) with App Passwords | Google Mail Infrastructure |
| **Storage** | Ephemeral or SQLite / Supabase for audit logs | Cloud Database / Local SQLite |

---

## 3. Backend API Specifications (FastAPI)

### Core Endpoints

#### `POST /api/upload/excel`
- **Payload**: `multipart/form-data` with `.xlsx` or `.csv` file.
- **Response**: List of parsed recipients with columns normalized (`hr_email`, `company_name`, `hr_name`, `job_role`).
- **Validation**: Verifies valid email formats and non-empty recipient lists.

#### `POST /api/upload/resume`
- **Payload**: `multipart/form-data` with PDF file.
- **Response**: Filename, file size, and upload confirmation.
- **Validation**: Checks file type (`.pdf`) and enforces a 15MB size ceiling.

#### `POST /api/preview`
- **Payload**: `{ recipient: { hr_email, company_name, hr_name, job_role }, template: { subject, body } }`
- **Response**: Rendered subject, HTML body preview, and plain-text fallback preview.

#### `POST /api/test-email`
- **Payload**: `{ test_email: "user@gmail.com" }`
- **Action**: Immediately sends an email with the uploaded resume attached to verify credentials and inbox appearance.

#### `POST /api/campaign/start`
- **Payload**: `{ batch_limit: 30, min_delay: 20, max_delay: 40 }`
- **Action**: Launches asynchronous background task executing the delivery loop with jitter delays and deduplication checks.

#### `GET /api/campaign/status`
- **Response**:
  ```json
  {
    "status": "RUNNING",
    "total": 25,
    "sent": 12,
    "failed": 0,
    "current_recipient": "recruiter@company.com",
    "next_send_in_seconds": 24,
    "logs": [
      "[SUCCESS] Sent to TCS (kaustubh5147@gmail.com)",
      "[INFO] Waiting 28.4s to protect sender reputation..."
    ]
  }
  ```

#### `GET /api/history`
- **Response**: Historical array of sent emails from `sent_history.csv` / database.

---

## 4. Frontend Component Blueprint

```text
frontend/src/
├── components/
│   ├── Header.tsx             # App title, sender badge & status indicator
│   ├── ConfigModal.tsx        # Secure modal to enter App Password & sender details
│   ├── FileUploadZone.tsx     # Dual drag-and-drop for Excel sheet and PDF resume
│   ├── RecipientTable.tsx     # Interactive data grid showing parsed HR contacts
│   ├── TemplateEditor.tsx     # Live editor with variable insertion ({hr_name}, {role})
│   ├── PreviewModal.tsx       # Side-by-side Desktop/Mobile email simulator
│   ├── CampaignController.tsx # Controls (Start, Pause, Stop, Batch Limit slider)
│   ├── LiveProgressBar.tsx    # Visual progress bar with estimated completion time
│   └── LogsViewer.tsx         # Terminal-style live console feed
├── hooks/
│   ├── useCampaign.ts         # Hook polling/streaming campaign status
│   └── useFileUpload.ts       # Hook handling drag-and-drop file validations
├── App.tsx                    # Main layout dashboard
└── main.tsx
```

---

## 5. Deployment Step-by-Step Guide

### Part A: Deploying Backend on Render.com (or Railway)

1. **Verify Your Repository on GitHub**:
   - Repository: `https://github.com/rohanmore221/Email-Sending`
   - Ensure the `main` branch is pushed without any committed secrets (`.env` is in `.gitignore`).

2. **Create Web Service on Render**:
   - Log in to [Render.com](https://render.com) and click **New +** -> **Web Service**.
   - Connect your GitHub repository `rohanmore221/Email-Sending`.
   - Configure the service settings:
     - **Name**: `job-mailer-api` (or your preferred name)
     - **Region**: Closest to your location (e.g., Singapore or Frankfurt)
     - **Branch**: `main`
     - **Root Directory**: leave blank (root contains `server.py` and `requirements.txt`)
     - **Runtime / Environment**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
     - **Plan**: `Free`

3. **Set Environment Variables in Render Dashboard**:
   Under **Environment Variables**, add the following keys and values:
   - `FRONTEND_URL`: `https://<your-vercel-app-domain>.vercel.app`
   - `GOOGLE_CLIENT_ID`: `<your-google-client-id>`
   - `GOOGLE_CLIENT_SECRET`: `<your-google-client-secret>`
   - `GOOGLE_REDIRECT_URI`: `https://job-mailer-api.onrender.com/api/auth/google/callback`
   - `SMTP_HOST`: `smtp.gmail.com`
   - `SMTP_PORT`: `587`
   - `SMTP_USER`: `rohanmore151@gmail.com`
   - `SMTP_PASSWORD`: `<your-16-character-app-password>`
   - `SENDER_NAME`: `Rohan More`
   - `SENDER_PHONE`: `+91-8652492520`
   - `SENDER_LINKEDIN`: `https://www.linkedin.com/in/rohan-sambhaji-more-72497121b/`
   - `SENDER_GITHUB`: `https://github.com/rohanmore221`

4. Click **Create Web Service**. Render will build and deploy your API:
   Your backend URL will look like: `https://job-mailer-api.onrender.com`

---

### Part B: Deploying Frontend on Vercel (Free)

1. **Log in to [Vercel.com](https://vercel.com)**:
   - Click **Add New...** -> **Project**.
   - Select your GitHub repository: `rohanmore221/Email-Sending`.

2. **Configure Project Settings in Vercel**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click *Edit* and select **`frontend`** (crucial!).
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `dist` (default)
   - **Environment Variables**:
     - Key: `VITE_API_BASE_URL`
     - Value: `https://job-mailer-api.onrender.com/api` (replace with your Render backend URL)

3. Click **Deploy**. Vercel will build and assign you a live production URL:
   `https://job-application-mailer-rohan.vercel.app`

---

### Part C: Configure Google Cloud OAuth for Production

To allow 1-click Google OAuth sign-in in production:
1. Go to [Google Cloud Console](https://console.cloud.google.com/) -> **APIs & Services** -> **Credentials**.
2. Select your OAuth 2.0 Client ID.
3. Under **Authorized JavaScript origins**, add:
   - `https://<your-vercel-app-domain>.vercel.app`
4. Under **Authorized redirect URIs**, add:
   - `https://job-mailer-api.onrender.com/api/auth/google/callback`
5. Save changes. OAuth will now seamlessly authorize your live application!

---

## 6. Security & Anti-Abuse Measures for Web Deployment

1. **Authentication Gate**: Add a simple master password or PIN protection to your web dashboard so unauthorized visitors cannot trigger emails from your Gmail account.
2. **CORS Restrictions**: Configure FastAPI CORS middleware to only accept requests originating from your Vercel frontend URL.
3. **Session Rate Limiting**: Limit API requests to prevent accidental spam triggers.
4. **Credential Isolation**: Store App Passwords securely in server environment variables, never exposed in client-side JavaScript.
