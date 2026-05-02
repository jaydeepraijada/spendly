
# Spec: Backend Routes for Profile Page

## Overview
Extend the profile page with edit functionality so users can update their display name, email address, and password directly from `/profile`. Step 04 delivered the read-only profile UI; this step adds the backend POST route and a minimal inline edit form. It follows the same session-guard pattern established in Step 04 and keeps all validation server-side, consistent with the register/login routes.

## Depends on
- Step 01 — Database Setup (`get_db`, `users` table must exist)
- Step 02 — Registration (user records must exist)
- Step 03 — Login and Logout (session must be set; `session["user_id"]` written on login)
- Step 04 — Profile Page Design (profile template and GET `/profile` route must exist)

## Routes
- `GET /profile` — already implemented; no changes to the read path
- `POST /profile/edit` — update name, email, and/or password for the logged-in user — logged-in only
- `GET /profile/edit` — render the edit form pre-populated with current user data — logged-in only

## Database changes
No new tables or columns. The existing `users` table already has `name`, `email`, and `password_hash`.

## Templates
- **Create:**
  - `templates/profile_edit.html` — edit form with name, email, current password (required for any change), and optional new password fields
- **Modify:**
  - `templates/profile.html` — add an "Edit profile" button/link pointing to `url_for("edit_profile")`

## Files to change
- `app.py` — add `GET /profile/edit` and `POST /profile/edit` routes
- `templates/profile.html` — add "Edit profile" link

## Files to create
- `templates/profile_edit.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with werkzeug — use `check_password_hash` to verify current password before any change, `generate_password_hash` for new password
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Both `/profile/edit` routes must redirect to `url_for("login")` if `session.get("user_id")` is falsy
- Current password field is always required — validate it server-side before applying any update
- Email uniqueness: catch `sqlite3.IntegrityError` and return an error if the new email is already taken by another account
- New password is optional — only update `password_hash` if the new password field is non-empty; validate minimum 8 characters if provided
- On success, update `session["user_name"]` if the name changed, then redirect to `url_for("profile")` with no flash message (keep it simple)
- On validation error, re-render the edit form with the error and preserve non-sensitive field values (name, email — never password)

## Definition of done
- [ ] `GET /profile/edit` while logged out redirects to `/login`
- [ ] `GET /profile/edit` while logged in renders the edit form (200) pre-populated with current name and email
- [ ] Submitting the form with a wrong current password shows an inline error and does not update the database
- [ ] Submitting with a valid current password and a new name updates `users.name` in the database
- [ ] Submitting with a valid current password and a new email updates `users.email` in the database
- [ ] Submitting with a duplicate email shows an inline error ("Email already in use")
- [ ] Submitting with a new password shorter than 8 characters shows an inline error
- [ ] Submitting with a valid new password updates `users.password_hash` in the database
- [ ] After a successful update the user is redirected to `/profile` and the updated name/email is displayed
- [ ] If the name changed, the navbar reflects the new name immediately (session updated)
- [ ] App starts without errors (`python app.py`)
