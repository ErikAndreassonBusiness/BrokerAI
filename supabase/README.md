# Supabase setup (manual, once)

Design: `docs/decisions/0005-supabase-schema-and-ci.md`. Nothing here needs a login or token on your machine.

1. Create a Supabase project. Use a name with no personal info.
2. Authentication: enable only the email magic link. Turn **sign-ups off**.
3. Create your own user once (Authentication > Users > Add user > Create new user, with "Auto Confirm User" on). Use the exact email you will type on the site: with sign-ups off, any other address gets "Signups not allowed for otp".
4. SQL editor: paste each file in `supabase/migrations/` in filename order and run it. Never edit a file that is already applied; add a new migration instead.
5. Authentication > URL Configuration: set **Site URL** to `https://erikandreassonbusiness.github.io/BrokerAI/` and add `https://erikandreassonbusiness.github.io/BrokerAI/**` to **Redirect URLs** (the `**` covers `stock.html?ticker=...`; an unlisted redirect silently falls back to the Site URL).
   The built-in email service sends only a few emails per hour and only to members of your Supabase organization's team. If links stop arriving, check Authentication > Rate Limits, or set up your own SMTP under Authentication > Emails > SMTP Settings.
6. Never share or commit the `service_role` key or the database password. Only the project URL and the anon/publishable key may go in the repo (`app/frontend/client/config.js`).
7. Verify by hand: a signed-out request with the anon key to `valuations`, `customers` and `notes` returns no rows.

CI runs the SQL and secret checks (`tests/test_supabase.py`) without any database.
