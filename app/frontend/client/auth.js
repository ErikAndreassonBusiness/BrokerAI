// Sign-in with Supabase magic links. Uses the vendored client only; no fetch of its own.
// Exposes window.BrokerAuth = { init, signIn, signOut }; pages call BrokerAuth.init() once.
(function () {
  const DEFAULT_TIMEOUT_MS = 5000;
  let client = null;

  function setControl(html) {
    const el = document.getElementById("auth");
    if (!el) return;
    el.innerHTML = html;
    const form = el.querySelector && el.querySelector("form");
    if (form) {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        signIn(form.elements.email.value);
      });
    }
    const out = el.querySelector && el.querySelector("button[data-signout]");
    if (out) out.addEventListener("click", signOut);
  }

  function setSections(html) {
    document.querySelectorAll("[data-user-section]").forEach((el) => {
      el.innerHTML = html;
    });
  }

  function signedOutHtml(note) {
    return (
      '<form class="auth-form">' +
      '<input type="email" name="email" placeholder="Email" aria-label="Email" required />' +
      '<button type="submit">Sign in</button>' +
      (note ? '<span class="auth-note">' + note + "</span>" : "") +
      "</form>"
    );
  }

  function signedInHtml(note) {
    return (
      '<button type="button" data-signout>Sign out</button>' +
      (note ? '<span class="auth-note">' + note + "</span>" : "")
    );
  }

  function showSignedOut(note) {
    setControl(signedOutHtml(note));
    setSections('<p class="muted">Sign in to see this.</p>');
  }

  function showUnavailable() {
    setControl("");
    setSections('<p class="muted">Unavailable right now.</p>');
  }

  function timeoutAfter(ms) {
    let id;
    const promise = new Promise((_, reject) => {
      id = setTimeout(() => reject(new Error("timeout")), ms);
    });
    return { promise, cancel: () => clearTimeout(id) };
  }

  async function init({ timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
    const timer = timeoutAfter(timeoutMs);
    try {
      const cfg = window.BROKERAI_CONFIG;
      if (!cfg || !cfg.url || !cfg.anonKey || !window.supabase) throw new Error("not configured");
      client = window.supabase.createClient(cfg.url, cfg.anonKey);
      const { data, error } = await Promise.race([client.auth.getSession(), timer.promise]);
      if (error) throw error;
      if (data && data.session) {
        setControl(signedInHtml());
        setSections("");
        return "signed-in";
      }
      showSignedOut();
      return "signed-out";
    } catch (e) {
      client = null;
      showUnavailable();
      return "unavailable";
    } finally {
      timer.cancel();
    }
  }

  const SIGN_IN_ERRORS = {
    otp_disabled: "No account for this email.",
    user_not_found: "No account for this email.",
    over_email_send_rate_limit: "Too many links sent. Try again later.",
    email_address_not_authorized: "The email service can't send to this address.",
  };

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function signInErrorNote(e) {
    const code = e && e.code;
    const known = (code && SIGN_IN_ERRORS[code]) || (e && e.status === 429 && SIGN_IN_ERRORS.over_email_send_rate_limit);
    if (known) return escapeHtml(known);
    return escapeHtml("Could not send the link. Try again." + (code ? " (" + code + ")" : ""));
  }

  async function signIn(email) {
    try {
      if (!client) throw new Error("unavailable");
      const { error } = await client.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: location.origin + location.pathname + location.search,
          shouldCreateUser: false,
        },
      });
      if (error) throw error;
      setControl('<span class="auth-note">Check your email: a sign-in link was sent.</span>');
    } catch (e) {
      setControl(signedOutHtml(signInErrorNote(e)));
    }
  }

  async function signOut() {
    try {
      if (!client) throw new Error("unavailable");
      const { error } = await client.auth.signOut();
      if (error) throw error;
      showSignedOut();
    } catch (e) {
      setControl(signedInHtml("Could not sign out. Try again."));
    }
  }

  window.BrokerAuth = { init, signIn, signOut };
})();
