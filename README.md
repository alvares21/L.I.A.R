# L.I.A.R - Language-based Instant Apology Responder - Capstone Project

## Quick Start Guide

### 1. Installation

Create virtual environment
python -m venv venv

Activate environment
Windows:
venv\Scripts\activate

macOS/Linux:
source venv/bin/activate

Install dependencies
pip install -r requirements.txt


### 2. Configuration

Copy environment template
copy .env.example .env # Windows
cp .env.example .env # macOS/Linux


### 3. Run Application

python app.py


Visit: http://localhost:5000

## API Keys Required

### Flask SECRET_KEY (Required)
Generate using Python:

import secrets
print(secrets.token_hex(32))


### OpenAI API Key (Required for AI Features)
1. Go to https://platform.openai.com/api-keys
2. Create account and generate API key
3. Add to .env file: `OPENAI_API_KEY=sk-your-key-here`

## Features Implemented

- ✅ AI-Generated Excuses (GPT-3.5)
- ✅ Scenario-Based Customization
- ✅ Proof Document Generator (Email, Receipt, Medical Note)
- ✅ Voice Integration (Text-to-Speech)
- ✅ Excuse History & Favorites
- ✅ Multi-Language Support (English, Spanish, French, German)
- ✅ Smart Believability Scoring
- ✅ Professional UI/UX
- ✅ Database Management

## Project Structure

excuse-generator/
├── app.py # Main Flask application
├── requirements.txt # Python dependencies
├── .env.example # Environment configuration
├── templates/
│ └── index.html # UI template
├── static/
│ ├── audio/ # Generated voice files
│ └── proofs/ # Generated documents
└── README.md # Setup instructions


## Complete Setup Process

### Step 1: Create Project Directory

mkdir excuse-generator
cd excuse-generator
mkdir templates static static/audio static/proofs


### Step 2: Create All Project Files
Create the following files with the provided content:
- `app.py` (Main Flask application)
- `requirements.txt` (Dependencies)
- `.env.example` (Configuration template)
- `templates/index.html` (User interface)
- `README.md` (This file)

### Step 3: Set Up Python Environment

Create virtual environment
python -m venv venv

Activate virtual environment
On Windows:
venv\Scripts\activate

On macOS/Linux:
source venv/bin/activate

Install required packages
pip install -r requirements.txt


### Step 4: Install PyAudio (Windows Users)
PyAudio is required for voice features. Choose one method:

**Method 1: Using Pipwin (Recommended)**

pip install pipwin
pipwin install pyaudio


**Method 2: Pre-compiled Wheel**

pip install https://github.com/intxcc/pyaudio_portaudio/releases/download/v0.2.11/PyAudio-0.2.11-cp38-cp38-win_amd64.whl


**Method 3: Manual Download**
1. Go to: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
2. Download the appropriate .whl file for your Python version
3. Install: `pip install path/to/downloaded/file.whl`

### Step 5: Configure Environment Variables

Copy the template
copy .env.example .env # Windows
cp .env.example .env # macOS/Linux


Edit your `.env` file with:

Flask Configuration
SECRET_KEY=your-generated-secret-key-here
DEBUG=True
FLASK_ENV=development

Database
DATABASE_URL=sqlite:///excuse_generator.db

OpenAI API (Required for AI features)
OPENAI_API_KEY=sk-your-openai-api-key-here


### Step 6: Generate Flask SECRET_KEY
Run this in Python terminal:

import secrets
print(secrets.token_hex(32))

Copy the output and use it as your SECRET_KEY in the .env file.

### Step 7: Get OpenAI API Key
1. Visit https://platform.openai.com/api-keys
2. Sign up/login to OpenAI
3. Create a new API key
4. Copy the key (starts with `sk-`)
5. Add it to your .env file

### Step 8: Run the Application

python app.py


You should see:

📊 Database tables created successfully!
🎉 Intelligent Excuse Generator is starting...
📱 Access the app at: http://localhost:5000
🎤 Voice features enabled!
✅ Text-to-Speech engine initialized successfully!


### Step 9: Test Your Application
1. Open your browser
2. Go to http://localhost:5000
3. Fill out the excuse generation form
4. Click "Generate Excuse"
5. Test additional features:
   - Generate Proof Documents
   - Convert to Voice (NEW!)
   - Add to Favorites
   - View Excuse History
