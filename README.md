# 🌟 Wiwi Events — Modern Event Management System & REST API

A high-performance, full-stack **Event Management Platform** built with **Django**, **Django REST Framework**, and a modern **Dark Glassmorphism Design System**.

[![Django](https://img.shields.io/badge/Django-6.0+-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![REST API](https://img.shields.io/badge/Django_REST_Framework-3.15+-red?logo=django&logoColor=white)](https://www.django-rest-framework.org/)

---

## ✨ Highlights & Features

### 🎨 Dark Glassmorphism Design System
- Modern dark mode aesthetic using curated color tokens (`#060913`, `#0f172a`), radial ambient glows, and `backdrop-filter: blur()`.
- Responsive layout using Google Fonts (**Outfit** for headings, **Inter** for body text) and Font Awesome 6 icons.

### 📅 Event Host & Moderation Workflow
- **Host Submission:** Authenticated users can host events with custom title, description, category, venue format (In-Person / Virtual / Hybrid), speaker info, capacity, and banner image uploads.
- **Admin Moderation Panel:** Customized Django Admin (`/admin/`) dashboard featuring dedicated pending review and approved active event tables with one-click approve/reject actions.
- **Capacity Protection:** Row-level database locking (`select_for_update`) and atomic transactions prevent overbooking during concurrent user registrations.

### 🎟️ QR-Code Digital Ticket Passes
- Automatic generation of unique alphanumeric ticket codes (`TIC-XXXXXXXX`).
- Server-side QR code generation (`qrcode[pil]`) rendered dynamically as base64 PNG data.
- **Printable Ticket Stub:** Responsive print stylesheet (`@media print`) rendering landscape physical ticket stubs with left info panel and right QR stub.

### ⚡ Django REST Framework API (v1)
- Complete RESTful endpoints under `/api/v1/`:
  - `GET /api/v1/events/` — List & filter events by category, venue format, upcoming date (`?upcoming=true`), and text search (`?search=`).
  - `POST /api/v1/events/` — Submit new events via API.
  - `POST /api/v1/registrations/` — Register for events with thread-safe capacity checks.
  - `DELETE /api/v1/registrations/{id}/` — Cancel registrations.
  - `POST /api/v1/auth/token/` — Obtain Token Authentication credentials.
- DRF Browsable API (`/api-auth/`) for interactive browser testing.
- Complete API reference documentation in [`API.md`](API.md).

---

## 🛠️ Tech Stack

- **Backend Framework:** Python 3.13 / Django 6.0+
- **REST API:** Django REST Framework (DRF)
- **Database:** SQLite (Development) / PostgreSQL compatible
- **Image & QR Processing:** Pillow, qrcode[pil]
- **Frontend UI:** Vanilla CSS3 (Glassmorphism Tokens), HTML5, JavaScript
- **Security:** `python-dotenv` environment variables, CSRF protection, Django RBAC

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+ installed
- `git` command-line tool

### 1. Clone the Repository
```bash
git clone https://github.com/Nehaa2509/Event_Management_System.git
cd Event_Management_System
```

### 2. Set Up Virtual Environment & Install Dependencies
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Database Setup & Migrations
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run Local Development Server
```bash
python manage.py runserver
```

Visit the application in your browser:
- **Main Platform:** `http://127.0.0.1:8000/`
- **Admin Moderation Panel:** `http://127.0.0.1:8000/admin/`
- **REST API Explorer:** `http://127.0.0.1:8000/api/v1/`

---

## 🧪 Running Unit Tests

Run the full Django test suite (including concurrency, RBAC, and REST API tests):
```bash
python manage.py test
```

---

## 📚 API Documentation

Detailed REST API documentation with endpoint tables, request/response JSON schemas, and `curl` examples can be found in [`API.md`](API.md).
