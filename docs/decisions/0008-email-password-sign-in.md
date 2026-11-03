# 0008 - Sign in with email and password (replaces Google sign-in)

Status: accepted. Date: 2026-11-03. Supersedes the sign-in part of ADR 0006 (Google, OAuth, linking test,
Google setup steps). Everything else in 0006 (invite only, `watchlist`, landing page, home page) and ADR
0005/0007 stands. Issues: #92 (this ADR and README), #93 (forgot password), #81 and #85 change scope.

## Context
Erik changed the sign-in decision: email + password instead of Google. Nothing was set up in Google, so
there is nothing to clean up there. Fixed by Erik: Supabase's email provider stays ON; the magic link
disappears from the site; sign-ups stay off (invite only); Erik creates each user in the dashboard with
a temporary password; users can change their password and reset a forgotten one themselves.

Facts: the live project has the email provider on and sign-ups disabled. `auth.js` today uses
`signInWithOtp`. The vendored supabase-js defaults to `flowType: "implicit"` and `detectSessionInUrl: true`
(checked in `client/vendor/supabase.js`), and emits `PASSWORD_RECOVERY` from `onAuthStateChange` when a
recovery link is opened. The built-in Supabase mailer reaches only Erik's Supabase team (and is heavily
rate limited), so reset emails to invitees need custom SMTP. Redirect URLs already allow `/BrokerAI/**`.

## Options
A. **Password + self-service reset (chosen).** No Google, no OAuth linking question, one provider.
B. Password only, Erik resets passwords by hand in the dashboard: no SMTP, but every forgotten password
   is a chore for Erik and a wait for the user. Rejected by Erik.
C. Keep the magic link next to the password: two sign-in paths, still needs SMTP. Rejected by Erik.

## Decision
- **Provider:** Supabase email provider, `signInWithPassword({email, password})`. Sign-ups stay off. The
  "unknown address" and "wrong password" cases both give Supabase's generic `invalid_credentials`, shown
  as "Wrong email or password." (no hint which). `signInWithOtp` is removed from `auth.js`; the API
  still exists server-side but with sign-ups off it only mails a user their own address.
- **Invite:** unchanged mechanism (ADR 0006 option A) but simpler: Authentication > Users > Add user >
  Create new user, email + temporary password, **Auto Confirm User on**. No linking question remains, so
  ADR 0006's "unverified linking, fall back to option B" risk is gone. Erik makes the temporary password
  random (password manager, 16+ characters) and gives it to the person privately (not by email and not in an
  issue, a commit or any file). It is hashed in Supabase; Erik cannot read it back.
- **Knowing a password is temporary, no dashboard step for Erik:** the site checks `user_metadata`. If
  the flag `own_password` is **absent**, the user is shown "Choose your own password" right after sign-in
  and nothing else until done. The form calls `updateUser({ password, data: { own_password: true } })`
  in one call, so password and flag cannot get out of step. Why inverted instead of a
  `must_change_password` flag Erik sets: the dashboard's create-user form has no metadata field, so
  Erik would need a second edit per invite and could forget it; "absent means not yet chosen" needs
  nothing from him, and also covers his own account (below). Why `user_metadata` and not `app_metadata`:
  only `user_metadata` can be written by the signed-in user, which the site needs. A user could set the
  flag without changing the password; that is fine because it is a nudge, not a security control.
  Enforcement is client-side only (the temporary password stays valid until changed), so tell people to
  change it at once.
- **Change password:** a "Change password" control for signed-in users (new password twice, same
  `updateUser` call). Errors shown: `weak_password` (too short), `same_password` (must differ).
- **Forgot password (#93):** "Forgot password?" on the sign-in form asks for the email and calls
  `resetPasswordForEmail(email, { redirectTo: current page })`. The answer is always the neutral "If this
  address has an account, an email is on its way" (Supabase returns success for unknown addresses too, so
  no account enumeration). The email link signs the user in with a recovery session and fires
  `PASSWORD_RECOVERY`; `auth.js` shows the "Set new password" form (same form and call as above). The
  `onAuthStateChange` listener must be registered right after `createClient`, before any `await`, or the
  event from the link in the URL is missed. Test in JS: the event shows the form; a normal sign-in does not.
- **PKCE or implicit:** keep the library default, **implicit**, no `flowType` option. Reason: implicit
  recovery links work when the email is opened on another device or browser than the one that asked
  (typical: ask on desktop, open the mail on the phone); PKCE needs the code verifier saved in the
  asking browser's localStorage and fails otherwise, and PKCE gives no extra protection here (no
  third-party redirect, tokens are in our own origin). Cost: the tokens are briefly in the URL hash, which
  supabase-js clears on load; accepted for a few users. Revisit if a CSP or a server ever enters.
  (ADR 0006 chose PKCE only for the OAuth flow, which is gone.)
- **Supabase settings (Erik, dashboard, in README):**
  1. Authentication > Sign In / Providers > Email: provider on, "Allow new users to sign up" off,
     **Minimum password length 10**, no character-class rule (length matters more; invitees use a
     password manager). **Secure password change OFF**: it forces a reauthentication email for every
     change, which breaks the "change password" and first-login flow. Trade-off accepted: someone with a
     stolen live session can change the password.
  2. **Leaked-password protection** (checks against known breaches) is, as far as I know, a paid-plan
     feature; **unsure, check the dashboard**. If it is not available, the 10-character minimum and
     "use a password manager" are the only guards.
  3. Authentication > Emails > Templates > "Reset password": keep the default (it uses the confirmation
     URL, which honours `redirectTo`). Redirect URLs allowlist stays as is (`.../BrokerAI/**`); an
     unlisted redirect silently falls back to the Site URL.
  4. Authentication > Rate Limits: leave defaults for sign-in attempts per IP; once custom SMTP is on,
     check the "emails sent per hour" limit and keep it low (a few users need about 5/hour); a low
     limit also caps abuse of the reset form. Exact default numbers: verify in the dashboard.
- **Custom SMTP (needed for reset mail to invitees) - Erik picks; entered only in the Supabase SMTP page:**
  - *Gmail SMTP with an app password:* no domain needed, about 500 recipients a day, ample. Needs 2-step
    verification on that Gmail account. Sender is that Gmail address (invitees see it). Mail is signed by
    Google, so delivery is good. The app password gives access to that mailbox, so prefer a **dedicated
    sender account** over Erik's main inbox, and revoke the app password if in doubt.
  - *Transactional provider (Brevo, Resend, similar):* free tiers of roughly 100-300 mails a day. Needs
    a verified sender or a **domain Erik owns** with DNS records (SPF/DKIM); sending "from a Gmail
    address" through them tends to fail Google's DMARC policy and land in spam. Better long-run, more
    setup. Limits and sender rules: verify with the provider before choosing.
  Until SMTP works, reset mail reaches only Supabase team members, i.e. Erik himself. Do not invite
  anyone before a reset mail has reached a non-team address.
- **Erik's own account (keeps its id; never delete and recreate it):** safe order, magic link still the
  fallback until the last step:
  1. Set the Supabase settings above (provider stays on). Merge the password code; the magic link is
     removed only later, by #85.
  2. While still signed in from the magic link, the site shows "Choose your own password" (his flag is
     absent); he sets his password.
  3. Sign out, sign in with the password in a private window; confirm the user id and his valuations,
     customers and notes are unchanged.
  4. Test "Forgot password" for himself (the built-in mailer reaches him as team member; also test once
     SMTP is on, with a non-team address).
  5. Only then merge #85 (remove the magic link). If step 2 fails, the dashboard's "Send password
     recovery" on his user is the way in, so he is not locked out.
- **Threats:** *Brute force:* Supabase rate-limits sign-in attempts per IP (verify values in
  Authentication > Rate Limits), plus 10-character minimum; no CAPTCHA now (adding Turnstile would put a
  site key in the frontend; add only if abuse shows). *Temporary password:* one person, shared privately,
  replaced at first sign-in. *Secrets:* no password, SMTP credential or app password in the repo, an
  issue, a log or a test (tests use obvious dummy values). Existing CI scans for `service_role` and keys
  still apply. *Reset mail:* link is one-time and short-lived; anyone with the invitee's mailbox owns
  the account, as with any reset.
- **Unchanged:** RLS/migrations (0005), `watchlist` and `stock_requests` tables (0006/0007), session
  handling in localStorage, `.github/`, `AGENT.md`, `validate.py`, `todo.py`, `reports.yml`.

## Consequences
- ADR 0006 remains valid except its Google provider, OAuth/PKCE, M4 linking test and the Google parts of
  the setup checklist; its "keep email on until Google works" risk is void. ADR 0002's magic link is
  also replaced by this decision.
- `supabase/README.md`: the Google and linking-test sections are replaced by Email settings, SMTP,
  invite with a temporary password, and the own-account order above. The CI content checks for the
  README (`tests/test_supabase.py`) must be updated with it.
- A forgotten-password flow means reliance on mail delivery; if SMTP breaks, Erik resets by hand in the
  dashboard.
- Follow-up issues: #92 (ADR + README rewrite; settings and SMTP as Erik's manual steps, M-list in
  #77 updated: drop Google steps); #81 retitled to `auth.js` password sign-in, change password and the
  `own_password` gate, tests rewritten; #93 forgot password and recovery form; #82 landing page gets an
  email + password form and "Forgot password?" link; #85 removes the magic link last. Order: #92, #81,
  #93, then Erik's own-account steps 2-4, then #85.

## Risks for planning
- Locking Erik out: follow the own-account order; remove the magic link (#85) only after step 4.
- Reset mail untested with a non-team address gives false confidence; make that a gate before the first
  invitee.
- Recovery event missed if the listener is registered late (see above): needs a test.
- Public repo: no addresses, temporary passwords, SMTP credentials or project ref in files or issues.

## Open questions for Erik
1. Which SMTP route: Gmail app password (dedicated sender account) or a provider with a domain?
2. Is leaked-password protection available on your plan? If not, is the 10-character minimum enough?
