# Supabase setup (manual, once)

Design: `docs/decisions/0005-supabase-schema-and-ci.md`. Nothing here needs a login or token on your machine.

1. Create a Supabase project. Use a name with no personal info.
2. Authentication: enable only the email magic link. Turn **sign-ups off**.
3. Create your own user once (Authentication > Users).
4. SQL editor: paste each file in `supabase/migrations/` in filename order and run it. Never edit a file that is already applied; add a new migration instead.
5. Authentication > URL configuration: add the GitHub Pages URL to the redirect URLs.
6. Never share or commit the `service_role` key or the database password. Only the project URL and the anon/publishable key may go in the repo (`app/frontend/client/config.js`).
7. Verify by hand: a signed-out request with the anon key to `valuations`, `customers` and `notes` returns no rows.

CI runs the SQL and secret checks (`tests/test_supabase.py`) without any database.
