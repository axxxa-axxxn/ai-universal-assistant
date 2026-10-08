# AI Universal Assistant

A full-stack personal AI assistant with:

- Account registration and login
- JWT authentication
- Personal chat history
- File upload (PDF, TXT, DOCX, CSV, MD)
- Image upload
- Personal document retrieval (RAG-style local search)
- AI answers through Google Gemini
- Optional web search
- React + Vite frontend
- Flask backend
- SQLite by default, easy to switch to PostgreSQL later

## 1. Requirements

Install:

- Python 3.11+
- Node.js 18+
- npm

A Gemini API key is required for AI answers. Add it to `backend/.env`.

## 2. Backend

PowerShell:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `backend/.env` and set:

```env
SECRET_KEY=change-this-secret
JWT_SECRET_KEY=change-this-jwt-secret
GEMINI_API_KEY=your_gemini_api_key
```

Then:

```powershell
python run.py
```

Backend runs at:

http://127.0.0.1:5000

## 3. Frontend

Open a second PowerShell window:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL shown by Vite, normally:

http://localhost:5173

## 4. How to use

1. Register an account.
2. Log in.
3. Start a conversation.
4. Ask questions.
5. Upload a PDF/TXT/DOCX/CSV/MD file.
6. Ask questions about your uploaded files.
7. Upload an image and ask the AI to explain it.
8. Enable "Web Search" when you want current web information.

## Important

The default database is SQLite so the project works immediately on one computer.

Uploaded files are stored in `backend/uploads`.

For production deployment, move uploads to object storage and SQLite to PostgreSQL, and use a hosted vector database/object-storage architecture. This starter deliberately avoids local ChromaDB persistence so it is easier to deploy later.
