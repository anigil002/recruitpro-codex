# Getting Started - Run RecruitPro Locally

This guide will help you run the complete RecruitPro system on your local machine with all features enabled.

## Prerequisites

- **Python 3.11+** (check with `python --version` or `python3 --version`)
- **Node.js 18+** (check with `node --version`)
- **npm 9+** (check with `npm --version`)

---

## Step 1: Install Python Dependencies

```bash
# Navigate to the project directory
cd /home/user/recruitpro-codex

# Upgrade pip
python -m pip install --upgrade pip

# Install the application and dev dependencies
python -m pip install -e .[dev]
```

**What this does:**
- Installs FastAPI, SQLAlchemy, and all backend dependencies
- `-e` flag means "editable" - you can modify code without reinstalling
- `[dev]` includes testing tools like pytest

**Expected output:** Should see "Successfully installed fastapi-X.X.X..." and similar messages

---

## Step 2: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Generate a secure secret key
python -c "from secrets import token_urlsafe; print('RECRUITPRO_SECRET_KEY=' + token_urlsafe(64))"
```

**Copy the output** and paste it into your `.env` file.

### Edit `.env` file:

```bash
nano .env  # or use your preferred editor
```

**Minimal configuration:**
```bash
# Required - Use the secure key generated above
RECRUITPRO_SECRET_KEY=your_generated_key_here

# Database (default SQLite location)
RECRUITPRO_DATABASE_URL=sqlite:///./data/recruitpro.db

# CORS (allows web browser access)
RECRUITPRO_CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000

# Storage for uploads
RECRUITPRO_STORAGE_PATH=storage
```

**Optional - For AI features (Google Gemini):**
```bash
RECRUITPRO_GEMINI_API_KEY=your_google_gemini_key
```

**Optional - For SmartRecruiters integration:**
```bash
RECRUITPRO_SMARTRECRUITERS_EMAIL=your_email
RECRUITPRO_SMARTRECRUITERS_PASSWORD=your_password
RECRUITPRO_SMARTRECRUITERS_COMPANY_ID=your_company_id
```

Save and close the file (Ctrl+X, then Y, then Enter in nano).

---

## Step 3: Create Required Directories

```bash
# Create data directory for database
mkdir -p data

# Create storage directory for uploads
mkdir -p storage
```

---

## Step 4: Initialize Database

```bash
# Create database tables
python -m app.database
```

**Expected output:** Tables created successfully (no errors)

---

## Step 5: Run Tests (Optional but Recommended)

```bash
# Run all tests to verify everything works
pytest

# Or run with verbose output
pytest -v
```

**Expected:** All tests should pass (green checkmarks)

---

## Step 6: Start the Backend Server

### Option A: Direct Python (Simple)

```bash
# Start the FastAPI backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Flags explained:**
- `--host 0.0.0.0` - Makes server accessible from other devices on your network
- `--port 8000` - Uses port 8000
- `--reload` - Auto-restarts when you change code (development mode)

### Option B: Production Mode (No Auto-Reload)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Backend is now running!** You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Step 7: Access the Web Application

Open your browser and navigate to:

### Main Application:
- **http://localhost:8000/app** - Main RecruitPro dashboard

### Other Pages:
- **http://localhost:8000** - Status page (redirects to /app)
- **http://localhost:8000/login** - Login page
- **http://localhost:8000/docs** - Interactive API documentation (Swagger UI)
- **http://localhost:8000/settings** - Integration settings

---

## Step 8: Create Your First Admin User

### Via API (using curl):

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "SecurePassword123!",
    "name": "Admin User",
    "role": "admin"
  }'
```

### Via Web Browser:

1. Go to **http://localhost:8000/app**
2. Click "Register" or open browser console (F12)
3. Run this JavaScript:

```javascript
fetch('http://localhost:8000/api/auth/register', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    email: 'admin@example.com',
    password: 'SecurePassword123!',
    name: 'Admin User',
    role: 'admin'
  })
}).then(r => r.json()).then(console.log)
```

### Then Login:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=SecurePassword123!"
```

**Save the `access_token` from the response** - you'll need it for API calls.

---

## Step 9: Run the Desktop Application (Optional)

If you want to use the Electron desktop app instead of the web browser:

```bash
# Navigate to desktop directory
cd desktop

# Install Node dependencies (first time only)
npm install

# Start the desktop app
npm start
```

**What happens:**
1. Electron launches
2. Automatically starts the Python backend
3. Waits for backend to be healthy
4. Opens the app window
5. Loads http://localhost:8000/app inside the desktop window

**Benefits of desktop app:**
- Native window controls
- System tray integration
- Auto-update capability
- Process monitoring and auto-restart

---

## Accessing Different Features

### 1. API Documentation (Swagger UI)
**URL:** http://localhost:8000/docs

Explore and test all 54+ API endpoints interactively.

### 2. Project Management
**Create a project via API:**
```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Software Engineering Hiring",
    "client": "Acme Corp",
    "summary": "Hiring 5 senior engineers",
    "status": "active"
  }'
```

### 3. Candidate Management
**Add a candidate:**
```bash
curl -X POST http://localhost:8000/api/candidates \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "PROJECT_ID",
    "name": "John Doe",
    "email": "john@example.com",
    "source": "LinkedIn"
  }'
```

### 4. AI Features (Requires Gemini API Key)

**Configure Gemini:**
1. Get API key from https://ai.google.dev/gemini-api/docs/api-key
2. Add to `.env`: `RECRUITPRO_GEMINI_API_KEY=your_key`
3. Restart backend
4. Or set via UI: http://localhost:8000/settings

**Use AI features:**
- AI candidate screening
- Job description generation
- Resume analysis
- Salary benchmarking

### 5. SmartRecruiters Integration

**Configure via UI:**
1. Go to http://localhost:8000/settings
2. Enter SmartRecruiters credentials
3. Save

**Or via .env:**
```bash
RECRUITPRO_SMARTRECRUITERS_EMAIL=your_email
RECRUITPRO_SMARTRECRUITERS_PASSWORD=your_password
RECRUITPRO_SMARTRECRUITERS_COMPANY_ID=your_company_id
```

### 6. Document Upload

**Upload a resume:**
```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@resume.pdf" \
  -F "project_id=PROJECT_ID"
```

Files are stored in `storage/` directory.

### 7. Activity Feed

**View activity log:**
```bash
curl http://localhost:8000/api/activity \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Tracks all actions: logins, project creation, candidate additions, etc.

### 8. Reporting & Analytics

**Get project statistics:**
```bash
curl http://localhost:8000/api/reporting/project/PROJECT_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Troubleshooting

### Backend won't start

**Error: "No module named 'fastapi'"**
```bash
# Dependencies not installed
python -m pip install -e .[dev]
```

**Error: "Address already in use"**
```bash
# Port 8000 is taken, use a different port
uvicorn app.main:app --port 8001
```

**Error: "Permission denied: 'data'"**
```bash
# Create directories
mkdir -p data storage
```

### Desktop app won't start

**Error: "Cannot find module 'electron'"**
```bash
cd desktop
npm install
```

**Error: "Backend not responding"**
```bash
# Check if Python is available
which python3
# Set custom Python path
export ELECTRON_PYTHON=/usr/bin/python3
npm start
```

### Database errors

**Error: "no such table: users"**
```bash
# Initialize database
python -m app.database
```

**Reset database (WARNING: deletes all data):**
```bash
rm data/recruitpro.db
python -m app.database
```

### Tests failing

```bash
# Install dev dependencies
python -m pip install -e .[dev]

# Run with verbose output to see errors
pytest -v --tb=short
```

---

## Development Workflow

### Making Code Changes

1. **Edit backend code** in `app/` directory
2. **Auto-reload** happens automatically (if using `--reload` flag)
3. **Test your changes:**
   ```bash
   pytest tests/test_your_feature.py
   ```

### Adding New Features

1. **Create new router** in `app/routers/`
2. **Add models** in `app/models/__init__.py`
3. **Register router** in `app/main.py`:
   ```python
   from .routers import your_new_router
   app.include_router(your_new_router.router)
   ```
4. **Add tests** in `tests/test_your_feature.py`

### Viewing Logs

**Backend logs:**
- Printed to console where uvicorn is running
- Check for errors, warnings, and info messages

**Desktop logs:**
- **Location:** `~/.config/RecruitPro Desktop/logs/` (Linux)
- **Location:** `~/Library/Logs/RecruitPro Desktop/` (macOS)
- **Location:** `%APPDATA%\RecruitPro Desktop\logs\` (Windows)

---

## Production Deployment

### Create Lock Files

```bash
# Python lock file
pip freeze > requirements.txt

# Node lock file (created automatically)
cd desktop
npm install  # creates package-lock.json
```

### Build Desktop Installers

```bash
cd desktop

# Build for your platform
npm run make

# Output in desktop/dist/
```

**Installers created:**
- **macOS:** `.dmg` file
- **Windows:** `.exe` installer
- **Linux:** `.AppImage` and `.deb` packages

---

## Quick Reference

### Start Backend (Web Access)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Start Desktop App
```bash
cd desktop && npm start
```

### Run Tests
```bash
pytest
```

### View API Docs
```
http://localhost:8000/docs
```

### Access Application
```
http://localhost:8000/app
```

---

## Next Steps

1. ✅ Follow steps 1-8 to get running
2. 📖 Read `recruitpro_system_v2.5.md` for detailed feature documentation
3. 🧪 Explore API at http://localhost:8000/docs
4. 🎨 Customize templates in `templates/` directory
5. 🔧 Add integrations via http://localhost:8000/settings

**Need help?** Check `PRODUCTION_READINESS_REPORT.md` for detailed system analysis.

---

**Congratulations!** You now have a fully functional RecruitPro ATS system running locally. 🎉
