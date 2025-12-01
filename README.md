# YouTube Gist Generator 🎥✨

A modern, AI-powered web application that generates concise summaries of YouTube videos instantly. Built with a sleek Glassmorphism UI and powered by Google's Gemini Pro model.

## 🚀 Features

- **Instant Summaries**: Get key points from long videos in seconds.
- **Modern UI**: Beautiful, responsive interface with glassmorphism effects and neon gradients.
- **AI-Powered**: Utilizes Google's advanced Gemini 2.0 Flash model for accurate and coherent summaries.
- **Privacy Focused**: Runs locally and processes transcripts securely.

## 🛠️ Tech Stack

### Frontend
- **HTML5 & CSS3**: Custom responsive design with CSS variables and flexbox.
- **JavaScript (ES6+)**: Modular architecture using MVC pattern.
- **Parcel**: Blazing fast web application bundler.

### Backend
- **Python & Flask**: Lightweight REST API.
- **Google Gemini API**: For generative AI summarization.
- **YouTube Transcript API**: To extract video captions.

## ⚙️ Installation & Setup

Follow these steps to run the project locally.

### Prerequisites
- **Node.js** (v14+ recommended)
- **Python** (v3.8+ recommended)
- A **Google Gemini API Key** (Get one [here](https://aistudio.google.com/app/apikey))

### 1. Clone the Repository
```bash
git clone https://github.com/justishika/Video-Gist-Generator.git
cd Video-Gist-Generator
```

### 2. Backend Setup (Flask API)
Navigate to the API directory and set up the Python environment.

```bash
cd Flask-API

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Configure API Key:**
Open `Flask-API/config.py` and replace the placeholder with your actual Gemini API key:
```python
GEMINI_API_KEY = 'YOUR_ACTUAL_API_KEY_HERE'
```
download the below:
```python
   cd Flask-API
   pip install spacy
   python -m spacy download en_core_web_sm
```

*Note: Never commit your actual API key to GitHub!*

**Run the Server:**
```bash
python app.py
```
The backend will start at `http://127.0.0.1:5000`.

### 3. Frontend Setup
Open a new terminal window, return to the project root, and install frontend dependencies.

```bash
# Return to root directory if you are in Flask-API
cd .. 

# Install dependencies
npm install

# Start the development server
npm start
```
The application will open in your browser at `http://localhost:1234`.

## 📖 Usage
1. Copy a YouTube video URL (e.g., educational videos, tech talks, podcasts).
2. Paste it into the search bar on the web app.
3. Click **"Summarize in 10 Points"**.
4. Wait a few seconds for the AI to generate your summary!

## 📄 License
This project is licensed under the ISC License.
