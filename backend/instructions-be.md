# Backend setup — Windows PowerShell

### 1. Open the backend folder

Run from the project root.

```powershell
cd backend
```

### 2. Create a Python environment

Install Python 3.11 first.

```powershell
py -3.11 -m venv .venv
```

### 3. Activate the environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If activation is blocked, run this and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 4. Install required packages

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 5. Create the settings file

Skip the copy command if `.env` already exists.

```powershell
Copy-Item .env.example .env
```

Generate a secret key:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Open `.env` and paste the generated key after `AUTH_SECRET_KEY=`. Keep
`AUTH_COOKIE_SECURE=false` for local development.

```powershell
notepad .env
```

SQLite is created automatically. No database installation is needed.

### 6. Run the backend

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

Health check: http://localhost:8000/health

Press `Ctrl+C` to stop.

### Run again next time

From the project root:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000
```
