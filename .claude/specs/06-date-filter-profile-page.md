# Spec: Date Filter for Profile Page

## Overview
Extend the `/profile` page so users can filter their expenses by a date range and see a matching expense list below their stats. Right now the profile shows only a total expense count; this step adds an optional "from / to" date filter form (submitted as GET query parameters) and a table of matching expenses. When no filter is applied the page shows all expenses. This gives users a lightweight way to review spending over a period without navigating away from the profile.

## Depends on
- Step 01 — Database Setup (`get_db`, `expenses` table with `date` column must exist)
- Step 02 — Registration (user records must exist)
- Step 03 — Login and Logout (session with `session["user_id"]` must be set on login)
- Step 04 — Profile Page Design (`/profile` route and `profile.html` template must exist)
- Step 05 — Backend Routes for Profile Page (profile edit flow must be complete)

## Routes
- `GET /profile?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` — same route as before, now accepts optional query params to filter the expense list — logged-in only

No new routes.

## Database changes
No database changes. The existing `expenses` table already has `date TEXT NOT NULL` (stored as `YYYY-MM-DD`), `amount`, `category`, and `description`.

## Templates
- **Create:** none
- **Modify:**
  - `templates/profile.html` — add:
    1. A date filter form (`method="get"`, `action="{{ url_for('profile') }}"`) with two `<input type="date">` fields (`date_from`, `date_to`) and a "Filter" submit button plus a "Clear" link back to `/profile`
    2. A summary line below the stat card: "Showing X of Y expenses" (filtered count vs. total count)
    3. An expenses table listing the filtered results with columns: Date, Category, Description, Amount — sorted newest first
    4. An empty-state message when the filtered result is empty

## Files to change
- `app.py` — update the `profile` view function to:
  - Read `date_from` and `date_to` from `request.args` (strip and default to `""`)
  - Build a parameterised SQL query against `expenses` for the logged-in user, adding `AND date >= ?` / `AND date <= ?` clauses only when the respective param is non-empty
  - Pass `expenses`, `filtered_count`, `expense_count` (total, unfiltered), `date_from`, and `date_to` to the template
- `templates/profile.html` — add filter form, summary line, expenses table, and empty state

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL; build the WHERE clause by conditionally appending `?` placeholders and a matching params list
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `GET /profile` must still redirect to `/login` if `session.get("user_id")` is falsy
- `date_from` and `date_to` are optional — omitting either removes that bound from the filter
- Date inputs must be re-populated with the current filter values after submit (use `value="{{ date_from }}"` etc.)
- The "Clear" link must point to `url_for('profile')` with no query params
- Expenses in the table must be ordered `ORDER BY date DESC, id DESC`
- Amount column must be formatted to 2 decimal places in the template (e.g. `{{ "%.2f"|format(e.amount) }}`)
- Keep the existing profile info card and stat card unchanged — only add new elements below

## Definition of done
- [ ] `GET /profile` while logged out redirects to `/login`
- [ ] `GET /profile` with no query params renders all expenses in the table (no filter applied)
- [ ] The stat card still shows the correct total expense count regardless of filter
- [ ] The summary line reads "Showing X of Y expenses" with correct counts
- [ ] Submitting `date_from` only returns all expenses on or after that date
- [ ] Submitting `date_to` only returns all expenses on or before that date
- [ ] Submitting both `date_from` and `date_to` returns only expenses within that inclusive range
- [ ] Date inputs are pre-filled with the submitted values after filtering
- [ ] The "Clear" link removes all filter params and shows the full list again
- [ ] When no expenses match the filter an empty-state message is displayed (not an empty table)
- [ ] Expenses in the table are sorted newest-first
- [ ] Amount column is formatted to 2 decimal places
- [ ] App starts without errors (`python app.py`)
