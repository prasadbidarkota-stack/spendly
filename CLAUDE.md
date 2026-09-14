# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

**Spendly** is a Flask expense tracker being built incrementally as a step-by-step learning project. Most of the backend is currently unimplemented scaffolding:

- `database/db.py` contains only a docstring describing what to build — `get_db()`, `init_db()`, and `seed_db()` do not exist yet.
- `app.py` has working routes for `/`, `/register` (GET), and `/login` (GET), but `/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, and `/expenses/<id>/delete` are placeholder stubs that just return a string like `"Logout — coming in Step 3"`.
- There is no auth, session handling, or database wiring yet — `register.html` and `login.html` POST to `/register` and `/login`, but no POST handlers exist.
- `static/js/main.js` is an empty stub for future JS.

When asked to implement one of these pieces, follow the step markers in `app.py` comments (`Step 3`, `Step 4`, `Step 7`, `Step 8`, `Step 9`) and the contract described in `database/db.py`'s docstring as the source of truth for what's expected, rather than assuming a different design.

## Commands

```bash
# Activate virtualenv (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the dev server (http://localhost:5001)
python app.py

# Run tests
pytest
```

There is no lint/format tooling configured in this repo.

## Architecture

- **Flask app factory-less, single-module app**: `app.py` creates `app = Flask(__name__)` at module scope and defines all routes directly — no blueprints.
- **Database layer**: SQLite, accessed through `database/db.py` (currently a stub). The intended pattern per its docstring is a `get_db()` returning a connection with `row_factory` and foreign keys enabled, `init_db()` creating tables with `CREATE TABLE IF NOT EXISTS`, and `seed_db()` for sample dev data. The DB file (`expense_tracker.db`) is gitignored and created locally.
- **Templates**: Jinja2 templates in `templates/` extend `templates/base.html`, which defines the nav/footer chrome and pulls in `static/css/style.css` and `static/js/main.js` via `{% block content %}` / `{% block scripts %}`. Auth pages (`login.html`, `register.html`) render an `{% if error %}` block for server-side validation errors passed into the template context.
- **Forms → routes**: `register.html` posts `name`/`email`/`password` to `/register`; `login.html` posts `email`/`password` to `/login`. Both currently only have GET handlers.
- **Static assets**: single CSS file (`static/css/style.css`, ~530 lines) driving the whole UI (uses DM Serif Display / DM Sans via Google Fonts, loaded in `base.html`); JS is not yet used.
- Dev server runs on port `5001` (not Flask's default 5000).
