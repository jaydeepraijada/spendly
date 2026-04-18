# Spec: Registration

## Overview
Wire up the registration form so new users can create a Spendly account. The `register.html` template and `users` table already exist from Step 1; this step adds the POST handler, server-side validation, password hashing, session creation, and a redirect on success. After this step, a visitor can sign up and be taken to the login page — it is the first user-facing interaction that writes to the database.

## Depends on
- Step 01 — Database Setup (`get_db`, `init_db`, `users` table must exist)

## Routes
- `GET /register` — render registration form — public (already exists, no change needed)
- `POST /register` — handle form submission, create user, redirect — public

## Database changes
No database changes. The `users` table created in Step 01 already has all required columns (`id`, `name`, `email`, `password_hash`, `created_at`).

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html` — already renders `{{ error }}`; no structural changes needed. Re-render with `value` attributes on name/email inputs to preserve user input on validation failure (add `value="{{ name or '' }}"` and `value="{{ email or '' }}"`).

## Files to change
- `app.py` — add `app.secret_key`, import `request`, `redirect`, `url_for`, `session` from flask; import `get_db` from `database.db`; import `generate_password_hash` from `werkzeug.security`; convert `/register` route to accept `GET, POST`; implement POST logic.

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug` is already installed with Flask.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Catch `sqlite3.IntegrityError` to handle duplicate email gracefully (re-render form with error message, do not let a 500 surface to the user)
- After successful registration, store `user_id` and `user_name` in `session` and redirect to `/login` (dashboard does not exist yet)
- Validate server-side: name non-empty, valid email format (basic), password ≥ 8 characters — return the form with a descriptive `error` string on failure
- Strip whitespace from name and email before inserting
- `app.secret_key` must be set before any session use; use a hard-coded dev string for now (e.g. `"dev-secret-change-in-prod"`)

## Definition of done
- [ ] `GET /register` still renders the form (no regression)
- [ ] Submitting the form with valid data inserts a new row in `users` with a hashed password
- [ ] After successful registration the browser redirects to `/login`
- [ ] Submitting with an email that already exists re-renders the form with an error message (no 500)
- [ ] Submitting with a password shorter than 8 characters re-renders the form with an error message
- [ ] Submitting with an empty name re-renders the form with an error message
- [ ] Name and email fields are repopulated with the user's input after a validation failure
- [ ] Password is never stored in plain text — `password_hash` column contains a werkzeug hash
- [ ] App starts without errors (`python app.py`)
