# Quick Access Reference

## 🎉 Your RecruitPro System is RUNNING!

The backend server is currently running on **http://localhost:8000**

---

## 🔐 Admin Credentials

**Email:** admin@example.com
**Password:** Admin123

---

## 🌐 Access Links

### Main Application
- **Dashboard:** http://localhost:8000/app
- **Login Page:** http://localhost:8000/login
- **Settings:** http://localhost:8000/settings

### API & Documentation
- **API Docs (Swagger):** http://localhost:8000/docs
- **API Health Check:** http://localhost:8000/api/health
- **API Version:** http://localhost:8000/api/version

### Your Access Token
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjMjljMjQ4Y2FhNTI0ZDdlYjMyZDNkYjAzODJlYTgxZCIsImV4cCI6MTc2MTYxMTM2OX0.JcCgW34JfOUc5U_VyfCDE3M2LPtrIRei5Y6IH5MlHxI
```

Use this token in API requests:
```bash
curl http://localhost:8000/api/user \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## 🚀 Quick Start Commands

### Create a Project
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

### Add a Candidate
```bash
curl -X POST http://localhost:8000/api/candidates \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "PROJECT_ID_HERE",
    "name": "John Doe",
    "email": "john@example.com",
    "source": "LinkedIn"
  }'
```

### List Your Projects
```bash
curl http://localhost:8000/api/projects \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📁 File Locations

- **Database:** `/home/user/recruitpro-codex/data/recruitpro.db`
- **Uploads:** `/home/user/recruitpro-codex/storage/`
- **Config:** `/home/user/recruitpro-codex/.env`
- **Logs:** Console output (where uvicorn is running)

---

## ✅ Setup Status

✅ Python dependencies installed
✅ Environment configured (.env)
✅ Database initialized
✅ All 29 tests passing
✅ Backend server running
✅ Admin user created

---

## 🔧 Server Management

### Check if server is running
```bash
curl http://localhost:8000/api/health
```

### View server logs
The server is running in background process. Check console output.

### Stop the server
```bash
# Find the process
ps aux | grep uvicorn

# Kill it
kill <PID>
```

### Restart the server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🎨 Enable AI Features

### Option 1: Via Web UI
1. Go to http://localhost:8000/settings
2. Enter your Gemini API key
3. Save

### Option 2: Via Environment Variable
Edit `.env` file:
```bash
RECRUITPRO_GEMINI_API_KEY=your_api_key_here
```

Get a free API key: https://ai.google.dev/gemini-api/docs/api-key

### AI Features Available:
- AI candidate screening
- Job description generation
- Resume analysis
- Candidate scoring
- Salary benchmarking
- Market research

---

## 📚 Documentation

- **Full Setup Guide:** `GETTING_STARTED.md`
- **Production Readiness Report:** `PRODUCTION_READINESS_REPORT.md`
- **Product Documentation:** `recruitpro_system_v2.5.md`
- **Feature Status:** `desktop/FEATURE_STATUS.md`

---

## 🖥️ Desktop Application (Optional)

To use the Electron desktop app:

```bash
cd desktop
npm install
npm start
```

The desktop app will:
- Automatically start the backend
- Open a native window
- Provide system tray integration
- Enable auto-updates

---

## 🧪 Testing

Run all tests:
```bash
python -m pytest -v
```

Run specific test:
```bash
python -m pytest tests/test_health.py -v
```

---

## 💡 Next Steps

1. **Explore the API:** Visit http://localhost:8000/docs
2. **Create projects and candidates** via the web UI or API
3. **Add integrations:** Configure Gemini, SmartRecruiters at http://localhost:8000/settings
4. **Read the docs:** Check `GETTING_STARTED.md` for detailed guides
5. **Try the desktop app:** `cd desktop && npm install && npm start`

---

## 🆘 Troubleshooting

### Can't access the server?
```bash
# Check if it's running
curl http://localhost:8000/api/health

# Check if port is in use
lsof -i :8000
```

### Database errors?
```bash
# Reinitialize (WARNING: deletes all data)
rm data/recruitpro.db
python -m app.database
```

### Forgot credentials?
Check `QUICK_ACCESS.md` for the admin credentials.

---

**Need Help?** Check the full documentation in `GETTING_STARTED.md`

**Enjoy your RecruitPro ATS! 🚀**
