# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the development server (port 5001)
python app.py

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run a single test file
pytest tests/test_foo.py
```

## Architecture

**Spendly** is a Flask-based personal expense tracker. The codebase is structured as a guided student project — many routes are stubbed out with placeholder strings and will be filled in across numbered steps.

### Request flow

`app.py` (single file, all routes) → `render_template(...)` → `templates/<name>.html` (extends `base.html`) → `static/css/style.css` + `static/js/main.js`

### Key files

- **`app.py`** — all Flask routes live here. Fully implemented: `/`, `/register`, `/login`, `/terms`, `/privacy`. Stubbed: `/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`.
- **`database/db.py`** — placeholder only; students will implement `get_db()`, `init_db()`, `seed_db()` using SQLite.
- **`templates/base.html`** — shared layout: sticky navbar, `{% block content %}`, footer with Terms/Privacy links, and `{% block scripts %}`. All pages extend this.
- **`static/css/style.css`** — single stylesheet for the entire app. Uses CSS custom properties defined in `:root` (colors, fonts, radii, max-widths). Font pair: `DM Serif Display` (headings/display) + `DM Sans` (body).

### Design tokens (`:root` in `style.css`)

| Variable | Value | Use |
|---|---|---|
| `--ink` | `#0f0f0f` | primary text |
| `--accent` | `#1a472a` | brand green (buttons, highlights) |
| `--accent-2` | `#c17f24` | warm gold accent |
| `--paper` | `#f7f6f3` | page background |
| `--paper-card` | `#ffffff` | card surfaces |
| `--font-display` | DM Serif Display | hero titles, section headings |
| `--font-body` | DM Sans | all body copy |
| `--max-width` | `1200px` | page content cap |
| `--auth-width` | `440px` | login/register form cap |

### Template conventions

- All pages: `{% extends "base.html" %}` + `{% block title %}` + `{% block content %}`
- Page-specific JS goes in `{% block scripts %}` at the bottom
- `url_for()` is used for all internal links and static assets
- The landing page (`landing.html`) contains inline vanilla JS for the YouTube demo modal — `data-src` pattern stops video on close by setting `iframe.src = ''`
