# Spec: Login and Logout

## Overview
Implement the login form POST handler and the logout route so users can authenticate with their email and password and end their session. The `login.html` template already exists as a stub from Step 01; this step wires up the POST handler, verifies the password hash, writes the session, and redirects on success. The logout route clears the session and redirects to the landing page. After this step, a registered user can sign in and sign out — completing the authentication loop opened by Step 02.

## Depends on
- Step 01 — Database Setup (`get_db`, `users` table must exist)
- Step 02 — Registration (user records with hashed passwords must exist in the database)

## Routes
- `GET /login` — render login form — public (already exists, convert to accept both methods)
- `POST /login` — handle form submission, verify credentials, create session, redirect — public
- `GET /logout` — clear session, redirect to landing page — logged-in (currently stubbed as a string)

## Database changes
No database changes. The `users` table from Step 01 already has all required columns.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — add a POST form with email and password fields; render `{{ error }}` for validation/auth failures; preserve email input on failure with `value="{{ email or '' }}"`.

## Files to change
- `app.py` — convert `/login` route to accept `GET, POST`; implement POST logic (lookup user by email, verify password, set session, redirect); implement `/logout` (clear session, redirect to landing); import `check_password_hash` from `werkzeug.security`.
- `templates/login.html` — add form markup, error display, and preserved-value attributes.

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug` is already installed with Flask.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords verified with `werkzeug.security.check_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- On login failure (user not found OR wrong password) show the same generic error: "Invalid email or password." — never reveal which field was wrong
- On successful login store `user_id` and `user_name` in `session` and redirect to `/` (dashboard does not exist yet)
- Logout must call `session.clear()` and redirect to `url_for('landing')`
- Strip whitespace from email before querying
- Do not expose internal errors (500) to the user — catch lookup failures gracefully

## Definition of done
- [ ] `GET /login` renders the login form (no regression)
- [ ] Submitting valid credentials sets `session["user_id"]` and `session["user_name"]` and redirects to `/`
- [ ] Submitting an unregistered email re-renders the form with "Invalid email or password."
- [ ] Submitting the correct email with the wrong password re-renders the form with "Invalid email or password."
- [ ] Email field is repopulated with the user's input after a failed attempt
- [ ] `/logout` clears the session and redirects to the landing page
- [ ] After logout, visiting `/logout` again still redirects to the landing page (no error)
- [ ] The demo user (`demo@spendly.com` / `demo123`) can log in successfully
- [ ] App starts without errors (`python app.py`)
