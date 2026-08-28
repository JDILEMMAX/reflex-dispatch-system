# Repository Contribution Guidelines & Engineering Governance

**System Name:** Reflex On-Demand Dispatch & Chain of Custody System  
**Document Classification:** Engineering Standards, Git Hygiene & Audit Protocol  
**Pod:** Commit Crew (Group 92)  
**Lead Architect:** Jesse Vincent (`jdilemmax`)  

---

## 1. Engineering Philosophy & Audit Integrity

To satisfy the strict industry evaluation criteria of the 1MILL Devs Readiness Sprint under Power Learn Project Africa, the Commit Crew adheres to strict version control standards. Direct pushes to the `main` branch are restricted. Every line of code, migration script, test suite and documentation update must enter the repository through traceable, peer-reviewed Pull Requests with auditable conventional commit messages.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          THE COMMIT CREW GIT GOVERNANCE CYCLE                          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. BRANCH:   Create isolated feature branch from latest main (feat/, fix/, docs/)      │
│ 2. COMMIT:   Commit small, atomic changes: <type>: <what changed> - <why it matters>   │
│ 3. TEST:     Run full automated test suite locally (pytest tests/ must pass 100%)      │
│ 4. PR & REV: Open PR with issue link (Closes #X), obtain peer review approval          │
│ 5. PRUNE:    Merge into main and immediately delete feature branch to prevent drift    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Branch Naming Conventions

All contributors must branch off an updated `main` branch using structured, lowercase prefixes separated by hyphens. Generic branch names (such as `test`, `patch` or `updates`) are strictly prohibited.

| Branch Prefix | Usage Scope | Compliant Examples |
| :--- | :--- | :--- |
| **`feat/`** | New features, API routes, state machine logic or UI views | `feat/jwt-auth-gateway`<br>`feat/rider-pod-terminal`<br>`feat/customer-stepper-ui` |
| **`fix/`** | Bug fixes, state machine boundary patches or error handling | `fix/sqlite-lock-timeout`<br>`fix/duplicate-scan-rejection`<br>`fix/cors-header-origin` |
| **`docs/`** | Architectural documentation, ERD diagrams, scripts or logs | `docs/architecture-specification`<br>`docs/erd-schema-dictionary`<br>`docs/timing-log-audit` |
| **`test/`** | Unit test suites, integration tests or Playwright E2E tests | `test/state-machine-lifecycle`<br>`test/auth-rbac-security`<br>`test/e2e-browser-flows` |
| **`chore/`** | Build tasks, package dependencies, seeders or configuration | `chore/database-seeder-kenya`<br>`chore/requirements-playwright`<br>`chore/render-deploy-config` |

---

## 3. Mandatory Commit Message Standards

Generic commit messages (such as `"wip"`, `"changes"`, `"fixed stuff"` or `"more updates"`) fail our procurement audit. Every single commit must follow the strict three-part syntax:

```text
<type>: <what changed> - <why it matters>
```

### Approved Commit Types:
* `feat`: A new user-facing feature or backend endpoint
* `fix`: A bug fix or security patch
* `docs`: Documentation updates, architecture diagrams or rehearsal logs
* `style`: Formatting, CSS whitespace or cosmetic visual tweaks with zero logic changes
* `refactor`: Code restructuring without modifying behavior or API contracts
* `test`: Adding or refactoring automated unit, integration or E2E browser tests
* `chore`: Dependency updates, `.gitignore` tweaks or database seed data generation

### Compliant Commit Examples:
* `feat: implement dual-factor POD verification endpoint - prevents unauthorized order completion without customer PIN`
* `fix: enable WAL journal mode and busy timeout pragma - eliminates SQLite table lock contention during concurrent writes`
* `docs: finalize 10-minute presentation script and handoff cues - prepares pod for live mock panel defense`
* `test: add Playwright E2E browser test for multi-role workflows - verifies end-to-end user journeys from order entry to delivery`
* `chore: seed database with authentic Kenyan retail profiles - provides verified test accounts for live evaluation`

---

## 4. Pull Request (PR) & Peer Review Protocol

All code entering `main` must follow this step-by-step workflow:

1. **Synchronize Local Main:** Before creating a branch, pull the latest changes:
   ```bash
   git checkout main && git pull origin main
   ```
2. **Create Feature Branch:**
   ```bash
   git checkout -b feat/your-feature-name
   ```
3. **Write & Verify Code:** Ensure all code adheres to PEP 8 standards and passes all automated tests locally:
   ```bash
   pytest tests/
   ```
4. **Atomic Commit:** Stage and commit using the mandatory format:
   ```bash
   git add .
   git commit -m "feat: implement retailer order entry modal - allows staff to log deliveries with automatic PIN generation"
   ```
5. **Push to Remote:**
   ```bash
   git push -u origin feat/your-feature-name
   ```
6. **Open Pull Request:** Navigate to GitHub, open a PR against `main`, and include:
   * A concise summary of changes
   * The explicit issue closing keyword (e.g. `Closes #3`)
   * Assigned reviewer tags
7. **Peer Review & Approval:** At least one pod member or the Team Lead (`jdilemmax`) must review the diff, verify test coverage and approve.
8. **Merge & Prune:** Merge via clean merge commit and immediately delete the remote and local feature branches to prevent branch sprawl:
   ```bash
   git checkout main && git pull origin main && git fetch -p && git branch -D feat/your-feature-name
   ```

---

## 5. Security, Secret Management & Repository Hygiene

To maintain high software engineering standards, the following files and directories must never be committed to version control:

* **Virtual Environments:** `reflex-dispatch-system/`, `.venv/`, `env/` (enforced via `.gitignore`)
* **Compiled Bytecode:** `__pycache__/`, `*.pyc`, `*.pyo`
* **Test Artifacts:** `.pytest_cache/`, `test-results/`, `playwright-report/`
* **Active SQLite Database Instances:** `data/reflex.db`, `data/reflex.db-wal`, `data/reflex.db-shm` (only `data/schema.sql` and `data/seed.py` are tracked)
* **Local Secrets & Tokens:** Never hardcode raw secret keys or production JWT secrets in source code; load them through environment variables or secure defaults.

---

## 6. Pod Role Distribution & Domain Ownership

| Team Member | GitHub Handle | Core Domain Ownership | Primary File Responsibilities |
| :--- | :--- | :--- | :--- |
| **Jesse Vincent** | `@jdilemmax` | Team Lead, Security & Architecture | `backend/auth.py`, `backend/main.py`, `docs/ARCHITECTURE.md` |
| **Silvya Atieno** | `@oswaldsly` | Frontend Lead & UX Engineer | `frontend/index.html`, `frontend/tracker.html`, `frontend/styles.css` |
| **Peter Kuria** | `@peakaykush` | Full-Stack Integration & QA Lead | `frontend/app.js`, `tests/test_e2e_browser.py`, `docs/DEMO_SCRIPT.md` |
| **Aphane Ginah** | `@ginahAphane` | Database Architect & Data Modeler | `data/schema.sql`, `data/seed.py`, `docs/ERD.md` |
| **Ahmed Abdi Ibrahim** | `@ahmedabdy590-spec`| Backend Engineer & Systems Specialist | `backend/state_machine.py`, `backend/queue_manager.py`, `docs/TRADEOFFS.md` |

---

## 7. Zero-Tolerance Formatting Rules

All contributors must uphold the following stylistic constraints across all commit messages, code comments, test outputs and documentation files:

1. **No Oxford Commas:** Never place a comma before the conjunction in a list (e.g. use *"retailer, dispatcher and rider"*, never *"retailer, dispatcher, and rider"*).
2. **No Long Dashes:** Never use em-dashes (`—`) or en-dashes (`–`). Always use standard hyphens, colons, parentheses or clear sentence breaks.
3. **Professional Tone:** Keep all technical documentation direct, human, empathetic to the Kenyan market context and free of generic AI fluff.