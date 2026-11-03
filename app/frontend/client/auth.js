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
      setControl(signedOutHtml("Could not send the link. Try again."));
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
