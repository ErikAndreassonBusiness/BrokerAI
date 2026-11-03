"""Content checks for supabase/README.md Google setup docs (issue #78, ADR 0006)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "supabase" / "README.md"
CONFIG = ROOT / "app" / "frontend" / "client" / "config.js"


def text():
    return README.read_text(encoding="utf-8").lower()


def has_all(*phrases):
    t = text()
    missing = [p for p in phrases if p.lower() not in t]
    assert not missing, f"README is missing: {missing}"


def test_req_78_1_google_cloud_steps():
    """REQ-78-1"""
    has_all(
        "google cloud", "oauth consent screen", "external", "openid", "email", "profile"
    )
    has_all("web application")
    t = text()
    assert re.search(r"publish\w*[^.\n]*production|production[^.\n]*publish", t), (
        "publish to production"
    )


def test_req_78_2_redirect_uri_is_pattern():
    """REQ-78-2"""
    has_all("https://<project-ref>.supabase.co/auth/v1/callback")


def test_req_78_2_8_no_real_project_ref():
    """REQ-78-2, REQ-78-8"""
    m = re.search(r"https://([a-z0-9]+)\.supabase\.co", CONFIG.read_text())
    assert m, "config.js should hold the project url"
    assert m.group(1) not in text()
    for ref in re.findall(r"https://([a-z0-9<>-]+)\.supabase\.co", text()):
        assert ref == "<project-ref>", f"real-looking project ref: {ref}"


def test_req_78_3_client_secret_only_in_supabase():
    """REQ-78-3"""
    has_all("authentication > providers > google", "client secret", "skip nonce check")
    t = text()
    assert re.search(r"(never|not)[^.\n]*(repo|commit)", t), "secret never in the repo"
    assert re.search(r"skip nonce check[^.\n]*off|off[^.\n]*skip nonce check", t)


def test_req_78_4_invite_with_auto_confirm():
    """REQ-78-4"""
    has_all("authentication > users", "auto confirm", "exact", "google address")
    t = text()
    assert "+" in t and "alias" in t
    assert re.search(r"sign-?ups[^.\n]*off", t)


def test_req_78_5_url_configuration_kept():
    """REQ-78-5"""
    has_all("url configuration", "site url", "redirect urls", "/brokerai/**")


def test_req_78_6_m4_linking_test():
    """REQ-78-6"""
    has_all("m4", "linking", "auto confirm")
    has_all(
        "https://<project-ref>.supabase.co/auth/v1/authorize?provider=google&redirect_to="
    )
    has_all("browser")
    t = text()
    assert re.search(r"no new user", t)
    assert "linked" in t
    assert re.search(r"uninvited[^.\n]*refused|refused[^.\n]*uninvited", t)
    assert "user id" in t and "unchanged" in t
    for word in ("valuations", "customers", "notes"):
        assert word in t


def test_req_78_6_fallback_adr_0006_option_b():
    """REQ-78-6"""
    t = text()
    assert re.search(r"0006[^.\n]*option b|option b[^.\n]*0006", t)
    assert "fall back" in t or "fallback" in t


def test_req_78_7_email_provider_disabled_last():
    """REQ-78-7"""
    t = text()
    assert re.search(r"disable[^.\n]*email provider|email provider[^.\n]*disabl", t)
    assert re.search(r"only after[^.\n]*home page[^.\n]*google", t)


def test_req_78_8_no_emails_or_secrets():
    """REQ-78-8"""
    raw = README.read_text(encoding="utf-8")
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", raw), "email address in README"
    assert not re.search(r"eyJ[\w-]{10,}\.[\w-]{10,}", raw), "JWT in README"
    assert not re.search(r"sb_(publishable|secret)_\w+", raw)
    assert not re.search(r"GOCSPX-\w+", raw)


def test_req_78_adrs_accepted():
    """ADR 0006 and 0007 flipped to accepted in this PR (approved by Erik)"""
    for pattern in ("0006-*.md", "0007-*.md"):
        files = list((ROOT / "docs" / "decisions").glob(pattern))
        assert len(files) == 1, pattern
        assert re.search(
            r"^Status:\s*accepted", files[0].read_text(), re.IGNORECASE | re.MULTILINE
        ), files[0].name
