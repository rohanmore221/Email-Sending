# Full-Stack Email Outreach Engine - Implementation Plan

An end-to-end plan to transform the Python mailer into a full-stack web application supporting both **Job Applications** and **Sales / Cold Marketing Campaigns**.

---

## 1. System Vision & Architecture

```
┌────────────────────────────────────────────────────────┐
│                   FRONTEND (React + Vite)              │
│               Port 5173 / Deployed on Vercel           │
├────────────────────────────────────────────────────────┤
│  • Mode Switcher: [ 💼 Job Applications ] | [ 📈 Sales Outreach ]
│  • Drag & Drop Lead Sheet (.xlsx / .csv) with Live Data Grid
│  • Drag & Drop PDF Attachments (Resume / Pitch Deck)
│  • Live Variable-Powered Template & Subject Editor
│  • Real-Time Side-by-Side Email Preview Simulator
│  • 1-Click "Send Test Email to Me"
│  • Live Dispatch Dashboard: Progress Bar, Countdown & Logs
│  • Historical Delivery Audit Table
└───────────────────────────┬────────────────────────────┘
                            │ REST API (JSON / FormData)
                            ▼
┌────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI + Python)           │
│               Port 8000 / Deployed on Render           │
├────────────────────────────────────────────────────────┤
│  • Configuration & SMTP Credential Verifier            │
│  • Universal Excel/CSV Parser with Column Normalizer   │
│  • MIME Email Builder & Jinja2 Dynamic Templating      │
│  • Async Background Task Dispatcher with Jitter Delays │
│  • Anti-Duplicate Tracker & Rate Limiter               │
│  • Live Campaign Progress & Event Stream               │
└────────────────────────────────────────────────────────┘
```

---

## 2. Directory Structure

```text
job-application-mailer/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application entrypoint & CORS
│   │   ├── routes/
│   │   │   ├── config_routes.py # Credentials & settings API
│   │   │   ├── upload_routes.py # Excel/CSV & PDF uploaders
│   │   │   ├── preview_routes.py# Live Jinja2 preview generator
│   │   │   └── campaign_routes.py # Start/Stop/Status dispatch loop
│   │   ├── services/
│   │   │   ├── mailer_service.py   # SMTP engine & MIME builder
│   │   │   ├── parser_service.py   # Excel (.xlsx) & CSV reader
│   │   │   └── tracker_service.py  # sent_history deduplication ledger
│   │   └── schemas/
│   │       └── campaign.py      # Pydantic request/response models
│   ├── requirements.txt         # fastapi, uvicorn, openpyxl, python-multipart, etc.
│   └── .env                     # Credentials (SMTP, Sender details)
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.tsx             # Header with Mode Toggle & SMTP status badge
│   │   │   ├── FileUploadZone.tsx     # Drag & drop for Excel and PDF files
│   │   │   ├── ContactsTable.tsx      # Interactive data table of parsed leads
│   │   │   ├── TemplateEditor.tsx     # Subject & Body editor with variable chips
│   │   │   ├── EmailPreviewSimulator.tsx # Simulated Gmail desktop/mobile preview
│   │   │   ├── CampaignController.tsx # Delay sliders, quota caps, start/stop buttons
│   │   │   ├── LiveProgressPanel.tsx  # Animated progress bar, timer, active contact
│   │   │   ├── TerminalLogs.tsx       # Live status console logs
│   │   │   └── HistoryTable.tsx       # Past delivery records
│   │   ├── services/
│   │   │   └── api.ts                 # Axios / Fetch client for FastAPI
│   │   ├── App.tsx                    # Main dashboard state & tab manager
│   │   ├── index.css                  # Modern styling & design system
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── attachments/                       # Stored PDF resumes / brochures
├── data/                              # Stored excel sheets & sent_history.csv
└── IMPLEMENTATION_PLAN.md
```

---

## 3. Phased Implementation Roadmap

### Phase 1: Backend Foundation (FastAPI)
- [ ] Initialize `backend/` directory and install dependencies (`fastapi`, `uvicorn`, `python-multipart`, `pydantic`).
- [ ] Refactor existing `src/mailer.py`, `src/tracker.py`, and `main.py` into modular FastAPI services.
- [ ] Implement Endpoints:
  - `GET /api/health`: Healthcheck & SMTP status.
  - `POST /api/upload/contacts`: Uploads and parses `.xlsx` or `.csv`, returning normalized rows.
  - `POST /api/upload/attachment`: Saves PDF files with size validation (< 15MB).
  - `POST /api/preview`: Renders HTML and plain-text preview with dynamic fields.
  - `POST /api/test-email`: Sends an immediate verification email with PDF attachment.
  - `POST /api/campaign/start`: Dispatches emails in background task with safety delays (20–40s).
  - `GET /api/campaign/status`: Returns current campaign progress, sent/failed count, and logs.
  - `POST /api/campaign/stop`: Stops/pauses the active campaign.
  - `GET /api/history`: Fetches delivery history from `sent_history.csv`.

### Phase 2: Frontend Foundation (React + Vite + Modern CSS)
- [ ] Initialize React + Vite application inside `frontend/`.
- [ ] Set up modern typography (Inter/Outfit), clean card layouts, and responsive flex/grid.
- [ ] Build **Campaign Switcher Tab**:
  - **Job Mode**: Default subject, B.Tech/SDE body, Resume PDF attachment.
  - **Sales Mode**: Custom B2B pitch, pain point variables, Brochure PDF attachment, auto Unsubscribe line.
- [ ] Build **Drag & Drop Uploaders**:
  - Excel sheet dropzone with instant data table display (Name, Email, Company, Role/Service).
  - PDF attachment dropzone with file size verification chip.
- [ ] Build **Live Email Preview Simulator**:
  - Renders authentic Gmail-like view updating in real-time as the user edits the template.
  - Clickable variable pills: `+ {hr_name}`, `+ {company_name}`, `+ {role}`, `+ {service}`.

### Phase 3: Live Campaign Controller & Execution
- [ ] Build **Control Bar**:
  - Sliders for minimum/maximum delays (e.g. 20–40s).
  - Batch size limiter (e.g. max 30 emails).
  - "Send Test Email to Me" button.
  - "Launch Campaign" primary CTA with confirmation modal.
- [ ] Build **Real-Time Progress & Terminal**:
  - Visual animated progress bar (e.g. `Sent 8 of 25 (32%)`).
  - Next send countdown ticker (`Next email in 26s...`).
  - Terminal stream showing `[SUCCESS] Dispatched to TCS (hr@tcs.com)`.

### Phase 4: Verification & End-to-End Testing
- [ ] Test uploading Excel sheets with missing columns / invalid emails.
- [ ] Test dynamic replacement for both Job Application and Sales formats.
- [ ] Test live sending to test accounts and verify inbox appearance on Gmail mobile and desktop.
- [ ] Verify deduplication (ensuring already-emailed contacts are skipped).

### Phase 5: Cloud Deployment
- [ ] **Backend Deployment (Render.com / Railway)**:
  - Add `Procfile` / startup script.
  - Configure environment variables in cloud dashboard.
  - Enable CORS for the frontend origin.
- [ ] **Frontend Deployment (Vercel)**:
  - Set `VITE_API_BASE_URL` pointing to backend.
  - Build and deploy production bundle with HTTPS.

---

## 4. Execution Start

We are ready to begin with **Phase 1: Backend Setup (FastAPI)**.
Upon your confirmation, we will initialize the `backend/` directory, set up `main.py`, and create the API endpoints.
