# Spec: Profile Page Design

## Overview
Implement the `/profile` route and its template so a logged-in user can view their account information: display name, email address, and account creation date. The page also shows a summary stat (total number of expenses) pulled from the `expenses` table. This is a read-only view — no editing in this step. It establishes the authenticated inner-app layout pattern (redirect guests to `/login`) that later steps (add/edit/delete expense) will reuse.

## Depends on
- Step 01 — Database Setup (`get_db`, `users` and `expenses` tables must exist)
- Step 02 — Registration (user records must exist)
- Step 03 — Login and Logout (session must be set; `session["user_id"]` and `session["user_name"]` must be written on login)

## Routes
- `GET /profile` — render the profile page for the currently logged-in user; redirect to `/login` if no session — logged-in only

## Database changes
No database changes. The `users` table already has `name`, `email`, and `created_at`. The `expenses` table already has `user_id`.

## Templates
- **Create:**
  - `templates/profile.html` — profile page showing user info card and expense count stat
- **Modify:**
  - `templates/base.html` — add conditional nav links: show "Profile" and "Sign out" when `session.user_id` is set; show "Sign in" and "Get started" when not

## Files to change
- `app.py` — implement `/profile` route: check session, query `users` by `id`, query expense count for user, pass data to template
- `templates/base.html` — update nav to be session-aware

## Files to create
- `templates/profile.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with werkzeug (no password changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- If `session.get("user_id")` is falsy, redirect to `url_for("login")` immediately — do not render the page
- Query the `users` row by `id = session["user_id"]`; if the row is missing (deleted account edge case) clear the session and redirect to `/login`
- Format `created_at` for display (e.g. "April 2026") — do this in Python, not in the template
- The profile card must use existing CSS variables only; no inline styles with hardcoded colours
- Nav changes must use `session` from the Jinja2 context — Flask automatically exposes `session` to templates

## Definition of done
- [ ] `GET /profile` while logged out redirects to `/login`
- [ ] `GET /profile` while logged in renders a page (200) — no "coming soon" string
- [ ] Page displays the logged-in user's name and email address
- [ ] Page displays the account creation date in a human-readable format
- [ ] Page displays the user's total expense count (0 or more)
- [ ] Navbar shows "Profile" and "Sign out" links when the user is logged in
- [ ] Navbar shows "Sign in" and "Get started" links when the user is logged out
- [ ] Clicking "Sign out" in the navbar calls `/logout` and clears the session
- [ ] Clicking "Profile" in the navbar navigates to `/profile`
- [ ] App starts without errors (`python app.py`)
