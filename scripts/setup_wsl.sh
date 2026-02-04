#!/bin/bash

# setup_wsl.sh - Environment Setup for cres_ytdlp in WSL

echo "Initializing WSL Environment Setup..."

# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install FFmpeg (Critical for Whisper and Thumbnails)
sudo apt install -y ffmpeg

# 3. Install Python and Pip
sudo apt install -y python3 python3-pip python3-venv

# 4. Install Node.js and NPM
# Using NodeSource for a modern version
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
fi

# 5. Set up Python Virtual Environment
cd "$(dirname "$0")"
python3 -m venv venv
source venv/bin/activate

# 6. Install Python Dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 7. Install Web Dependencies
if [ -d "web" ]; then
    cd web
    npm install
    cd ..
fi

echo "------------------------------------------------"
echo "Setup Complete!"
echo "To run the project:"
echo "1. Activate venv: source venv/bin/activate"
echo "2. Run Search: python3 main.py"
echo "3. Run Web: cd web && npm run dev"
echo "------------------------------------------------"
