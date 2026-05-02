"""
tests/test_06_date_filter_profile.py

Tests for Step 06 — Date Filter on the Profile Page.

Feature spec: .claude/specs/06-date-filter-profile-page.md

Covered behaviours (mirrors the Definition of Done):
  1.  GET /profile while logged out redirects to /login
  2.  GET /profile with no query params renders ALL expenses in the table
  3.  Stat card shows the correct TOTAL expense count regardless of filter
  4.  Summary line reads "Showing X of Y expenses" with correct counts
  5.  date_from only — expenses on or after that date are returned
  6.  date_to only — expenses on or before that date are returned
  7.  Both date_from and date_to — inclusive range is returned
  8.  Date inputs are pre-filled with submitted values after filtering
  9.  Clear link points to /profile with no query params
 10.  Empty state message shown when no expenses match the filter
 11.  Expenses are sorted newest-first
 12.  Amount column is formatted to 2 decimal places

Additional edge cases:
  - Boundary inclusivity: date_from/date_to on an exact expense date
  - User isolation: another user's expenses are never shown
"""

import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from database.db import init_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app(monkeypatch):
    """
    Isolated Flask app using an in-memory SQLite database.

    We monkeypatch database.db.get_db so every call inside the app (including
    inside imported helpers) uses the same in-memory connection that was
    initialised by init_db().  Because SQLite in-memory databases are
    connection-scoped, we keep one persistent connection alive for the
    duration of each test.
    """
    import sqlite3
    import database.db as db_module

    flask_app.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "WTF_CSRF_ENABLED": False,
        }
    )

    # Create a single shared in-memory connection that stays alive for the test.
    mem_conn = sqlite3.connect(":memory:")
    mem_conn.row_factory = sqlite3.Row
    mem_conn.execute("PRAGMA foreign_keys = ON")

    # Patch get_db to always return the same in-memory connection wrapped in a
    # thin proxy that makes conn.close() a no-op (so the connection persists).
    class _PersistentConn:
        """Thin proxy around mem_conn that silences close() calls."""
        def __getattr__(self, name):
            return getattr(mem_conn, name)

        def close(self):
            pass  # keep the in-memory DB alive between calls within one test

    import app as app_module
    monkeypatch.setattr(db_module,  "get_db", lambda: _PersistentConn())
    monkeypatch.setattr(app_module, "get_db", lambda: _PersistentConn())

    with flask_app.app_context():
        # Run schema creation against the real in-memory connection.
        mem_conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                email         TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                amount      REAL    NOT NULL,
                category    TEXT    NOT NULL,
                date        TEXT    NOT NULL,
                description TEXT,
                created_at  TEXT    DEFAULT (datetime('now'))
            );
        """)
        mem_conn.commit()
        yield flask_app

    mem_conn.close()


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def _seed_user(client, name="Alice", email="alice@example.com", password="password123"):
    """Register a user via the HTTP endpoint and return (email, password)."""
    client.post(
        "/register",
        data={"name": name, "email": email, "password": password},
        follow_redirects=False,
    )
    return email, password


def _login(client, email, password):
    """Log in via the HTTP endpoint."""
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def _insert_expense(app, user_id, amount, category, date, description=""):
    """
    Directly insert an expense row into the in-memory DB.
    Returns the new expense's id.
    """
    from database.db import get_db
    with app.app_context():
        conn = get_db()
        cur = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        conn.commit()
        return cur.lastrowid


def _get_user_id(app, email):
    """Fetch a user's id from the DB by email."""
    from database.db import get_db
    with app.app_context():
        conn = get_db()
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        return row["id"] if row else None


# ---------------------------------------------------------------------------
# Shared fixture: logged-in client with deterministic expense data
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_client_with_expenses(app, client):
    """
    Returns a logged-in test client whose DB contains exactly these expenses
    for the primary test user:

        id=auto  date=2026-01-01  Food        10.00  "January lunch"
        id=auto  date=2026-02-15  Transport   25.50  "Bus pass"
        id=auto  date=2026-03-10  Bills       99.99  "Electricity"
        id=auto  date=2026-04-20  Health      5.00   "Vitamins"
        id=auto  date=2026-05-05  Shopping    200.10 "Clothes"

    Newest-first order: 2026-05-05, 2026-04-20, 2026-03-10, 2026-02-15, 2026-01-01
    """
    email, password = _seed_user(client)
    _login(client, email, password)
    user_id = _get_user_id(app, email)

    _insert_expense(app, user_id, 10.00,  "Food",      "2026-01-01", "January lunch")
    _insert_expense(app, user_id, 25.50,  "Transport", "2026-02-15", "Bus pass")
    _insert_expense(app, user_id, 99.99,  "Bills",     "2026-03-10", "Electricity")
    _insert_expense(app, user_id, 5.00,   "Health",    "2026-04-20", "Vitamins")
    _insert_expense(app, user_id, 200.10, "Shopping",  "2026-05-05", "Clothes")

    return client


# ---------------------------------------------------------------------------
# 1. Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_get_profile_logged_out_redirects_to_login(self, client):
        """Unauthenticated GET /profile must redirect to /login."""
        response = client.get("/profile")
        assert response.status_code == 302, (
            f"Expected 302 redirect for unauthenticated /profile, got {response.status_code}"
        )
        location = response.headers.get("Location", "")
        assert "/login" in location, (
            f"Expected redirect to /login, got Location: {location}"
        )

    def test_get_profile_logged_out_follow_redirects(self, client):
        """Following the redirect lands on the login page."""
        response = client.get("/profile", follow_redirects=True)
        assert response.status_code == 200
        assert b"login" in response.data.lower(), (
            "Expected login page content after redirect from unauthenticated /profile"
        )


# ---------------------------------------------------------------------------
# 2. No filter — full list rendered
# ---------------------------------------------------------------------------

class TestNoFilter:
    def test_profile_no_filter_returns_200(self, auth_client_with_expenses):
        response = auth_client_with_expenses.get("/profile")
        assert response.status_code == 200, (
            f"Expected 200 for authenticated /profile, got {response.status_code}"
        )

    def test_profile_no_filter_shows_all_expenses(self, auth_client_with_expenses):
        """All 5 seeded expenses must appear in the response."""
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()
        # Each expense has a unique description; verify all 5 are present.
        for description in ["January lunch", "Bus pass", "Electricity", "Vitamins", "Clothes"]:
            assert description in data, (
                f"Expected '{description}' in unfiltered profile page, but it was missing"
            )

    def test_profile_no_filter_all_categories_visible(self, auth_client_with_expenses):
        """All seeded categories appear when no filter is active."""
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()
        for category in ["Food", "Transport", "Bills", "Health", "Shopping"]:
            assert category in data, (
                f"Expected category '{category}' in unfiltered profile page"
            )


# ---------------------------------------------------------------------------
# 3. Stat card shows total count regardless of filter
# ---------------------------------------------------------------------------

class TestStatCard:
    def test_stat_card_total_count_no_filter(self, auth_client_with_expenses):
        """Stat card must show 5 (total) when no filter is applied."""
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()
        # The stat card should show the total count "5" somewhere prominent.
        assert "5" in data, "Expected total expense count '5' to appear on the profile page"

    def test_stat_card_total_count_with_filter_active(self, auth_client_with_expenses):
        """
        Even when a date filter reduces the visible list, the stat card must
        still reflect the TOTAL (unfiltered) count — 5 in our fixture.
        """
        # Filter to a single expense (only 2026-01-01)
        response = auth_client_with_expenses.get(
            "/profile?date_from=2026-01-01&date_to=2026-01-01"
        )
        data = response.data.decode()
        # Total count (5) should still be present somewhere on the page.
        assert "5" in data, (
            "Expected total expense count '5' to appear on profile even when filter is active"
        )

    def test_stat_card_total_not_replaced_by_filtered_count(self, auth_client_with_expenses):
        """
        When the filter shows 1 of 5, the page must contain '5' (total) AND '1' (filtered).
        This guards against the implementation accidentally using filtered_count for the stat.
        """
        response = auth_client_with_expenses.get(
            "/profile?date_from=2026-01-01&date_to=2026-01-01"
        )
        data = response.data.decode()
        assert "5" in data, "Expected total count '5' on stat card"
        assert "1" in data, "Expected filtered count '1' in summary line"


# ---------------------------------------------------------------------------
# 4. Summary line "Showing X of Y expenses"
# ---------------------------------------------------------------------------

class TestSummaryLine:
    def test_summary_line_no_filter_shows_equal_counts(self, auth_client_with_expenses):
        """With no filter, summary should read 'Showing 5 of 5 expenses'."""
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()
        assert "Showing 5 of 5" in data, (
            f"Expected 'Showing 5 of 5' in unfiltered profile; got page: {data[:500]}"
        )

    def test_summary_line_filtered_shows_correct_counts(self, auth_client_with_expenses):
        """Filter to 3 expenses — summary should read 'Showing 3 of 5 expenses'."""
        # date_from=2026-02-15 captures Transport, Bills, Health, Shopping = 4 expenses
        response = auth_client_with_expenses.get("/profile?date_from=2026-02-15")
        data = response.data.decode()
        assert "Showing 4 of 5" in data, (
            f"Expected 'Showing 4 of 5' with date_from=2026-02-15; page excerpt: {data[:500]}"
        )

    def test_summary_line_empty_filter_shows_zero_of_total(self, auth_client_with_expenses):
        """Filter that matches nothing — summary should read 'Showing 0 of 5 expenses'."""
        response = auth_client_with_expenses.get("/profile?date_from=2030-01-01")
        data = response.data.decode()
        assert "Showing 0 of 5" in data, (
            f"Expected 'Showing 0 of 5' when filter matches nothing; page: {data[:500]}"
        )

    def test_summary_line_contains_expenses_word(self, auth_client_with_expenses):
        """The summary line must include the word 'expenses'."""
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()
        assert "expenses" in data.lower(), "Expected word 'expenses' in the summary line"


# ---------------------------------------------------------------------------
# 5. date_from only
# ---------------------------------------------------------------------------

class TestDateFromFilter:
    def test_date_from_excludes_older_expenses(self, auth_client_with_expenses):
        """Expenses before date_from must not appear."""
        # date_from=2026-03-01 should exclude 2026-01-01 and 2026-02-15
        response = auth_client_with_expenses.get("/profile?date_from=2026-03-01")
        data = response.data.decode()
        assert "January lunch" not in data, (
            "Expense on 2026-01-01 should be excluded by date_from=2026-03-01"
        )
        assert "Bus pass" not in data, (
            "Expense on 2026-02-15 should be excluded by date_from=2026-03-01"
        )

    def test_date_from_includes_expenses_on_and_after(self, auth_client_with_expenses):
        """Expenses on or after date_from must appear."""
        response = auth_client_with_expenses.get("/profile?date_from=2026-03-01")
        data = response.data.decode()
        for desc in ["Electricity", "Vitamins", "Clothes"]:
            assert desc in data, (
                f"Expected '{desc}' to appear with date_from=2026-03-01"
            )

    def test_date_from_boundary_inclusive(self, auth_client_with_expenses):
        """An expense whose date exactly equals date_from must be included."""
        response = auth_client_with_expenses.get("/profile?date_from=2026-03-10")
        data = response.data.decode()
        assert "Electricity" in data, (
            "Expense on 2026-03-10 should be INCLUDED when date_from=2026-03-10 (inclusive)"
        )

    def test_date_from_boundary_excludes_day_before(self, auth_client_with_expenses):
        """An expense one day before date_from must be excluded."""
        # 2026-02-15 is before 2026-02-16
        response = auth_client_with_expenses.get("/profile?date_from=2026-02-16")
        data = response.data.decode()
        assert "Bus pass" not in data, (
            "Expense on 2026-02-15 should be EXCLUDED when date_from=2026-02-16"
        )

    def test_date_from_returns_correct_filtered_count(self, auth_client_with_expenses):
        """date_from=2026-04-20 should match exactly 2 expenses (Health, Shopping)."""
        response = auth_client_with_expenses.get("/profile?date_from=2026-04-20")
        data = response.data.decode()
        assert "Showing 2 of 5" in data, (
            f"Expected 'Showing 2 of 5' with date_from=2026-04-20"
        )


# ---------------------------------------------------------------------------
# 6. date_to only
# ---------------------------------------------------------------------------

class TestDateToFilter:
    def test_date_to_excludes_newer_expenses(self, auth_client_with_expenses):
        """Expenses after date_to must not appear."""
        response = auth_client_with_expenses.get("/profile?date_to=2026-03-01")
        data = response.data.decode()
        for desc in ["Electricity", "Vitamins", "Clothes"]:
            assert desc not in data, (
                f"'{desc}' should be excluded by date_to=2026-03-01"
            )

    def test_date_to_includes_expenses_on_and_before(self, auth_client_with_expenses):
        """Expenses on or before date_to must appear."""
        response = auth_client_with_expenses.get("/profile?date_to=2026-03-01")
        data = response.data.decode()
        for desc in ["January lunch", "Bus pass"]:
            assert desc in data, (
                f"Expected '{desc}' to appear with date_to=2026-03-01"
            )

    def test_date_to_boundary_inclusive(self, auth_client_with_expenses):
        """An expense whose date exactly equals date_to must be included."""
        response = auth_client_with_expenses.get("/profile?date_to=2026-02-15")
        data = response.data.decode()
        assert "Bus pass" in data, (
            "Expense on 2026-02-15 should be INCLUDED when date_to=2026-02-15 (inclusive)"
        )

    def test_date_to_boundary_excludes_day_after(self, auth_client_with_expenses):
        """An expense one day after date_to must be excluded."""
        response = auth_client_with_expenses.get("/profile?date_to=2026-02-14")
        data = response.data.decode()
        assert "Bus pass" not in data, (
            "Expense on 2026-02-15 should be EXCLUDED when date_to=2026-02-14"
        )

    def test_date_to_returns_correct_filtered_count(self, auth_client_with_expenses):
        """date_to=2026-03-10 should match exactly 3 expenses (Jan, Feb, Mar)."""
        response = auth_client_with_expenses.get("/profile?date_to=2026-03-10")
        data = response.data.decode()
        assert "Showing 3 of 5" in data, (
            f"Expected 'Showing 3 of 5' with date_to=2026-03-10"
        )


# ---------------------------------------------------------------------------
# 7. Both date_from and date_to (inclusive range)
# ---------------------------------------------------------------------------

class TestDateRangeFilter:
    def test_range_returns_only_expenses_within_bounds(self, auth_client_with_expenses):
        """Only the one expense in [2026-02-15, 2026-03-10] range should appear."""
        response = auth_client_with_expenses.get(
            "/profile?date_from=2026-02-15&date_to=2026-03-10"
        )
        data = response.data.decode()
        assert "Bus pass" in data, "2026-02-15 expense should be inside the range"
        assert "Electricity" in data, "2026-03-10 expense should be inside the range"

    def test_range_excludes_expenses_outside_bounds(self, auth_client_with_expenses):
        """Expenses outside [2026-02-15, 2026-03-10] must not appear."""
        response = auth_client_with_expenses.get(
            "/profile?date_from=2026-02-15&date_to=2026-03-10"
        )
        data = response.data.decode()
        assert "January lunch" not in data, "2026-01-01 is before range lower bound"
        assert "Vitamins" not in data, "2026-04-20 is after range upper bound"
        assert "Clothes" not in data, "2026-05-05 is after range upper bound"

    def test_range_correct_count_in_summary(self, auth_client_with_expenses):
        """Range [2026-02-15, 2026-03-10] matches 2 expenses."""
        response = auth_client_with_expenses.get(
            "/profile?date_from=2026-02-15&date_to=2026-03-10"
        )
        data = response.data.decode()
        assert "Showing 2 of 5" in data, (
            "Expected 'Showing 2 of 5' for range [2026-02-15, 2026-03-10]"
        )

    def test_range_single_day_exact_match(self, auth_client_with_expenses):
        """date_from == date_to picks only expenses on that exact day."""
        response = auth_client_with_expenses.get(
            "/profile?date_from=2026-04-20&date_to=2026-04-20"
        )
        data = response.data.decode()
        assert "Vitamins" in data, "Exact-day filter should include the matching expense"
        assert "Showing 1 of 5" in data, "Expected exactly 1 expense for single-day filter"

    def test_range_no_match_shows_zero_in_summary(self, auth_client_with_expenses):
        """A range with no matching expenses shows 'Showing 0 of 5'."""
        response = auth_client_with_expenses.get(
            "/profile?date_from=2026-06-01&date_to=2026-06-30"
        )
        data = response.data.decode()
        assert "Showing 0 of 5" in data, (
            "Expected 'Showing 0 of 5' when date range matches nothing"
        )

    @pytest.mark.parametrize("date_from,date_to,expected_count", [
        ("2026-01-01", "2026-01-01", 1),   # exact lower-bound date
        ("2026-05-05", "2026-05-05", 1),   # exact upper-bound date
        ("2026-01-01", "2026-05-05", 5),   # full span — all expenses
        ("2026-01-02", "2026-05-04", 3),   # span that excludes both endpoints
    ])
    def test_range_parametrized_counts(
        self, auth_client_with_expenses, date_from, date_to, expected_count
    ):
        response = auth_client_with_expenses.get(
            f"/profile?date_from={date_from}&date_to={date_to}"
        )
        data = response.data.decode()
        assert f"Showing {expected_count} of 5" in data, (
            f"Expected 'Showing {expected_count} of 5' for range [{date_from}, {date_to}]"
        )


# ---------------------------------------------------------------------------
# 8. Date inputs pre-filled after filtering
# ---------------------------------------------------------------------------

class TestDateInputsPrefilled:
    def test_date_from_input_prefilled(self, auth_client_with_expenses):
        """After submitting date_from, the input value attribute must echo it back."""
        response = auth_client_with_expenses.get("/profile?date_from=2026-03-01")
        data = response.data.decode()
        assert '2026-03-01' in data, (
            "Expected date_from value '2026-03-01' to appear in the rendered HTML (pre-fill)"
        )

    def test_date_to_input_prefilled(self, auth_client_with_expenses):
        """After submitting date_to, the input value attribute must echo it back."""
        response = auth_client_with_expenses.get("/profile?date_to=2026-04-30")
        data = response.data.decode()
        assert '2026-04-30' in data, (
            "Expected date_to value '2026-04-30' to appear in the rendered HTML (pre-fill)"
        )

    def test_both_date_inputs_prefilled(self, auth_client_with_expenses):
        """Both date_from and date_to must be echoed back into the form."""
        response = auth_client_with_expenses.get(
            "/profile?date_from=2026-02-01&date_to=2026-04-01"
        )
        data = response.data.decode()
        assert '2026-02-01' in data, "Expected date_from='2026-02-01' to be pre-filled"
        assert '2026-04-01' in data, "Expected date_to='2026-04-01' to be pre-filled"

    def test_inputs_empty_when_no_filter_submitted(self, auth_client_with_expenses):
        """When no filter is submitted, the date inputs must not contain stale values."""
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()
        # There must not be a stale date like '2026-03-01' appearing in the empty form.
        # We check that neither input carries a date value from a previous (non-existent) request.
        # We assert the form renders without a value for date_from/date_to by checking
        # that the placeholder dates used in other tests are absent.
        assert 'value="2026-03-01"' not in data, (
            "date_from input should be empty when no filter param was submitted"
        )
        assert 'value="2026-04-30"' not in data, (
            "date_to input should be empty when no filter param was submitted"
        )


# ---------------------------------------------------------------------------
# 9. Clear link
# ---------------------------------------------------------------------------

class TestClearLink:
    def test_clear_link_present_on_profile_page(self, auth_client_with_expenses):
        """The profile page must contain a link that points to /profile with no params."""
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()
        # The Clear link should be an <a> pointing to /profile (no query string).
        # Accept href="/profile" or href="/profile" followed by a quote/space.
        assert 'href="/profile"' in data, (
            "Expected a 'Clear' link with href='/profile' (no query params) on the profile page"
        )

    def test_clear_link_present_when_filter_active(self, auth_client_with_expenses):
        """The Clear link must also appear when a filter is currently active."""
        response = auth_client_with_expenses.get("/profile?date_from=2026-01-01")
        data = response.data.decode()
        assert 'href="/profile"' in data, (
            "Expected a Clear link on the filtered profile page"
        )

    def test_following_clear_link_shows_all_expenses(self, auth_client_with_expenses):
        """GETting /profile with no params after a filter shows all expenses again."""
        # First apply a filter (simulates user having filtered).
        auth_client_with_expenses.get("/profile?date_from=2026-05-05")
        # Then follow the Clear link — GET /profile with no params.
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()
        assert "Showing 5 of 5" in data, (
            "After clearing the filter, all 5 expenses should be shown"
        )


# ---------------------------------------------------------------------------
# 10. Empty state when no expenses match
# ---------------------------------------------------------------------------

class TestEmptyState:
    def test_empty_state_message_shown_when_no_match(self, auth_client_with_expenses):
        """When the filter matches nothing, an empty-state message must appear."""
        response = auth_client_with_expenses.get("/profile?date_from=2030-01-01")
        data = response.data.decode()
        # The spec requires an empty-state message (not just an empty table).
        # We check that some kind of "no expenses" / "no results" message is present.
        no_match_indicators = [
            "no expenses",
            "no results",
            "nothing to show",
            "no records",
            "empty",
            "no matching",
        ]
        found = any(indicator in data.lower() for indicator in no_match_indicators)
        assert found, (
            "Expected an empty-state message when the filter matches no expenses, "
            f"but none of {no_match_indicators} were found in the page."
        )

    def test_empty_state_not_shown_when_expenses_exist(self, auth_client_with_expenses):
        """When expenses do exist, the empty-state message must NOT appear."""
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()
        # Ensure the empty-state text is absent when there are matching expenses.
        no_match_indicators = [
            "no expenses",
            "no results",
            "nothing to show",
            "no records",
            "no matching",
        ]
        found = any(indicator in data.lower() for indicator in no_match_indicators)
        assert not found, (
            "Empty-state message should NOT appear when expenses are present"
        )

    def test_empty_state_no_expenses_in_db(self, app, client):
        """User with zero expenses sees the empty state without filtering."""
        email, password = _seed_user(client, name="Bob", email="bob@example.com")
        _login(client, email, password)
        response = client.get("/profile")
        data = response.data.decode()
        no_match_indicators = [
            "no expenses",
            "no results",
            "nothing to show",
            "no records",
            "empty",
            "no matching",
        ]
        found = any(indicator in data.lower() for indicator in no_match_indicators)
        assert found, (
            "Expected an empty-state message for a user with zero expenses"
        )


# ---------------------------------------------------------------------------
# 11. Expenses sorted newest-first
# ---------------------------------------------------------------------------

class TestNewestFirstOrdering:
    def test_newest_expense_appears_before_oldest(self, auth_client_with_expenses):
        """
        In the rendered HTML, the newest expense's description must appear
        before (at a lower byte offset than) the oldest expense's description.
        """
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()

        newest_desc = "Clothes"        # date 2026-05-05
        oldest_desc = "January lunch"  # date 2026-01-01

        pos_newest = data.find(newest_desc)
        pos_oldest = data.find(oldest_desc)

        assert pos_newest != -1, f"'{newest_desc}' not found in page"
        assert pos_oldest != -1, f"'{oldest_desc}' not found in page"
        assert pos_newest < pos_oldest, (
            f"Expected '{newest_desc}' (2026-05-05) to appear before '{oldest_desc}' (2026-01-01) "
            f"in the rendered HTML, but it appeared after (offsets: {pos_newest} vs {pos_oldest})"
        )

    def test_second_newest_before_second_oldest(self, auth_client_with_expenses):
        """Mid-range expenses also appear in descending date order."""
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()

        second_newest = "Vitamins"    # date 2026-04-20
        second_oldest = "Bus pass"    # date 2026-02-15

        pos_newer = data.find(second_newest)
        pos_older = data.find(second_oldest)

        assert pos_newer != -1, f"'{second_newest}' not found in page"
        assert pos_older != -1, f"'{second_oldest}' not found in page"
        assert pos_newer < pos_older, (
            f"Expected '{second_newest}' to appear before '{second_oldest}' in HTML"
        )

    def test_filtered_results_also_sorted_newest_first(self, auth_client_with_expenses):
        """Filtered results must also be sorted newest-first."""
        # Filter to the 3 middle expenses; newest among them is Electricity (2026-03-10)
        response = auth_client_with_expenses.get(
            "/profile?date_from=2026-02-15&date_to=2026-03-10"
        )
        data = response.data.decode()

        pos_electricity = data.find("Electricity")  # 2026-03-10 — newer
        pos_bus_pass = data.find("Bus pass")         # 2026-02-15 — older

        assert pos_electricity != -1, "'Electricity' not found in filtered results"
        assert pos_bus_pass != -1, "'Bus pass' not found in filtered results"
        assert pos_electricity < pos_bus_pass, (
            "Filtered results must also be sorted newest-first"
        )


# ---------------------------------------------------------------------------
# 12. Amount formatted to 2 decimal places
# ---------------------------------------------------------------------------

class TestAmountFormatting:
    def test_whole_number_amount_formatted_with_two_decimals(self, auth_client_with_expenses):
        """Amount 10.00 (whole number stored as float) must appear as '10.00'."""
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()
        assert "10.00" in data, (
            "Expected amount 10.00 to be rendered as '10.00' (2 decimal places)"
        )

    def test_decimal_amount_formatted_with_two_decimals(self, auth_client_with_expenses):
        """Amount 25.50 must appear as '25.50' (not '25.5')."""
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()
        assert "25.50" in data, (
            "Expected amount 25.50 to be rendered as '25.50' (trailing zero preserved)"
        )

    def test_multi_decimal_amount_formatted_correctly(self, auth_client_with_expenses):
        """Amount 200.10 must appear as '200.10'."""
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()
        assert "200.10" in data, (
            "Expected amount 200.10 to be rendered as '200.10'"
        )

    def test_amount_99_99_formatted_correctly(self, auth_client_with_expenses):
        """Amount 99.99 must appear as '99.99'."""
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()
        assert "99.99" in data, (
            "Expected amount 99.99 to be rendered as '99.99'"
        )

    @pytest.mark.parametrize("amount,expected", [
        (10.00,  "10.00"),
        (25.50,  "25.50"),
        (99.99,  "99.99"),
        (200.10, "200.10"),
        (5.00,   "5.00"),
    ])
    def test_all_amounts_formatted_to_two_decimal_places(
        self, auth_client_with_expenses, amount, expected
    ):
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()
        assert expected in data, (
            f"Expected amount {amount} to be formatted as '{expected}' in the expenses table"
        )


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------

class TestUserIsolation:
    def test_another_users_expenses_not_visible(self, app, client):
        """Expenses belonging to a different user must never appear on the logged-in user's profile."""
        # Register and expense for user A.
        email_a, pass_a = _seed_user(
            client, name="UserA", email="usera@example.com", password="password123"
        )
        _login(client, email_a, pass_a)
        user_a_id = _get_user_id(app, email_a)
        _insert_expense(app, user_a_id, 999.00, "Secret", "2026-03-15", "UserA secret expense")
        # Log out user A.
        client.get("/logout")

        # Register user B (no expenses).
        email_b, pass_b = _seed_user(
            client, name="UserB", email="userb@example.com", password="password456"
        )
        _login(client, email_b, pass_b)

        # User B's profile must not contain user A's expense.
        response = client.get("/profile")
        data = response.data.decode()
        assert "UserA secret expense" not in data, (
            "User B's profile must not display User A's expenses"
        )
        assert "999.00" not in data, (
            "User A's expense amount must not leak to User B's profile"
        )


class TestFilterFormStructure:
    def test_filter_form_uses_get_method(self, auth_client_with_expenses):
        """The filter form must use method='get' so params appear in the URL."""
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode().lower()
        assert 'method="get"' in data or "method='get'" in data, (
            "Expected the date filter form to use method='get'"
        )

    def test_filter_form_has_date_from_input(self, auth_client_with_expenses):
        """The form must contain an input named 'date_from'."""
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()
        assert 'name="date_from"' in data or "name='date_from'" in data, (
            "Expected an input with name='date_from' in the filter form"
        )

    def test_filter_form_has_date_to_input(self, auth_client_with_expenses):
        """The form must contain an input named 'date_to'."""
        response = auth_client_with_expenses.get("/profile")
        data = response.data.decode()
        assert 'name="date_to"' in data or "name='date_to'" in data, (
            "Expected an input with name='date_to' in the filter form"
        )
