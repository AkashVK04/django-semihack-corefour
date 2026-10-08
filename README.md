# EduEvent V2 — Academic Event & Digital Certificate Management Platform

> **EduEvent V2** is a production-grade, full-stack Django web platform engineered for complete academic event lifecycle management:
> **Student Registration ➔ Live QR Check-in ➔ Multi-Metric Feedback ➔ Gatekeeper Certificate Issuance ➔ Public Cryptographic Verification & Revocation**.

---

## 🚀 Key Features & Capabilities

### 1. **Public Cryptographic QR Certificate Verification (`/verify/<hash>/`)**
- Every generated certificate embeds a unique certificate ID (e.g. `EDU-2026-000124`) and SHA-256 hash.
- Scanning the certificate QR code leads to an authoritative verification web card displaying `VALID` (green shield badge with metadata and PDF download) or `REVOKED` (red alert banner with official revocation timestamp and reason).

### 2. **Certificate Revocation Engine**
- Authorized Event Organizers and Admins can revoke or reinstate certificates with official audit reasons via `/revoke/<id>/` and `/restore/<id>/`.

### 3. **Role-Based Access Control (RBAC)**
- Four defined access roles enforced via custom decorators (`@organizer_required`, `@staff_required`, `@student_required`):
  - **STUDENT**: Event registration, student portal access, certificate download.
  - **ATTENDANCE STAFF**: Live camera QR scanner check-in interface (`/scan/`).
  - **EVENT ORGANIZER**: Event creation/editing, participant management, CSV exports, certificate issuance & revocation.
  - **ADMINISTRATOR**: System-wide analytics, user management, and full security controls.

### 4. **Live Camera QR Attendance Scanner (`/scan/`)**
- Staff can scan participant registration QR codes via browser camera (`html5-qrcode`) or manually input IDs for instant attendance logging with timestamps.
- Manual AJAX attendance toggle preserved as fallback in organizer dashboard (`/dashboard/`).

### 5. **Strict Gatekeeper Eligibility Engine**
- Certificate generation requires **both** confirmed event attendance **AND** completed multi-metric feedback.
- Unauthorized or incomplete access attempts trigger a custom `403 Access Denied` explanation page (`certificate_denied.html`).

### 6. **ReportLab PDF Certificate Engine**
- Generates landscape A4 vector certificates formatted with gold/navy framing, institution seals, verification hashes, status badges, and signature blocks.

---

## 🏗️ System Architecture Flow

```
[ Student Registration ]
           │
           ▼
[ Participant Record & QR Created ] 
           │
           ▼
[ Staff Scans QR at Gate ] ── (AJAX POST) ──► [ Attendance Marked & Timestamped ]
                                                             │
                                                             ▼
                                             [ Student Submits 4-Metric Feedback ]
                                                             │
                                                             ▼
                                             [ Gatekeeper Eligibility Matrix Check ]
                                             (Attendance=True AND Feedback=True)
                                                             │
                                                             ▼
                                             [ Certificate Issued: EDU-2026-000124 ]
                                                             │
                                                             ▼
                                             [ Public Verification: /verify/<hash>/ ]
                                                ├── VALID   ==> Green Badge + PDF Download
                                                └── REVOKED ==> Red Badge + Official Reason
```

---

## 🛠️ Tech Stack & Dependencies

| Layer | Component |
| :--- | :--- |
| **Backend Framework** | Django 6.0+ / 4.2+ (Python) |
| **Database** | SQLite (Dev) / PostgreSQL (Prod ready) |
| **PDF Generation** | `reportlab` 4.5.0 (Vector canvas graphics) |
| **QR Engine** | `qrcode[pil]`, `Pillow`, `html5-qrcode` JS |
| **Frontend** | HTML5, Bootstrap 5.3, Inter & Space Grotesk Google Fonts, FontAwesome 6 |
| **Async / Interactivity**| Native JS `fetch()` API for AJAX attendance updates & QR camera scanner |

---

## 📦 Local Setup Instructions

```bash
# 1. Clone repository
git clone https://github.com/AkashVK04/django-semihack-corefour.git
cd django-semihack-corefour

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Apply database migrations
python manage.py makemigrations
python manage.py migrate

# 5. Create administrator account
python manage.py createsuperuser

# 6. Run development server
python manage.py runserver
```

Open **`http://127.0.0.1:8000`** in your browser.

---

## 🧪 Automated Testing

Run the automated test suite covering duplicate registration prevention, gatekeeper eligibility matrix, verification, and revocation:

```bash
python manage.py test events
```

Expected Output:
```
Ran 4 tests in 6.906s
OK
```

---

## 🛡️ Environment Variables (`.env.example`)

```env
SECRET_KEY=your-production-secret-key-here
DEBUG=False
ALLOWED_HOSTS=*.onrender.com,localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```
