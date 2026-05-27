# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LAMAN (Lexicon of Ancient Mesopotamian and Anatolian Names) is a Django web application for researching Hittite personal names, place names, and deities from cuneiform texts. It serves academic researchers studying ancient Anatolian civilizations.

- **Live site**: laman.hittites.org
- **Framework**: Django 5.2.10, Python 3.x
- **Database**: SQLite3 (db.sqlite3)
- **Frontend**: Django templates with server-side rendering, minimal JavaScript

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python manage.py runserver

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Collect static files for production
python manage.py collectstatic --noinput

# Create admin user
python manage.py createsuperuser

# Deploy to production (push to origin first, then run)
bash scripts/deploy.sh
```

No test suite or linter is currently configured.

## Architecture

The project has a single Django app (`namefinder`) within the `laman` project.

### Models (namefinder/models.py)

Three core models with several lookup/reference tables:

- **Name** — Core entity. Has a `query` field that is auto-normalized on save (removes accents like ḫ→h/š→s, collapses repeated letters, normalizes similar sounds g=k/b=p/d=t) for fuzzy searching. Has `is_fragmentary` flag for incomplete readings (hidden from search by default). Related to lookup tables: `NameType` (person/place/deity), `WritingType`, `CompletenessType`, `Milieu`, `Determinative` (M2M).
- **Fragment** — A cuneiform tablet/text reference. Organized by `Series` (KBo, KUB, etc.) and linked to CTH (Catalogue des Textes Hittites) numbers. Contains archaeological metadata (find spot, inventory number, dating).
- **Instance** — An attestation linking a Name to a Fragment (with line reference, spelling, writing type). Name FK is nullable — unlinked attestations (name=NULL) are supported and browsable via `/attestations/`.
- **DataReport** — User-submitted problem reports on names/fragments, with status tracking (open/resolved/dismissed). Listed in Data Problems page under Reports tab.
- **ChangeLog** — Audit trail storing old/new data as JSON, supports reverting changes.

### Views

Two view modules serve different purposes:

- **views.py** — Server-rendered page views: search pages (names, fragments, CTH, attestations), detail pages, CRUD forms, CSV exports, network visualization, data problems (admin).
- **api_views.py** — AJAX/JSON API endpoints for inline editing of names, instances, and fragments. Includes data problems API (delete/keep names) and report submission/resolution endpoints. All mutating API endpoints require authentication and log changes to ChangeLog.

### URL Structure

All routes are under the `namefinder` app namespace. Key patterns:
- `/` — Name search with filtering (type, writing, completeness, milieu, date)
- `/name/<pk>/` — Name detail with all attestations
- `/fragments/` — Fragment search by series
- `/fragment/<pk>/` — Fragment detail
- `/cth/` — CTH catalogue search (two-level hierarchical dropdowns)
- `/cth/<number>/` — CTH detail with related fragments/attestations
- `/attestations/` — Attestation search with filters (independent of names, supports unlinked attestations)
- `/api/` — JSON endpoints for inline CRUD operations
- `/network/` — Co-occurrence network visualization (uses NetworkX + python-louvain)
- `/data-problems/` — Admin-only page for reviewing data quality issues (fragmentary names, user reports)

### Static Assets

- `namefinder/static/css/style.css` — Main stylesheet (~2400 lines)
- `namefinder/static/css/guide.css` — User guide page styles
- `namefinder/static/js/script.js` — Minimal frontend JS

### Configuration

- Environment variables via `python-decouple`: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` (see `.env.example`)
- Static files served via WhiteNoise middleware
- Production: Nginx → Gunicorn (unix socket) → Django (see `deploy/` directory)

## Domain Context

This is a philological/academic tool. Key domain concepts:
- **CTH numbers**: Standard classification system for Hittite texts
- **Determinatives**: Classifier symbols prefixed to cuneiform names
- **Series** (KBo, KUB, etc.): Publication series for cuneiform tablet editions
- **Milieu**: Cultural context of a name (Western Semitic, Hattian, Hurrian, etc.)
- Names support cuneiform Unicode characters and specialized diacritics (ḫ, š, etc.)
