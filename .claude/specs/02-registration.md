# Spec: Registration

## Overview

This step makes the existing sign-up form work. `templates/register.html` already posts `name`, `email` and `password` to `/register`, but `app.py` only has a GET handler, so submitting the form returns 405 Method Not Allowed. This step adds POST handling to the `register()` view. It validates the fields, rejects duplicate emails, hashes the password with werkzeug and inserts a row into the `users` table from Step 1. It then redirects to `/login` with a success flash message. Registration comes first in the auth flow because Step 3 (Login and Logout) needs real accounts to sign in to. This step does **not** create a session or log the user in. That is Step 3.

## Depends on

- **Step 1 — Database setup**: `get_db()`, `init_db()` and the `users` table in `database/db.py`. The table has these columns: `id INTEGER PK AUTOINCREMENT`, `name TEXT NOT NULL`, `email TEXT NOT NULL UNIQUE`, `password_hash TEXT NOT NULL`, `created_at TEXT DEFAULT datetime('now')`.

## Routes

- `GET /register` — shows the registration form (already exists; keep it working) — public
- `POST /register` — validates the input, creates the user and redirects to `/login` with a success flash — public

Both methods go through the existing `register()` view, changed to `@app.route("/register", methods=["GET", "POST"])`. No other routes change.

### POST /register behaviour

1. Read `name`, `email` and `password` from `request.form`. Strip whitespace from `name` and `email`, and lowercase `email`.
2. Validate the fields in this order. On the first failure, re-render `register.html` with HTTP 400, an `error` message, and the submitted `name`/`email` filled back in (never the password):
   - All three fields present and non-empty → `"All fields are required."`
   - Email contains `@` and a `.` after the `@` → `"Please enter a valid email address."`
   - Password is at least 8 characters → `"Password must be at least 8 characters."`
3. Check for a duplicate with `SELECT id FROM users WHERE email = ?`. If a row exists, re-render with the error `"An account with that email already exists."` (HTTP 400). Also catch `sqlite3.IntegrityError` on insert, as a backstop against race conditions, and show the same error.
4. Insert with `INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)`, using `generate_password_hash(password)`, then commit.
5. Always close the DB connection, using `try/finally`.
6. Call `flash("Account created. Please sign in.", "success")` and `redirect(url_for("login"))`.

## Database changes

No database changes. The `users` table in `database/db.py` already has every column this step needs, and email uniqueness is already enforced by the `UNIQUE` constraint.

## Templates

**Create:** none.

**Modify:**
- `templates/register.html` — refill the `name` and `email` inputs from the template context after a failed submit (`value="{{ name or '' }}"`, `value="{{ email or '' }}"`). Keep the existing `{% if error %}` block.
- `templates/login.html` — render flashed messages inside `.auth-card`, above the form, using `get_flashed_messages(with_categories=true)`. Messages in the `success` category use a new `.auth-success` class.

## Files to change

- `app.py` — import `flash`; add POST handling to `register()` as described above. The `generate_password_hash` import is already there.
- `templates/register.html` — refill the form fields after an error.
- `templates/login.html` — show flash messages.
- `static/css/style.css` — add a `.auth-success` rule that mirrors `.auth-error`. Use `var(--accent)` and `var(--accent-light)` for its colours.

## Files to create

None.

## New dependencies

No new dependencies. Flask 3.1.3 and werkzeug 3.1.6 are already in `requirements.txt`.

## Rules for implementation

- No SQLAlchemy or ORMs. Use raw `sqlite3` through `get_db()`.
- Parameterised queries only (`?` placeholders). Never build SQL with string formatting.
- Hash passwords with werkzeug (`generate_password_hash`). Never store or log a plaintext password.
- Use CSS variables and never hardcode hex values. The new `.auth-success` rule must only use existing `:root` variables.
- All templates extend `base.html`.
- Do not set `session` values or log the user in. That is Step 3.
- Keep validation on the server side. The HTML `required` attributes are only a convenience.
- Normalise email (strip and lowercase) before both the duplicate check and the insert.
- Leave the placeholder routes (`/logout`, `/profile`, `/expenses/...`) untouched.

## Definition of done

- [ ] `GET /register` still shows the form with no error message.
- [ ] Submitting valid details (e.g. `Test User` / `test@example.com` / `password123`) redirects to `/login`, which shows "Account created. Please sign in."
- [ ] After that, `SELECT * FROM users WHERE email='test@example.com'` returns one row, and `password_hash` is a werkzeug hash (e.g. starts with `scrypt:`), not the plaintext password.
- [ ] Registering again with the same email (including different case, e.g. `TEST@example.com`) shows "An account with that email already exists." and adds no new row.
- [ ] Registering with `demo@spendly.com` (the seeded user) shows the duplicate-email error.
- [ ] Submitting a password shorter than 8 characters shows "Password must be at least 8 characters."
- [ ] Submitting an email without a valid `@` and domain (sent directly, bypassing browser validation) shows "Please enter a valid email address."
- [ ] Submitting blank or whitespace-only fields (sent directly) shows "All fields are required."
- [ ] After any validation error, the name and email fields are refilled and the password field is empty.
- [ ] The success message on `/login` is styled with the accent colours, and `style.css` gains no new hex values.
- [ ] The app starts with `python app.py` without errors, and all other existing pages (`/`, `/login`, `/terms`, `/privacy`) still load.
