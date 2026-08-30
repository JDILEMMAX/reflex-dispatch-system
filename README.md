# Reflex: On-Demand Retail Delivery & Chain of Custody Dispatch Engine

An auditable, real-time dispatch and delivery verification system built for Kenyan urban retail corridors during the 1MILL Devs Readiness Sprint under Power Learn Project Africa.

---

## 1. Executive Summary & Kenyan Retail Context

In dense East African commercial hubs such as Nairobi CBD (Luthuli Avenue electronics shops, River Road cosmetics distributors and neighbourhood pharmacies), on-demand last-mile delivery is the lifeblood of retail commerce. However, over 85% of small retailers coordinate deliveries through ad-hoc WhatsApp groups, voice notes and phone calls.

### The Three Operational Failures in Urban Last-Mile Logistics:
1. **Accountability Void:** Retailers hand parcels to informal boda boda riders with no digital record of who took possession. When packages go missing, blame shifts between staff and couriers.
2. **Status Blindness:** Customers constantly call shopkeepers asking *"Uko wapi?"*, forcing staff into manual, distracting phone tag while riders navigate city traffic.
3. **Proof of Delivery (POD) Breakdown:** Deliveries are completed without verifiable customer confirmation, leading to payment disputes, reconciliation delays and fraudulent non-receipt claims.

### The Reflex Solution:
Reflex replaces informal WhatsApp dispatching with a deterministic, auditable digital chain of custody. It gives shopkeepers instant order entry, gives dispatchers a single-pane command center, gives riders a lightweight mobile terminal with dual-factor Proof of Delivery (QR scan and 4-digit PIN verification) and gives customers an instant, zero-login milestone tracking link.

---

## 2. System Architecture & Personas

Reflex connects four distinct user touchpoints into a unified, secure backend gateway:

```text
 ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐  ┌───────────────────┐
 │   Retailer Portal    │  │   Dispatch Center    │  │    Rider Web App     │  │ Customer Tracker  │
 │  (Order Entry & PIN) │  │ (Command & Match Hub)│  │ (Mobile POD Terminal)│  │ (Public Stepper)  │
 └──────────┬───────────┘  └──────────┬───────────┘  └──────────┬───────────┘  └─────────┬─────────┘
            │                         │                         │                        │
            │ (Bearer JWT / HTTPS)    │ (Bearer JWT / HTTPS)    │ (Bearer JWT / HTTPS)   │ (Public)
            └─────────────────────────┼─────────────────────────┴────────────────────────┘
                                      │
                        ┌─────────────▼─────────────┐
                        │      FastAPI Gateway      │
                        │ (RBAC Guards / Static UI) │
                        └─────────────┬─────────────┘
                                      │
            ┌─────────────────────────┴─────────────────────────┐
            │                                                   │
 ┌──────────▼──────────────────────────┐             ┌──────────▼──────────────────────────┐
 │       SQLite Database Engine        │             │        Async Event Dispatcher       │
 │  • WAL (Write-Ahead Logging) Mode   │             │  • In-Memory `asyncio.Queue` Worker │
 │  • Full Chain of Custody Audit Log  │             │  • Non-Blocking Webhook Broadcasts  │
 └─────────────────────────────────────┘             └─────────────────────────────────────┘
```

### The Four User Personas:
* **Retailer Staff (`ROLE_RETAILER`):** Logs outgoing customer orders (recipient name, phone, address, item details and value), automatically generating a unique tracking token, parcel QR code and a 4-digit customer delivery PIN.
* **Dispatcher (`ROLE_DISPATCHER`):** Monitors open order queues, tracks rider availability rosters and assigns parcels to active riders with one click.
* **Rider (`ROLE_RIDER`):** Interacts with a high-contrast, mobile-first web app to accept runs, update delivery milestones (`PICKED_UP` ➔ `ARRIVED`) and unlock the final `DELIVERED` status by scanning the customer QR code or submitting the customer's 4-digit PIN.
* **Customer (Public Stepper):** Receives a lightweight tracking link (`/track/{order_id}`) displaying a live visual milestone stepper from order creation to doorstep handover without needing an account or app installation.

---

## 3. Technology Stack & Technical Rationale

| Layer | Technology | Architectural Rationale |
| :--- | :--- | :--- |
| **Backend Core** | Python 3.10+ & FastAPI | High-throughput asynchronous REST API with automatic OpenAPI documentation and native Pydantic validation. |
| **Security & Auth** | JWT (JSON Web Tokens) & Passlib | Stateless, role-based access control (`ROLE_RETAILER`, `ROLE_DISPATCHER`, `ROLE_RIDER`) enforcing strict endpoint security. |
| **Data Persistence** | SQLite 3 with WAL Mode | Zero-configuration relational database configured with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) for high concurrency reads and writes. |
| **Async Processing** | Python `asyncio.Queue` | Decoupled in-memory producer/consumer pipeline dispatching background webhook notifications without adding blocking latency to user requests. |
| **Frontend UI** | HTML5, Modern CSS3 & Vanilla JS | Zero-build frontend architecture featuring responsive glassmorphism dashboards, mobile-optimized rider terminals and instant live polling. |
| **Testing & Quality** | Pytest, HTTPX & Playwright | Full test automation covering unit route security, concurrency race conditions and end-to-end headless browser user flows. |

---

## 4. Repository Directory Structure

```text
reflex-dispatch-system/
│
├── frontend/                  # Responsive Multi-Persona Web Interface
│   ├── index.html             # Central login & role-aware dashboard container
│   ├── styles.css             # Glassmorphic dark UI, mobile layouts & milestone animations
│   ├── app.js                 # ES6 module entry point: persona routing & render logic
│   ├── tracker.html           # Standalone public customer milestone tracker
│   └── utils/                 # ES6 utility module library
│       ├── api.js             # All backend fetch wrappers (orders, dispatch, rider, auth)
│       ├── auth.js            # Auth state, session persistence & Bearer header builder
│       ├── polling.js         # Interval-based live polling engine (start/stop)
│       └── ui.js              # Toast notifications, HTML escaping & date formatting
│
├── backend/                   # FastAPI Application Core
│   ├── main.py                # App entrypoint, CORS configuration & static file mounting
│   ├── database.py            # SQLite connection factory, WAL initialization & query helpers
│   ├── models.py              # Pydantic schemas for requests, responses & state transitions
│   ├── auth.py                # OAuth2 password bearer, password hashing & JWT token handling
│   ├── state_machine.py       # Deterministic delivery lifecycle & milestone validator
│   └── queue_manager.py       # Asynchronous background event worker and webhook publisher
│
├── data/                      # Data Layer & Database Migrations
│   ├── schema.sql             # Relational DDL for users, riders, orders & status audit logs
│   ├── seed.py                # Database seeder populating test retailers, riders & orders
│   └── reflex.db              # Local SQLite database instance (WAL mode enabled)
│
├── tests/                     # Automated Verification Suites
│   ├── test_auth.py           # Unit tests for JWT authentication & role-based access guards
│   ├── test_lifecycle.py      # State machine tests verifying linear order transitions & POD validation
│   ├── test_models.py         # Schema contract tests for cancellation and reassignment workflows
│   ├── test_sanity.py         # Route sanity tests checking 200/400/401/403/404 HTTP responses
│   └── test_e2e_browser.py    # Playwright browser E2E test verifying live UI workflows across personas
│
├── docs/                      # Executive Defense & System Documentation
│   ├── ARCHITECTURE.md        # Master system architecture, tier flows & state machine design
│   ├── ERD.md                 # Entity Relationship Diagram & relational schema dictionary
│   ├── TRADEOFFS.md           # One-page executive trade-off log & panel defense justifications
│   ├── DEMO_SCRIPT.md         # 10-minute live demonstration script with role handoffs
│   ├── TIMING_LOG.md          # Rehearsal timing logs & dry-run evaluation records
│   └── CONTRIBUTING.md        # Git workflow, branch naming & conventional commit rules
│
├── README.md                  # Main setup guide & project documentation
├── requirements.txt           # Python dependencies (fastapi, uvicorn, pydantic, httpx, pytest, playwright)
└── .gitignore                 # Excludes virtual environments, SQLite database locks & temporary caches
```

---

## 5. Local Setup & Running Instructions

### Prerequisites:
* Python 3.10 or higher installed
* Modern web browser (Chrome, Firefox, Safari or Edge)

### Step 1: Clone the Repository
```bash
git clone https://github.com/JDILEMMAX/reflex-dispatch-system.git
cd reflex-dispatch-system
```

### Step 2: Set Up Virtual Environment & Dependencies
1. Create and activate a Python virtual environment:
   ```bash
   python -m venv reflex-dispatch-system
   source reflex-dispatch-system/bin/activate  # On Windows: reflex-dispatch-system\Scripts\activate
   ```
2. Install the required Python packages and browser testing drivers:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
3. Initialize and seed the database with mock Kenyan retail data:
   ```bash
   python data/seed.py
   ```

### Step 3: Start the Backend Server
```bash
uvicorn backend.main:app --reload
```
The API server and static frontend will be live at `http://127.0.0.1:8000`. You can inspect interactive OpenAPI documentation at `http://127.0.0.1:8000/docs`.

### Step 4: Run the Complete Test Suite
Execute the automated test suites to verify authentication, state transitions and browser E2E workflows:
```bash
# Run unit and integration tests
pytest tests/test_auth.py tests/test_lifecycle.py tests/test_sanity.py

# Run Playwright automated browser E2E test
pytest tests/test_e2e_browser.py
```

---

## 6. Seeded Demo Accounts (For Live Evaluation)

The database seeder pre-configures representative accounts across all roles (default password for all demo accounts is `Reflex2026!`):

| Role | Username | Display Name | Associated Entity / Territory |
| :--- | :--- | :--- | :--- |
| **Retailer** | `luthuli_electronics` | Maina K. (Luthuli Electronics) | Electronics Shop (Luthuli Ave, Nairobi) |
| **Retailer** | `cbd_pharmacy` | Dr. Achieng O. (CBD Chemist) | Pharmacy (Kimathi Street, Nairobi) |
| **Dispatcher**| `nairobi_dispatch` | Kamau N. (Nairobi Central Hub) | Central Fleet Dispatcher |
| **Rider** | `rider_mwangi` | John Mwangi | Boxer 150 (Reg: `KMDF 420X`) |
| **Rider** | `rider_otieno` | Peter Otieno | TVS Star (Reg: `KMEB 819Y`) |

---

## 7. Core REST API Route Specification

| HTTP Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Public | Authenticates credentials and returns a Bearer JWT token. |
| `GET` | `/api/auth/me` | Authenticated | Retrieves current authenticated user profile and active role. |
| `POST` | `/api/orders` | Retailer Only | Logs a new delivery request and generates QR/PIN verification tokens. |
| `GET` | `/api/orders/retailer` | Retailer Only | Retrieves all orders originated by the authenticated retailer. |
| `GET` | `/api/dispatch/orders` | Dispatcher Only | Lists all active orders across unassigned, in-transit and completed queues. |
| `POST` | `/api/dispatch/assign` | Dispatcher Only | Assigns an open delivery request to a selected active rider. |
| `GET` | `/api/rider/tasks` | Rider Only | Retrieves tasks currently assigned to the authenticated rider. |
| `POST` | `/api/rider/milestone` | Rider Only | Transitions delivery status (`PICKED_UP`, `ARRIVED`, `DELIVERED`). |
| `GET` | `/api/track/{order_id}` | Public | Public tracking route returning live milestone status and timestamps. |

---

## 8. Engineering Governance & Deliverables Index

* **Engineering Pod:** Commit Crew (Group 92)
* **Team Lead & Systems Architect:** Jesse Vincent (`jdilemmax`)
* **Master System Architecture:** [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)
* **Entity Relationship Diagram:** [`docs/ERD.md`](./docs/ERD.md)
* **One-Page Trade-Off Log:** [`docs/TRADEOFFS.md`](./docs/TRADEOFFS.md)
* **Executive Presentation Script:** [`docs/DEMO_SCRIPT.md`](./docs/DEMO_SCRIPT.md)
* **Rehearsal Timing Logs:** [`docs/TIMING_LOG.md`](./docs/TIMING_LOG.md)
* **Git Contribution Guidelines:** [`docs/CONTRIBUTING.md`](./docs/CONTRIBUTING.md)