// Tests for frontend sign-in and the Supabase client (issue #57, ADR 0002/0005). No network: a mocked client.
//
// Assumed seam (to be built in app/frontend/client/):
//   config.js  sets window.BROKERAI_CONFIG = { url, anonKey } (public values only).
//   auth.js    reads window.supabase.createClient(url, anonKey) (vendored lib) and exposes window.BrokerAuth:
//                init({ timeoutMs }) -> Promise<"signed-in" | "signed-out" | "unavailable">
//                  renders the control into document.getElementById("auth"), and a short message into every
//                  element of document.querySelectorAll("[data-user-section]") (innerHTML):
//                  signed out -> "Sign in", signed in -> section left for its feature (no sign-in message), down/unconfigured -> "Unavailable".
//                signIn(email) / signOut() -> Promise; the control's form and button call these.
//              The client used: auth.getSession() -> { data: { session }, error }, auth.signInWithOtp({ email }) -> { error },
//              auth.signOut() -> { error }. auth.js must not call fetch itself.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const client = path.join(__dirname, "..", "..", "app", "frontend", "client");
const read = (f) => fs.readFileSync(path.join(client, f), "utf8");

const CONFIG = { url: "https://example.supabase.co", anonKey: "anon-public-key" };
const PAGE = "<h1>Alpha</h1> Quarterly financials";

// opts: config (or null = none), getSession (function), signInWithOtp, signOut
function openPage(opts = {}) {
  const calls = { createClient: [], otp: [], signOut: 0, fetch: 0 };
  const control = { innerHTML: "" };
  const sections = [{ innerHTML: "" }, { innerHTML: "" }];
  const app = { innerHTML: PAGE };
  const client = {
    auth: {
      getSession: opts.getSession || (async () => ({ data: { session: null }, error: null })),
      signInWithOtp:
        opts.signInWithOtp ||
        (async (args) => {
          calls.otp.push(args);
          return { error: null };
        }),
      signOut:
        opts.signOut ||
        (async () => {
          calls.signOut++;
          return { error: null };
        }),
      onAuthStateChange: () => ({ data: { subscription: { unsubscribe() {} } } }),
    },
  };
  const window = {
    BROKERAI_CONFIG: opts.config === null ? undefined : opts.config || CONFIG,
    supabase: {
      createClient: (...args) => {
        calls.createClient.push(args);
        return client;
      },
    },
  };
  const context = vm.createContext({
    window,
    document: {
      getElementById: (id) => (id === "auth" ? control : id === "app" ? app : null),
      querySelectorAll: (sel) => (sel === "[data-user-section]" ? sections : []),
      title: "",
    },
    fetch: async () => {
      calls.fetch++;
      throw new Error("network is not allowed in tests");
    },
    setTimeout,
    clearTimeout,
    console,
  });
  vm.runInContext(read("auth.js"), context);
  return { window, control, sections, app, calls };
}

const init = (page, timeoutMs = 30) => page.window.BrokerAuth.init({ timeoutMs });
const SESSION = { data: { session: { user: { email: "erik@example.com" } } }, error: null };

test("REQ-57-1: config.js holds the project URL and anon key only", () => {
  const window = {};
  vm.runInContext(read("config.js"), vm.createContext({ window }));
  assert.deepEqual(Object.keys(window.BROKERAI_CONFIG).sort(), ["anonKey", "url"]);
  assert.ok(!/service_role/i.test(read("config.js")));
});

test("REQ-57-1: the client is created from the public config", async () => {
  const page = openPage();
  await init(page);
  assert.deepEqual(page.calls.createClient[0], [CONFIG.url, CONFIG.anonKey]);
});

test("REQ-57-2, REQ-57-7: signed out shows Sign in with an email field and a Sign in message in user sections", async () => {
  const page = openPage();
  assert.equal(await init(page), "signed-out");
  assert.match(page.control.innerHTML, /<input[^>]*type="email"/);
  assert.match(page.control.innerHTML, /sign in/i);
  assert.ok(!/sign out/i.test(page.control.innerHTML));
  for (const s of page.sections) assert.match(s.innerHTML, /sign in/i);
});

test("REQ-57-3: submitting an email asks Supabase for a magic link and shows that it was sent", async () => {
  const page = openPage();
  await init(page);
  await page.window.BrokerAuth.signIn("erik@example.com");
  assert.equal(page.calls.otp.length, 1);
  assert.equal(page.calls.otp[0].email, "erik@example.com");
  assert.match(page.control.innerHTML, /link (was )?sent|check your (e-?mail|inbox)/i);
});

test("REQ-57-4: a failed sign-in request shows a short error and leaves the page working", async () => {
  const page = openPage({ signInWithOtp: async () => ({ error: { message: "rate limited" } }) });
  await init(page);
  await page.window.BrokerAuth.signIn("erik@example.com");
  assert.match(page.control.innerHTML, /could not|couldn.t|error|failed/i);
  assert.ok(!/link (was )?sent/i.test(page.control.innerHTML));
  assert.equal(page.app.innerHTML, PAGE);
});

test("REQ-57-4: a rejected sign-in request is also shown as an error", async () => {
  const page = openPage({
    signInWithOtp: async () => {
      throw new Error("offline");
    },
  });
  await init(page);
  await page.window.BrokerAuth.signIn("erik@example.com");
  assert.match(page.control.innerHTML, /could not|couldn.t|error|failed/i);
});

test("REQ-57-5: with a session the control offers Sign out and user sections have no sign-in message", async () => {
  const page = openPage({ getSession: async () => SESSION });
  assert.equal(await init(page), "signed-in");
  assert.match(page.control.innerHTML, /sign out/i);
  for (const s of page.sections) {
    assert.ok(!/sign in|unavailable/i.test(s.innerHTML), s.innerHTML);
  }
});

test("REQ-57-6: signing out ends the session and user sections show Sign in again", async () => {
  const page = openPage({ getSession: async () => SESSION });
  await init(page);
  await page.window.BrokerAuth.signOut();
  assert.equal(page.calls.signOut, 1);
  assert.match(page.control.innerHTML, /<input[^>]*type="email"/);
  for (const s of page.sections) assert.match(s.innerHTML, /sign in/i);
});

test("REQ-57-8: a failing client shows Unavailable", async () => {
  const page = openPage({
    getSession: async () => {
      throw new Error("boom");
    },
  });
  assert.equal(await init(page), "unavailable");
  for (const s of page.sections) assert.match(s.innerHTML, /unavailable/i);
});

test("REQ-57-8: a client that times out shows Unavailable", async () => {
  const page = openPage({ getSession: () => new Promise(() => {}) });
  assert.equal(await init(page, 20), "unavailable");
  for (const s of page.sections) assert.match(s.innerHTML, /unavailable/i);
});

test("REQ-57-8: a session error from Supabase shows Unavailable", async () => {
  const page = openPage({ getSession: async () => ({ data: { session: null }, error: { message: "down" } }) });
  assert.equal(await init(page), "unavailable");
});

test("REQ-57-8, REQ-57-1: missing config shows Unavailable and creates no client", async () => {
  for (const config of [null, {}, { url: "", anonKey: "" }, { url: CONFIG.url }]) {
    const page = openPage({ config });
    assert.equal(await init(page), "unavailable", JSON.stringify(config));
    assert.equal(page.calls.createClient.length, 0);
    for (const s of page.sections) assert.match(s.innerHTML, /unavailable/i);
  }
});

test("REQ-57-9: page content from data/ is untouched and auth makes no fetches in every state", async () => {
  const states = [
    {},
    { getSession: async () => SESSION },
    {
      getSession: async () => {
        throw new Error("boom");
      },
    },
    { getSession: () => new Promise(() => {}) },
    { config: null },
    { signInWithOtp: async () => ({ error: { message: "x" } }) },
  ];
  for (const opts of states) {
    const page = openPage(opts);
    await init(page, 20);
    await page.window.BrokerAuth.signIn("erik@example.com").catch(() => {});
    assert.equal(page.app.innerHTML, PAGE);
    assert.equal(page.calls.fetch, 0);
  }
});
