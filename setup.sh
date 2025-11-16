#!/bin/bash
set -e

echo "🚀 RecruitPro Setup Script"
echo "=========================="

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

echo ""
echo "📦 Installing Node.js dependencies..."
npm install

echo ""
echo "🎨 Building Tailwind CSS..."
npm run build:css

echo ""
echo "🐍 Installing Python dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -e .[dev] 2>&1 | grep -v "WARNING" || true

echo ""
echo "📁 Creating necessary directories..."
mkdir -p data storage

echo ""
echo "⚙️  Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env file from .env.example"
    echo "⚠️  Please update .env with your configuration"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🗄️  Initializing database..."
python3 -m app.database

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "  uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "Or for development with CSS auto-rebuild:"
echo "  npm run watch:css &"
echo "  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
