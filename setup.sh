#!/bin/bash
# Setup script for NIH/NSF At-Risk Labs Tracker

echo "Setting up NIH/NSF At-Risk Labs Tracker..."

# Backend setup
echo "Setting up backend..."
cd backend

# Create virtual environment
echo "Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Backend setup complete!"

# Frontend setup
echo "Setting up frontend..."
cd ../frontend

# Install Node.js dependencies
echo "Installing Node.js dependencies..."
npm install

echo "Frontend setup complete!"

echo "Setup complete! To run the application:"
echo "1. Backend: cd backend && python main.py"
echo "2. Frontend: cd frontend && npm start"
