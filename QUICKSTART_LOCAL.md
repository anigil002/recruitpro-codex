# RecruitPro - Local Single-User Quick Start

This guide will get you up and running with RecruitPro on your local computer in minutes.

## Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher (for CSS compilation)
- 500MB free disk space

## Step-by-Step Setup

### 1. Install Python Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

### 2. Install Node.js Dependencies and Build CSS

```bash
npm install
npm run build:css
```

### 3. Set Up Configuration

Copy the local configuration file:

```bash
cp .env.local .env
```

**Optional**: Edit `.env` to customize settings or add your Gemini API key for AI features.

### 4. Initialize the Database

Create the SQLite database and tables:

```bash
python -m app.database
```

This creates a `data/recruitpro.db` SQLite database file.

### 5. Start the Application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Access the Application

Open your browser and go to:
- **Web UI**: http://localhost:8000/app
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 7. Create Your First User

On the login page, click "Register" and create your account. That's it!

## Features Available Locally

### Works Out of the Box (No Additional Setup)

✅ User authentication and management
✅ Project and position management
✅ Candidate tracking and CV upload
✅ Document management
✅ Interview scheduling
✅ Activity feed and reporting
✅ Settings management

### Optional Enhancements

#### Enable AI Features (Recommended)

1. Get a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Add it to your `.env` file:
   ```
   RECRUITPRO_GEMINI_API_KEY=your-api-key-here
   ```
3. Restart the application

**AI features include:**
- CV screening with compliance analysis
- Job description generation
- Market research and salary benchmarking
- Candidate scoring and outreach generation
- Chatbot assistant

#### Enable Background Job Processing (Optional)

For faster AI processing, install and run Redis:

```bash
# Install Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# Or on macOS with Homebrew
brew install redis

# Start Redis
redis-server
```

Then uncomment this line in your `.env` file:
```
RECRUITPRO_REDIS_URL=redis://localhost:6379/0
```

Start a worker process in a separate terminal:
```bash
python -m app.worker
```

#### Enable Virus Scanning (Optional)

For enhanced security when uploading files:

```bash
# Install ClamAV (Ubuntu/Debian)
sudo apt-get install clamav clamav-daemon

# Or on macOS with Homebrew
brew install clamav
```

RecruitPro will automatically detect and use ClamAV if installed.

## Desktop Application

Want a native desktop app? See [desktop/README.md](desktop/README.md) for instructions on building the Electron application.

## Troubleshooting

### Port Already in Use

If port 8000 is already in use, specify a different port:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### Database Errors

If you encounter database errors, delete the database and recreate it:
```bash
rm -rf data/
python -m app.database
```

### Module Not Found Errors

Ensure you've installed all Python dependencies:
```bash
python -m pip install -e .[dev]
```

## Next Steps

- Read [AI_INTEGRATION_GUIDE.md](AI_INTEGRATION_GUIDE.md) to learn about AI features
- See [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md) if you want to deploy for multiple users
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues

## Getting Help

For issues or questions, check the existing documentation files or create an issue on GitHub.
