# Supabase setup (manual, once)

Design: `docs/decisions/0005-supabase-schema-and-ci.md` and `docs/decisions/0006-multi-user-google-sign-in-and-watchlists.md`. Nothing here needs a login or token on your machine. `<project-ref>` below is a placeholder for your project's reference id: never write the real one in the repo.

## Project and database

1. Create a Supabase project. Use a name with no personal info.
2. SQL editor: paste each file in `supabase/migrations/` in filename order and run it. Never edit a file that is already applied; add a new migration instead.
3. Verify by hand: a signed-out request with the anon key to `valuations`, `customers` and `notes` returns no rows.
4. Authentication > Sign In / Providers: turn "Allow new users to sign up" **off**, so sign-ups stay off. Only invited people can sign in.
5. Never share or commit the `service_role` key, the database password or any OAuth client secret. Only the project URL and the anon/publishable key may go in the repo (`app/frontend/client/config.js`).

## Google sign-in

6. Google Cloud console: create a project, then Google Auth Platform > OAuth consent screen (Branding/Audience). User type **External**. Fill in the app name and support address. Add the scopes `openid`, `email` and `profile`. Set publishing status to **In production** (publish to production, otherwise sign-in stops working for users after testing mode expires).
7. Google Cloud > Credentials > Create credentials > OAuth client ID, application type **Web application**. Add this as an Authorized redirect URI:
   `https://<project-ref>.supabase.co/auth/v1/callback`
   Leave Authorized JavaScript origins empty.
8. Supabase > Authentication > Providers > Google: enable it and paste the Client ID and the **Client Secret** there. The secret goes only into this Supabase page, never into the repo, an issue, a commit or a chat. Keep **Skip nonce check** off.

## Invite only

9. Invite a person: Authentication > Users > Add user > Create new user, with **Auto Confirm User** on. Use the exact Google address the person signs in with. No `+` aliases and no other aliases: Google returns the real address, so an alias will not match and the person is refused with "Signups not allowed".
10. Authentication > URL Configuration: set **Site URL** to `https://erikandreassonbusiness.github.io/BrokerAI/` and add `https://erikandreassonbusiness.github.io/BrokerAI/**` to **Redirect URLs** (the `**` covers `stock.html?ticker=...`; an unlisted redirect silently falls back to the Site URL).
   The built-in email service sends only a few emails per hour and only to members of your Supabase organization's team. If email links stop arriving, check Authentication > Rate Limits, or set up your own SMTP under Authentication > Emails > SMTP Settings.

## M4 linking test (before relying on Google)

11. Check that Google sign-in links to the invited user instead of creating a new one. In a private browser window open
    `https://<project-ref>.supabase.co/auth/v1/authorize?provider=google&redirect_to=<site URL>`
    (use the Site URL from step 10) and sign in with the invited Google address from step 9 (created with Auto Confirm). Check all three:
    - Authentication > Users shows no new user, and the existing user now has the Google identity linked.
    - The user id of that user is unchanged.
    - An uninvited Google account is refused (no user is created).

## Own account and fallback

12. Check your own account: sign in with Google using the address of your own existing user, confirm your own user id is unchanged, and confirm your valuations, customers and notes still show.
13. If a check in step 11 or 12 fails, stop and fall back to ADR 0006 option B; do not invite anyone else yet.

## Last step

14. Disable the email provider (Authentication > Providers > Email) only after your own user works with Google and the home page works with Google. Until then the email magic link stays as your way back in.

CI runs the SQL and secret checks (`tests/test_supabase.py`) and this README's content checks without any database.
