"""Content checks for supabase/README.md and ADR 0008 (issue #92, email + password sign-in)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "supabase" / "README.md"
CONFIG = ROOT / "app" / "frontend" / "client" / "config.js"
DECISIONS = ROOT / "docs" / "decisions"


def text():
    return README.read_text(encoding="utf-8").lower()


def lines():
    return text().splitlines()


def line_with(*patterns):
    """True if one single line (bullet) matches every regex."""
    return any(all(re.search(p, ln) for p in patterns) for ln in lines())


def adr(number):
    files = list(DECISIONS.glob(f"{number}-*.md"))
    assert len(files) == 1, number
    return files[0]


def test_req_92_1_no_google_oauth_or_linking_steps():
    """REQ-92-1"""
    t = text()
    for word in ("google", "oauth", "client secret", "linking", "authorize?provider"):
        assert word not in t, f"README still mentions {word!r}"
    assert not re.search(r"\bm4\b", t), "M4 linking test must be gone"


def test_req_92_2_signups_off():
    """REQ-92-2"""
    assert line_with(r"sign-?ups?[^.\n]*\boff\b|\boff\b[^.\n]*sign-?ups?")


def test_req_92_2_min_password_length_10():
    """REQ-92-2"""
    assert line_with(
        r"minimum password length[^.\n]*\b10\b|\b10\b[^.\n]*minimum password length"
    )


def test_req_92_2_secure_password_change_off():
    """REQ-92-2"""
    assert line_with(r"secure password change[^.\n]*\boff\b")


def test_req_92_3_smtp_gmail_app_password_route():
    """REQ-92-3: Erik's chosen route, with its prerequisites"""
    assert line_with(r"smtp\.gmail\.com")
    assert line_with(r"app password", r"2-step verification")


def test_req_92_3_transactional_provider_alternative():
    """REQ-92-3"""
    assert line_with(r"transactional", r"provider")


def test_req_92_3_smtp_credential_only_in_supabase():
    """REQ-92-3"""
    assert line_with(
        r"(app password|smtp|credential)",
        r"only[^.\n]*(supabase|smtp)",
        r"(never|not)[^.\n]*(repo|commit)",
    ) or line_with(
        r"(app password|smtp|credential)[^.\n]*only[^.\n]*supabase",
        r"never[^.\n]*repo",
    )


def test_req_92_3_smtp_settings_location():
    """REQ-92-3: where the SMTP credentials go"""
    assert line_with(r"authentication", r"smtp settings")


def test_req_92_4_builtin_mailer_team_members_only():
    """REQ-92-4"""
    assert line_with(
        r"built-in (email|mailer|email service)",
        r"only[^.\n]*team members|team members[^.\n]*only",
    )


def test_req_92_5_reset_password_template():
    """REQ-92-5"""
    assert line_with(r"reset password", r"template")


def test_req_92_5_redirect_url_allowlist():
    """REQ-92-5"""
    assert line_with(r"redirect urls", r"/brokerai/\*\*")


def test_req_92_6_invite_auto_confirm():
    """REQ-92-6"""
    assert line_with(r"create new user", r"auto confirm user")


def test_req_92_6_random_temporary_password_16_chars_private():
    """REQ-92-6"""
    assert line_with(
        r"random", r"temporary password", r"\b(16|[2-9]\d)\b[^.\n]*characters"
    ) or line_with(r"random", r"temporary password", r"16 or more")
    assert line_with(r"temporary password", r"privately")


def test_req_92_7_own_account_steps_in_order():
    """REQ-92-7: set password -> private-window check -> forgot-password test -> #85"""
    t = text()
    steps = [
        r"set[^.\n]*(your )?own password[^.\n]*magic link|magic link[^.\n]*still works",
        r"private[^.\n]*window[^.\n]*user id|user id[^.\n]*private[^.\n]*window",
        r"forgot[- ]password",
        r"only then[^.\n]*#85",
    ]
    positions = []
    for pattern in steps:
        m = re.search(pattern, t)
        assert m, f"missing own-account step: {pattern}"
        positions.append(m.start())
    assert positions == sorted(positions) and len(set(positions)) == 4, (
        f"own-account steps out of order: {positions}"
    )


def test_req_92_7_private_window_checks_data_unchanged():
    """REQ-92-7"""
    assert line_with(
        r"private[^.\n]*window",
        r"user id[^.\n]*unchanged",
        r"valuations[^.\n]*customers[^.\n]*notes",
    )


def test_req_92_7_send_password_recovery_fallback():
    """REQ-92-7"""
    assert line_with(r"send password recovery", r"(fallback|way back in|locked out)")


def test_req_92_8_no_invites_before_reset_mail_reached_non_team_address():
    """REQ-92-8"""
    assert line_with(
        r"(do not|don't|never) invite anyone|not invite anyone",
        r"reset (email|mail)",
        r"non-team",
    )


def test_req_92_9_no_real_project_ref():
    """REQ-92-9"""
    m = re.search(r"https://([a-z0-9]+)\.supabase\.co", CONFIG.read_text())
    assert m, "config.js should hold the project url"
    for doc in (text(), adr("0008").read_text(encoding="utf-8").lower()):
        assert m.group(1) not in doc
        for ref in re.findall(r"https://([a-z0-9<>-]+)\.supabase\.co", doc):
            assert ref == "<project-ref>", f"real-looking project ref: {ref}"


def test_req_92_9_no_emails_or_secrets():
    """REQ-92-9"""
    for path in (README, adr("0008")):
        raw = path.read_text(encoding="utf-8")
        assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", raw), f"email in {path.name}"
        assert not re.search(r"eyJ[\w-]{10,}\.[\w-]{10,}", raw), "JWT"
        assert not re.search(r"sb_(publishable|secret)_\w+", raw)
        assert not re.search(r"GOCSPX-\w+", raw)
        assert not re.search(r"\b[a-p]{4}( [a-p]{4}){3}\b", raw), "app password"
        assert not re.search(r"(?i)password\s*[:=]\s*`?\w{8,}", raw), "password value"


def test_req_92_10_adr_0008_accepted():
    """REQ-92-10"""
    assert re.search(
        r"^Status:\s*accepted",
        adr("0008").read_text(encoding="utf-8"),
        re.IGNORECASE | re.MULTILINE,
    )


def test_req_92_11_adr_0006_line_3_superseded_by_0008():
    """REQ-92-11"""
    line3 = adr("0006").read_text(encoding="utf-8").splitlines()[2].lower()
    assert re.search(r"sign-in[^.\n]*superseded[^.\n]*0008", line3), line3
