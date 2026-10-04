# AI-Based Smart Career Path Recommendation System

Group research project J26-IT-385. The system recommends career paths to students
based on their technical skills and personality, explains the recommendations, and
generates a learning roadmap and skill-gap analysis.

> This repository currently contains the **shared base project** only. The research
> components are placeholders — no AI/ML logic is implemented yet.

## Research Components

| # | Component | Owner | Git branch | Backend folder | Frontend folder |
|---|-----------|-------|------------|----------------|-----------------|
| 01 | Technical Skill Profile / Skill Assessment | Tharindi | `Tharindi-skill-profile` | `backend/app/component01_skill/` | `frontend/src/pages/component01/` |
| 02 | Personality Profile / Personality Analysis | Nethmi | `Nethmi-personality-profile` | `backend/app/component02_personality/` | `frontend/src/pages/component02/` |
| 03 | Explainable Career Recommendation (future: XGBoost + SHAP) | Oshada | `Oshada-career-recommendation` | `backend/app/component03_career/` | `frontend/src/pages/component03/` |
| 04 | Learning Roadmap & Skill Gap Analyzer | Dewmi | `Dewmi-learning-roadmap` | `backend/app/component04_roadmap/` | `frontend/src/pages/component04/` |

### System flow (future)

```
Student
   |
   +--> Component 01: Technical Skill Profile
   |
   +--> Component 02: Personality Profile
              |
              v
   Component 03: Career Recommendation
              |
              v
   Component 04: Learning Roadmap & Skill Gap
              |
              v
         Final Result
```

- **Component 01** provides technical skill information.
- **Component 02** provides personality information.
- **Component 03** combines Component 01 + 02 data to generate explainable career recommendations.
- **Component 04** uses the recommended career and skill information to generate learning roadmaps and skill-gap information.

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, Uvicorn, python-dotenv
- **Database:** PostgreSQL (psycopg2-binary)
- **Frontend:** React, Vite, React Router

## Project Structure

```
backend/
  app/
    main.py, database.py, config.py      # shared (group leader)
    component01_skill/                   # Tharindi
    component02_personality/             # Nethmi
    component03_career/                  # Oshada (includes ml/ for training)
    component04_roadmap/                 # Dewmi
  requirements.txt
  .env.example
frontend/
  src/
    api/client.js                        # shared API helpers
    components/Navbar.jsx, Sidebar.jsx   # shared layout
    pages/component01..04/               # one folder per component
    App.jsx, main.jsx
database/
  schema.sql, seed.sql                   # shared schema
```

## Backend Setup

```bash
cd backend
```

Create and activate a virtual environment:

**Windows**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Create the environment file:

**Windows**
```bash
copy .env.example .env
```

**macOS/Linux**
```bash
cp .env.example .env
```

Run the API:
```bash
uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000
- Health check: http://localhost:8000/health
- Swagger docs: http://localhost:8000/docs

The API starts even if PostgreSQL is not installed or not running. A database
connection is only opened when an endpoint actually uses `get_db()`. Tables are
**not** created automatically on startup.

## PostgreSQL Setup

1. Install and start PostgreSQL.
2. Create a database called `career_db`:
   ```sql
   CREATE DATABASE career_db;
   ```
3. Update `backend/.env` with your PostgreSQL username and password:
   ```
   DATABASE_URL=postgresql://<username>:<password>@localhost:5432/career_db
   ```
4. Run `database/schema.sql` against `career_db`, for example:
   ```bash
   psql -U postgres -d career_db -f database/schema.sql
   ```

Never commit your real `.env` file — it is ignored by Git.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

| Route | Page |
|-------|------|
| `/` | Home |
| `/component01` | Technical Skill Profile |
| `/component02` | Personality Profile |
| `/component03` | Explainable Career Recommendation |
| `/component04` | Learning Roadmap & Skill Gap |

## Team Git Workflow

- The **group leader maintains `main`**.
- Members **do not develop directly on `main`**.
- Each member works on their own existing branch:

| Member | Branch |
|--------|--------|
| Tharindi | `Tharindi-skill-profile` |
| Nethmi | `Nethmi-personality-profile` |
| Oshada | `Oshada-career-recommendation` |
| Dewmi | `Dewmi-learning-roadmap` |

### Updating your branch after `main` changes

After the group leader updates `main`, update your own branch:

```bash
git checkout <member-branch>
git fetch origin
git merge origin/main
```

**Do NOT run `git merge main`** unless your local `main` branch has already been
updated. Your local `main` may be out of date, so prefer:

```bash
git fetch origin
git merge origin/main
```

This explicitly merges the latest **remote** `main` into your current member branch.

### Committing your work

Commit and push **only your own branch**. Example:

```bash
git add .
git commit -m "Implement Component 01 feature"
git push origin Tharindi-skill-profile
```

Members must **NOT** push directly to `main`.

## Merge Conflict Prevention

Members should primarily modify **only their assigned component folders**:

| Owner | Allowed development folders |
|-------|-----------------------------|
| Tharindi | `backend/app/component01_skill/`, `frontend/src/pages/component01/` |
| Nethmi | `backend/app/component02_personality/`, `frontend/src/pages/component02/` |
| Oshada | `backend/app/component03_career/`, `frontend/src/pages/component03/` |
| Dewmi | `backend/app/component04_roadmap/`, `frontend/src/pages/component04/` |

If you need any of the following, **tell the group leader**:

- a new global route
- a shared database change
- a shared dependency (e.g. adding a package to `requirements.txt` or `package.json`)
- a Navbar change
- a Sidebar change
- an `App.jsx` change
- a database schema change
- a shared API client change

The group leader will make the shared change on `main`. Members then run
`git fetch origin` and `git merge origin/main` to bring it into their branches.

### Leader-owned shared files

These files are shared and should **only be changed by the group leader** unless
permission is given:

```
backend/app/main.py
backend/app/database.py
backend/app/config.py
backend/requirements.txt

frontend/src/App.jsx
frontend/src/api/client.js
frontend/src/components/Navbar.jsx
frontend/src/components/Sidebar.jsx

database/schema.sql
database/seed.sql

README.md
.gitignore
```
