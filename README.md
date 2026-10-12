# AI Universal Assistant

A full-stack AI-powered personal assistant that allows users to manage conversations, upload documents, retrieve relevant information, and receive AI-generated answers using Google Gemini.

## Features

* User registration and login
* JWT-based authentication
* Personal chat history
* File uploads: PDF, TXT, DOCX, CSV, and Markdown
* Image uploads for AI-assisted analysis
* Retrieval-Augmented Generation (RAG)-style document search
* AI-generated responses using Google Gemini
* Optional web search
* React and Vite frontend
* Flask and Python backend
* PostgreSQL database using Neon
* SQLAlchemy database integration
* Environment-based configuration for local development and deployment
* Vercel deployment configuration

## Technology Stack

| Component                   | Technology              |
| --------------------------- | ----------------------- |
| Frontend                    | React, Vite, JavaScript |
| Backend                     | Python, Flask           |
| Database                    | Neon PostgreSQL         |
| ORM                         | Flask-SQLAlchemy        |
| Authentication              | Flask-JWT-Extended      |
| AI model provider           | Google Gemini           |
| Database driver             | psycopg2                |
| Frontend development server | Vite                    |
| Backend deployment          | Vercel                  |
| Version control             | Git and GitHub          |

## Requirements

Install the following tools:

* Python 3.11 or later
* Node.js and npm
* Git
* A Google Gemini API key
* A Neon PostgreSQL database for the deployed configuration

## Project Structure

```text
ai-universal-assistant/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── routes.py
│   ├── instance/
│   ├── uploads/
│   ├── .env.example
│   ├── requirements.txt
│   ├── run.py
│   └── vercel.json
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
├── .gitignore
└── README.md
```

*Note: This structure shows the main expected files and directories. Your actual project may contain additional files.*

## 1. Backend Setup

Open PowerShell in the project root.

```powershell
cd backend

python -m venv venv

.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Create your local environment file if it does not already exist:

```powershell
Copy-Item .env.example .env
```

If `backend/.env` already exists, do not overwrite it. Open the existing file instead.

### Backend Environment Variables

Configure the following variables in `backend/.env`:

```dotenv
SECRET_KEY=your_generated_secret_key
JWT_SECRET_KEY=your_generated_jwt_secret
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=your_neon_postgresql_connection_string
FRONTEND_URL=http://localhost:5173
AI_MODEL=gemini-3.8-flash
MAX_CONTENT_LENGTH=52428800
```

Replace the example values with your actual configuration. Generate unique secret keys for `SECRET_KEY` and `JWT_SECRET_KEY`.

**Security rules:**

* Never commit `.env` to GitHub.
* Never publish API keys, database passwords, or secret keys.
* Configure production environment variables in the Vercel dashboard.
* Use your deployed frontend's origin for `FRONTEND_URL` in the production backend.
* Keep `http://localhost:5173` for local frontend development.

### Run the Backend

From the `backend` directory:

```powershell
python run.py
```

The local backend should be available at:

`http://127.0.0.1:5000`

## 2. Frontend Setup

Open a second PowerShell terminal from the project root:

```powershell
cd frontend

npm install

npm run dev
```

Open the local URL displayed by Vite, usually:

`http://localhost:5173`

Ensure the frontend API configuration points to the local backend during development and the deployed backend URL in production.

## 3. Database Configuration

The project uses SQLAlchemy to connect the Flask backend to its database.

### Local Development

The application can use SQLite if configured as a local fallback.

### Production Deployment

The deployed configuration uses Neon PostgreSQL.

Set `DATABASE_URL` in the backend environment to your Neon PostgreSQL connection string. Configure the same variable in Vercel's environment settings for the appropriate deployment environments.

The backend normalizes PostgreSQL connection URLs to use the installed `psycopg2` driver.

Database tables are initialized by the application using SQLAlchemy's `db.create_all()`.

**Note:** `db.create_all()` creates missing tables; it does not migrate existing database records from SQLite to PostgreSQL. Back up and migrate any data you want to preserve separately.

## 4. AI and Document Retrieval

The assistant uses Google Gemini to generate responses.

The document-retrieval workflow is intended to:

1. Accept supported document uploads.
2. Extract text from supported file formats.
3. Find relevant document content for a user's question.
4. Supply retrieved context to the AI response workflow.
5. Return a response based on the available context and configured AI services.

Actual support depends on the routes and services implemented in the current version.

The Gemini API key must be configured as an environment variable. Never place it directly in frontend code or commit it to the repository.

## 5. How to Use the Application

1. Open the frontend.
2. Register a user account.
3. Log in.
4. Start a conversation.
5. Ask the assistant a question.
6. Upload a supported document.
7. Ask questions related to the uploaded content.
8. Upload an image if image analysis is supported by the configured AI workflow.
9. Use the optional web-search functionality if it is enabled in the current implementation.

## 6. Vercel Deployment

The backend includes a `vercel.json` configuration for deploying the Flask application.

Before deployment:

1. Push the latest project changes to GitHub.
2. Import or connect the repository in Vercel.
3. Set the backend project's **Root Directory** to `backend` if deploying from this configuration.
4. Configure the required environment variables in Vercel.
5. Set `DATABASE_URL` to the Neon PostgreSQL connection string.
6. Set `FRONTEND_URL` to the deployed frontend's origin.
7. Ensure the production secrets differ from development placeholders.
8. Deploy and review the build and runtime logs.
9. Test the deployed API health endpoint and authentication routes.

The frontend and backend may be deployed as separate Vercel projects. If so, ensure the frontend uses the correct deployed backend API URL and the backend's CORS configuration allows the frontend origin.

**Deployment note:** A successful local startup does not guarantee that deployment will succeed. Verify the Vercel build, runtime logs, database connectivity, authentication, file handling, and AI endpoints after deployment.

## 7. Security and Production Considerations

* Keep `.env` files out of version control.
* Use strong, unique production secrets.
* Validate uploaded files and enforce upload-size limits.
* Avoid exposing internal exception details to users.
* Restrict CORS to trusted frontend origins.
* Back up important database records.
* Use persistent object storage for uploaded files when required.
* Confirm that any document-retrieval storage works in the deployed environment.
* Use database migrations when modifying an established production schema.

## 8. Current Configuration Notes

* **Database:** Neon PostgreSQL connection has been tested locally.
* **Backend:** Flask application startup and SQLAlchemy table initialization have succeeded locally.
* **Frontend:** React and Vite development setup.
* **AI provider:** Google Gemini.
* **Deployment:** Vercel configuration prepared; production behavior must be verified after deployment.

## License

Add your preferred open-source license before distributing this project publicly.
