# CVMatcher

> **Turn a CV and a target role into clear, evidence-backed career priorities.**

<p align="center">
  <img src="https://img.shields.io/github/actions/workflow/status/Adam-Ghanem/Cvmatcher/ci.yml?label=CI" alt="CI">
  <img src="https://img.shields.io/github/license/Adam-Ghanem/Cvmatcher" alt="License">
  <img src="https://img.shields.io/github/stars/Adam-Ghanem/Cvmatcher" alt="GitHub stars">
  <img src="https://img.shields.io/github/commit-activity/m/Adam-Ghanem/Cvmatcher" alt="Commit activity">
</p>

CVMatcher is a privacy-focused career intelligence platform that compares a user's CV with a target role and turns the available evidence into **transparent, reproducible matching signals and actionable gaps**.

The goal is simple: help people understand **what their CV demonstrates, what a target role asks for, and where the evidence is missing** — without pretending to predict hiring outcomes.

## ✨ Highlights

- 📄 Secure CV intake and bounded text extraction
- 🎯 Target-role and job-description matching
- 🧠 Deterministic evidence scoring
- 🔎 Skills, experience, keywords, education & ATS signals
- 📊 Transparent weighted match components
- 📝 Clear evidence gaps — *"Not found in the provided CV"*
- 🔐 Owner-scoped private data
- 🛡️ Authentication & CSRF protection
- 📦 Typed API contracts
- 🧪 Automated frontend and backend testing

## 🏗️ Architecture

```text
                    ┌─────────────────────┐
                    │      Web Client     │
                    │      Next.js         │
                    └──────────┬──────────┘
                               │
                         Typed API / CSRF
                               │
                    ┌──────────▼──────────┐
                    │      FastAPI API     │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
   ┌──────▼──────┐      ┌──────▼──────┐      ┌──────▼──────┐
   │ CV Intake   │      │ Role Intake │      │   Analysis  │
   │ & Extraction│      │ & Validation│      │   Engine    │
   └──────┬──────┘      └──────┬──────┘      └──────┬──────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Evidence / Contracts│
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │     PostgreSQL      │
                    │ Private persistence │
                    └─────────────────────┘
```

The system separates **identity, private document handling, extraction, target-role intake, deterministic analysis, persistence, and API contracts** so each boundary can be secured and tested independently.

## 🧠 How Matching Works

CVMatcher uses deterministic, source-controlled rules rather than opaque predictions.

A match is composed of weighted evidence signals such as:

| Signal | Weight |
|---|---:|
| Skills | 35% |
| Experience evidence | 20% |
| Controlled keywords | 25% |
| Education | 10% |
| ATS structure | 10% |

Every result is tied to the evidence available in the provided CV. Missing evidence is reported as a gap rather than treated as proof that the candidate lacks the underlying skill or experience.

## 🔐 Privacy & Security

Privacy is a core architectural boundary, not an afterthought.

- Private CV and role data is owner-scoped
- Raw CV and job-description text is not exposed through analysis responses
- Authentication and CSRF protection guard sensitive operations
- Extraction is bounded and treated as untrusted document data
- Analysis uses deterministic local rules
- Production secrets are kept outside source control
- Security and dependency checks are integrated into CI

## 🛠️ Built With

- **Next.js / TypeScript**
- **FastAPI / Python**
- **PostgreSQL**
- **Alembic**
- Typed frontend/backend contracts
- Automated tests and security checks

## 🚀 Quick Start

```bash
cp .env.example .env
pnpm install --frozen-lockfile

# Start PostgreSQL
docker compose up -d postgres

# Apply migrations
cd services/api
alembic upgrade head

# Start API
uvicorn app.main:app --reload
```

In another terminal:

```bash
pnpm web:dev
```

## 🏅 Engineering Quality

CVMatcher is built with a security-first engineering workflow including **CI, strict type checking, automated tests, dependency auditing, and secret scanning**.

> CVMatcher is a career-planning and evidence-analysis tool. It does not predict hiring decisions or guarantee employment outcomes.

## 📄 License

CVMatcher is released under the **MIT License**. See [`LICENSE`](LICENSE) for the full license text.

## 🔭 Vision

CVMatcher aims to become a trustworthy career-intelligence layer where users can understand the relationship between their experience and real-world opportunities through **evidence, transparency, privacy, and actionable insight**.

## 🤝 Contributing

Contributions, ideas, experiments, and improvements are welcome.

---

<p align="center">
  <strong>CVMatcher</strong><br>
  <em>Evidence in. Better career decisions out.</em>
</p>
