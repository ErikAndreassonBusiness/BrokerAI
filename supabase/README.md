# Supabase setup (manual, once)

Design: `docs/decisions/0005-supabase-schema-and-ci.md`, ADR 0006 (its sign-in part is superseded) and `docs/decisions/0008-email-password-sign-in.md`. Nothing here needs a login or token on your machine. Never write a real project reference id, an email address or a password in the repo.

## Project and database

1. Create a Supabase project. Use a name with no personal info.
2. SQL editor: paste each file in `supabase/migrations/` in filename order and run it. Never edit a file that is already applied; add a new migration instead.
3. Verify by hand: a signed-out request with the anon key to `valuations`, `customers` and `notes` returns no rows.
4. Authentication > Sign In / Providers: turn the User Signups toggle ("Allow new users to sign up", at the top of the page, not inside the Email provider) **off**, so sign-ups stay off. Keep the Email provider on. Only invited people can sign in.
5. Never share or commit the `service_role` key, the database password or any SMTP credential. Only the project URL and the anon/publishable key may go in the repo (`app/frontend/client/config.js`).

## Password settings

6. Authentication > Sign In / Providers > Email: set Minimum password length to **10**. No character-class rule.
7. Same page: set **Secure password change** to **off** (on, it can require a reauthentication email for a password change, which would break the change-password and first-login flow; verify in the dashboard).
8. Leaked-password protection may be a paid-plan feature: check the dashboard. If it is missing, the 10-character minimum is the guard.

## Email

9. The built-in email service sends only a few emails per hour and only to team members of your Supabase organization, so reset mail to invitees needs your own SMTP.
10. Your choice is Gmail: use a dedicated Gmail account (not your main inbox) with 2-step verification on, and create an app password for it.
11. Authentication > Emails > SMTP Settings: enable custom SMTP with host `smtp.gmail.com`, port `587`, username = that Gmail address, password = the app password, Sender email = the same Gmail address, Sender name = BrokerAI. The app password goes only into this Supabase SMTP page, never in the repo, an issue, a commit or a chat. Revoke it if in doubt.
12. Alternative: a transactional provider (Brevo, Resend, similar) with a verified sender or a domain you own. Check its limits and sender rules first.
13. Authentication > Rate Limits: once SMTP is on, check the email rate limit (emails sent per hour) and keep it low; a few users need about 5 per hour.
14. Authentication > Emails > Templates: keep the default Reset password template (it honours the redirect).
15. Authentication > URL Configuration: set **Site URL** to `https://erikandreassonbusiness.github.io/BrokerAI/` and add `https://erikandreassonbusiness.github.io/BrokerAI/**` to **Redirect URLs** (an unlisted redirect silently falls back to the Site URL).

## Your own account

Keep the existing user (never delete and recreate it) so its id and data stay. Do these in order, and only after #81 and #93 are merged and deployed:

16. After steps 1-15, sign in once with the email magic link; the site asks you to choose a password, so set your own password while the magic link still works.
17. Sign out, sign in with the password in a private window, and check the user id is unchanged and your valuations, customers and notes still show.
18. Test the forgot-password link for yourself (the built-in mailer reaches you as team member); test it again once SMTP is on, with a non-team address.
19. Only then #85 (remove the magic link).
20. Fallback if step 16 fails: Authentication > Users > your user > Send password recovery, so you are not locked out.

## Invite people

Needs #81 live (the first-login prompt that asks for their own password).

21. Do not invite anyone until a reset email has reached a non-team address (step 18).
22. Authentication > Users > Add user > Create new user, with the person's email and **Auto Confirm User** on.
23. Use a random temporary password of 16 or more characters (password manager) and give the temporary password to the person privately: not by email, not in an issue, a commit or any file. Supabase hashes it; you cannot read it back.
24. The site asks the person to choose their own password right after the first sign-in. Tell them to do it at once.

CI runs the SQL and secret checks (`tests/test_supabase.py`) and this README's content checks without any database.
