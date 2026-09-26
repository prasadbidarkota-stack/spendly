# Spec: Login and Logout

## Overview

This step turns the sign-in form and the `/logout` placeholder into working session-based authentication. `templates/login.html` already posts `email` and `password` to `/login`, but `app.py` only has a GET handler, so submitting the form returns 405 Method Not Allowed. `/logout` is still a placeholder string ("Logout — coming in Step 3"). This step adds POST handling to `login()`. It looks the user up by normalised email, checks the password with werkzeug's `check_password_hash`, and stores the user in Flask's signed `session` cookie. The step also implements `/logout` to clear the session, and makes the navbar in `base.html` aware of the session. Login and logout come straight after registration because every later step (Profile, adding, editing and deleting expenses) needs to know who the current user is.

## Depends on

- **Step 1 — Database setup**: `get_db()` and the `users` table (`id`, `name`, `email UNIQUE`, `password_hash`, `created_at`) in `database/db.py`, plus the seeded `demo@spendly.com` / `demo123` user.
- **Step 2 — Registration**: users are stored with lowercased emails and werkzeug password hashes, and `/login` already renders flashed messages (including the `.auth-success` style).

## Routes

- `GET /login` — shows the sign-in form. If the user is already logged in, redirects to `/profile` instead — public
- `POST /login` — checks credentials, starts a session and redirects to `/profile` — public
- `GET /logout` — clears the session, flashes "You have been signed out." and redirects to `/login` — public (safe to call when already logged out)

`login()` changes to `@app.route("/login", methods=["GET", "POST"])`. The existing `logout()` placeholder is replaced; its route stays `GET /logout`.

`GET /register` also gains an already-logged-in redirect to `/profile`, so a signed-in user doesn't see the sign-up form. Its POST behaviour is unchanged.

### POST /login behaviour

1. Read `email` and `password` from `request.form`. Strip and lowercase `email`. Don't strip `password`.
2. If either field is empty, re-render `login.html` with HTTP 400, the error `"Email and password are required."`, and the submitted email filled back in.
3. Run `SELECT id, name, password_hash FROM users WHERE email = ?`. Close the connection with `try/finally`.
4. If no row is found, or `check_password_hash(row["password_hash"], password)` is false, re-render `login.html` with HTTP 401, the error `"Invalid email or password."`, and the email filled back in. Use this same message for both cases, so the page never reveals whether an email is registered.
5. On success, call `session.clear()`, then set `session["user_id"] = row["id"]` and `session["user_name"] = row["name"]`, and `redirect(url_for("profile"))`.

### GET /logout behaviour

1. Call `session.clear()`.
2. Call `flash("You have been signed out.", "success")`.
3. Call `redirect(url_for("login"))`.

## Database changes

No database changes. The `users` table already has every column needed, and the lookup uses the existing `UNIQUE` index on `email`.

## Templates

**Create:** none.

**Modify:**
- `templates/login.html` — refill the email input after a failed submit (`value="{{ email or '' }}"`). Keep the existing flash-message loop and the `{% if error %}` block. The password field always renders empty.
- `templates/base.html` — make the navbar session-aware. When `session.user_id` is set, show the user's name (`session.user_name`, in a `.nav-user` span) and a "Sign out" link to `url_for('logout')`. Otherwise show the current "Sign in" and "Get started" links.

## Files to change

- `app.py` — add POST handling to `login()`, add the already-logged-in redirects to `GET /login` and `GET /register`, and replace the `logout()` placeholder. Use the `session` and `check_password_hash` imports that are already there.
- `templates/login.html` — refill the email field after an error.
- `templates/base.html` — make the navbar session-aware.
- `static/css/style.css` — add a `.nav-user` rule (for example `color: var(--ink-muted)`) that uses only existing `:root` variables. It must stay visible on mobile, like `.nav-cta`.

## Files to create

- `tests/test_login.py` — pytest tests for this step. Reuse the temporary-database fixture pattern from `tests/test_register.py`.

## New dependencies

No new dependencies. Flask's built-in `session` and werkzeug's `check_password_hash` cover everything this step needs.

## Rules for implementation

- No SQLAlchemy or ORMs. Use raw `sqlite3` through `get_db()`.
- Parameterised queries only (`?` placeholders). Never build SQL with string formatting.
- Check passwords only with werkzeug's `check_password_hash`. Never compare, store or log plaintext passwords.
- Use CSS variables and never hardcode hex values.
- All templates extend `base.html`.
- Use one generic error message for both an unknown email and a wrong password.
- Call `session.clear()` before setting the new session keys on login, so no state from a previous session carries over.
- Store only `user_id` and `user_name` in the session. Never store the email or the password hash.
- Don't protect `/profile` or the expense routes yet, and don't build a `login_required` decorator. That belongs to Step 4 and later steps.
- Leave the `/profile` and `/expenses/...` placeholder routes untouched.
- Don't change registration's POST behaviour. Its existing tests must still pass.

## Definition of done

- [ ] `GET /login` shows the sign-in form with no error message when logged out.
- [ ] Signing in as `demo@spendly.com` / `demo123` redirects to `/profile`. The navbar then shows "Demo User" and a "Sign out" link, and the "Sign in" and "Get started" links are gone.
- [ ] Signing in with a mixed-case email with surrounding spaces (e.g. `  Demo@Spendly.com `) also succeeds.
- [ ] A user who has just registered through `/register` can sign in with their new credentials.
- [ ] A wrong password shows "Invalid email or password." (HTTP 401), keeps the email filled in, and leaves the password field empty.
- [ ] An unregistered email shows exactly the same "Invalid email or password." message.
- [ ] Submitting a blank email or password (sent directly, bypassing browser validation) shows "Email and password are required." (HTTP 400).
- [ ] While logged in, visiting `/login` or `/register` redirects to `/profile`.
- [ ] Clicking "Sign out" redirects to `/login` and shows "You have been signed out." After that, the navbar shows "Sign in" and "Get started" again.
- [ ] Visiting `/logout` while already logged out still redirects to `/login` without an error.
- [ ] After signing out, visiting `/login` shows the form again instead of redirecting.
- [ ] `style.css` gains no new hex values.
- [ ] `pytest` passes, including the existing `tests/test_register.py` and the new `tests/test_login.py`.
- [ ] The app starts with `python app.py` without errors, and `/`, `/register`, `/terms` and `/privacy` still load.
