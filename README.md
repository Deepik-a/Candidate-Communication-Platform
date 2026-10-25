# Candidate Communication Platform

A full-stack recruiter platform for communicating with candidates and tracking the complete communication journey.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, TypeScript, Material UI v7 |
| Backend | Python, Django 4.2, Django REST Framework |
| Database | PostgreSQL |
| Architecture | Clean Architecture + SOLID Principles |

---

## Project Structure

```
Candidate Communication Platform/
├── frontend/           # Next.js + TypeScript + MUI
│   ├── src/
│   │   ├── app/        # Next.js App Router pages
│   │   ├── components/ # React components
│   │   ├── context/    # React context providers
│   │   ├── lib/        # API client
│   │   └── types/      # TypeScript type definitions
│   └── .env.local      # Frontend environment variables
│
└── backend/            # Django REST API
    ├── core/           # Django project settings & URLs
    ├── apps/
    │   ├── candidates/         # Candidate management
    │   │   ├── domain/         # Entities & Repository interface
    │   │   ├── application/    # Service (use cases)
    │   │   ├── infrastructure/ # ORM models & repository impl
    │   │   └── api/            # DRF serializers & views
    │   └── communications/     # Messaging app
    ├── manage.py
    └── requirements.txt
```

---

## Backend Setup

> **Prerequisite**: Python 3.10+ and PostgreSQL must be installed.

### 1. Create and activate a virtual environment
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
# Copy and edit the example env file
copy .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 4. Create the PostgreSQL database
```sql
CREATE DATABASE candidate_comm_db;
```

### 5. Run migrations
```bash
python manage.py makemigrations candidates communications
python manage.py migrate
```

### 6. Create a superuser (optional, for admin)
```bash
python manage.py createsuperuser
```

### 7. Start the backend
```bash
python manage.py runserver
```

The API will be available at: `http://localhost:8000`
API docs (Swagger): `http://localhost:8000/api/docs/`
Admin panel: `http://localhost:8000/admin/`

---

## Frontend Setup

### 1. Install dependencies
```bash
cd frontend
npm install
```

### 2. Configure environment
```bash
# Edit .env.local if your backend runs on a different port
# NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 3. Start the frontend dev server
```bash
npm run dev
```

The app will be available at: `http://localhost:3000`

---

## API Endpoints

### Candidates
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/candidates/` | List candidates (paginated, searchable) |
| POST | `/api/v1/candidates/` | Create a new candidate |
| GET | `/api/v1/candidates/{id}/` | Get a candidate |
| PATCH | `/api/v1/candidates/{id}/` | Update a candidate |
| DELETE | `/api/v1/candidates/{id}/` | Delete a candidate |
| POST | `/api/v1/candidates/bulk-delete/` | Bulk delete candidates |

### Communications
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/communications/send/` | Send a message |
| GET | `/api/v1/communications/candidate/{id}/` | Get message history |

---

## Architecture Overview

The backend follows **Clean Architecture** with 4 distinct layers:

```
┌─────────────────────────────────────┐
│           API Layer (DRF)           │  ← Serializers, Views, URLs
├─────────────────────────────────────┤
│       Application Layer             │  ← Services (Use Cases)
├─────────────────────────────────────┤
│         Domain Layer                │  ← Entities, Repository Interface
├─────────────────────────────────────┤
│      Infrastructure Layer           │  ← Django ORM, Repository Impl
└─────────────────────────────────────┘
```

**SOLID Principles Applied:**
- **S** (SRP): Each class has a single responsibility
- **O** (OCP): Services extensible via repository interfaces
- **L** (LSP): Repository implementations are interchangeable
- **I** (ISP): Small, focused interfaces
- **D** (DIP): Services depend on abstractions, not concrete implementations
