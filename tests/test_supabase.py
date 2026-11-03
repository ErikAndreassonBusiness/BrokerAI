"""Tests for the Supabase SQL check and the secret scan (issue #56, ADR 0005).

Assumed interface (new module app/backend/supabase_check.py, no database or network):
  check_migrations(migrations_dir: Path) -> list[str]   problems, each naming the table or file
  scan_secrets(root: Path, files: list[str]) -> list[str]   problems, each naming the file (path relative to root)
Fake secrets are built at runtime so this file does not trip the scan itself.
"""

import base64
import importlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / "supabase" / "migrations"
CONFIG = "app/frontend/client/config.js"


def check():
    return importlib.import_module("app.backend.supabase_check")


def b64(obj):
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")


def jwt(role):
    return ".".join(
        [
            b64({"alg": "HS256", "typ": "JWT"}),
            b64({"role": role, "iss": "supabase"}),
            "c2ln" * 5,
        ]
    )


GOOD_SQL = """
create table public.things (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid(),
  ticker text not null
);
alter table public.things enable row level security;
create policy things_select on public.things for select to authenticated
  using (auth.uid() = user_id);
create policy things_insert on public.things for insert to authenticated
  with check (auth.uid() = user_id);
"""


def migrations(tmp_path, sql):
    d = tmp_path / "migrations"
    d.mkdir()
    (d / "20260101000000_init.sql").write_text(sql)
    return d


def problems(tmp_path, sql):
    return check().check_migrations(migrations(tmp_path, sql))


# --- SQL check on fixtures ---


def test_req_56_2_good_sql_passes(tmp_path):
    """REQ-56-2"""
    assert problems(tmp_path, GOOD_SQL) == []


def test_req_56_7_table_without_rls_fails_and_is_named(tmp_path):
    """REQ-56-7"""
    sql = GOOD_SQL.replace("alter table public.things enable row level security;", "")
    out = problems(tmp_path, sql)
    assert out and any("things" in p for p in out)


def test_req_56_2_disable_rls_fails(tmp_path):
    """REQ-56-2"""
    out = problems(
        tmp_path, GOOD_SQL + "alter table public.things disable row level security;"
    )
    assert out


def test_req_56_3_table_without_select_policy_fails(tmp_path):
    """REQ-56-3"""
    sql = re.sub(r"create policy things_select.*?;\n", "", GOOD_SQL, flags=re.DOTALL)
    out = problems(tmp_path, sql)
    assert out and any("things" in p for p in out)


def test_req_56_4_policy_to_anon_fails(tmp_path):
    """REQ-56-4"""
    sql = (
        GOOD_SQL
        + "create policy p on public.things for select to anon using (auth.uid() = user_id);"
    )
    assert problems(tmp_path, sql)


def test_req_56_4_using_true_fails(tmp_path):
    """REQ-56-4"""
    sql = (
        GOOD_SQL
        + "create policy p on public.things for select to authenticated using (true);"
    )
    assert problems(tmp_path, sql)


def test_req_56_3_policy_without_uid_match_fails(tmp_path):
    """REQ-56-3"""
    sql = (
        GOOD_SQL
        + "create policy p on public.things for delete to authenticated using (ticker = 'A.ST');"
    )
    assert problems(tmp_path, sql)


def test_req_56_3_valuations_update_policy_fails(tmp_path):
    """ADR 0005: valuations is append-only (no update/delete policy)"""
    sql = GOOD_SQL.replace("things", "valuations") + (
        "create policy v_upd on public.valuations for update to authenticated "
        "using (auth.uid() = user_id) with check (auth.uid() = user_id);"
    )
    assert problems(tmp_path, sql)


# --- SQL check on the real migrations ---


def real_sql():
    files = sorted(MIGRATIONS.glob("*.sql"))
    assert files, "no migrations in supabase/migrations"
    return "\n".join(f.read_text() for f in files).lower()


def test_req_56_1_tables_exist_with_key_columns():
    """REQ-56-1"""
    sql = real_sql()
    for table in ("valuations", "customers", "notes"):
        m = re.search(
            rf"create table (?:if not exists )?(?:public\.)?{table}\s*\((.*?)\n\);",
            sql,
            re.DOTALL,
        )
        assert m, table
        body = m.group(1)
        for col in ("user_id", "ticker", "created_at"):
            assert re.search(rf"\b{col}\b", body), f"{table}.{col}"
        if table != "valuations":  # ADR 0005: valuations is append-only, no updated_at
            assert re.search(r"\bupdated_at\b", body), f"{table}.updated_at"
    assert re.search(r"\bvalue numeric not null", sql)
    assert re.search(r"\bname text not null", sql)
    assert re.search(r"\bbody text not null", sql)


def test_req_56_2_real_migrations_pass_the_check():
    """REQ-56-2, REQ-56-3, REQ-56-4"""
    assert check().check_migrations(MIGRATIONS) == []


def test_req_56_6_migrations_hold_no_data_or_secrets():
    """REQ-56-6"""
    sql = real_sql()
    assert not re.search(r"\binsert\s+into\b", sql)
    assert "service" + "_role" not in sql and "sb_" + "secret_" not in sql


# --- Secret scan on fixtures ---


def scan(tmp_path, files):
    names = []
    for name, content in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        names.append(name)
    return check().scan_secrets(tmp_path, names)


def test_req_56_8_service_key_fails_and_names_file(tmp_path):
    """REQ-56-8"""
    out = scan(tmp_path, {"notes.txt": "key = " + "service" + "_role"})
    assert out and any("notes.txt" in p for p in out)


def test_req_56_8_secret_key_prefix_fails(tmp_path):
    """REQ-56-8"""
    out = scan(tmp_path, {"a.py": "k = '" + "sb_" + "secret_" + "abc123'"})
    assert out and any("a.py" in p for p in out)


def test_req_56_8_bare_secret_prefix_in_docs_passes(tmp_path):
    """REQ-56-8: naming the prefix (no key characters after it) is not a key."""
    out = scan(tmp_path, {"docs/x.md": "scan for `" + "sb_" + "secret_" + "` keys"})
    assert out == []


def test_req_56_8_jwt_outside_config_fails(tmp_path):
    """REQ-56-8"""
    out = scan(tmp_path, {"app/other.js": "const k = '" + jwt("anon") + "'"})
    assert out and any("other.js" in p for p in out)


def test_req_56_8_anon_jwt_in_config_passes(tmp_path):
    """REQ-56-8"""
    cfg = (
        "window.CONFIG = { url: 'https://x.supabase.co', anonKey: '"
        + jwt("anon")
        + "' };"
    )
    assert scan(tmp_path, {CONFIG: cfg}) == []


def test_req_56_8_publishable_key_in_config_passes(tmp_path):
    """REQ-56-8"""
    cfg = "window.CONFIG = { anonKey: '" + "sb_" + "publishable_" + "abc123' };"
    assert scan(tmp_path, {CONFIG: cfg}) == []


def test_req_56_8_service_key_jwt_in_config_fails(tmp_path):
    """REQ-56-8: a JWT in config.js must decode to role anon"""
    cfg = "window.CONFIG = { anonKey: '" + jwt("service" + "_role") + "' };"
    out = scan(tmp_path, {CONFIG: cfg})
    assert out and any("config.js" in p for p in out)


def test_req_56_8_vendor_directory_is_excluded(tmp_path):
    """REQ-56-8"""
    vendored = "var a = '" + jwt("anon") + "'; // service" + "_role"
    assert scan(tmp_path, {"app/frontend/client/vendor/supabase.js": vendored}) == []


def test_req_56_8_clean_files_pass(tmp_path):
    """REQ-56-8"""
    assert scan(tmp_path, {"a.py": "print('hi')", "b.md": "# Title"}) == []


# --- Real repo ---


def test_req_56_8_real_repo_has_no_secrets():
    """REQ-56-8, REQ-56-10"""
    files = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    assert check().scan_secrets(ROOT, files) == []


def test_req_56_9_reports_workflow_has_no_supabase_access():
    """REQ-56-9"""
    text = (ROOT / ".github" / "workflows" / "reports.yml").read_text().lower()
    assert "supabase" not in text and "service" + "_role" not in text


# --- Scan hardening ---


def test_req_56_8_uppercase_variants_fail(tmp_path):
    """REQ-56-8: matching is case-insensitive"""
    assert scan(tmp_path, {"a.txt": "SERVICE" + "_ROLE"})
    assert scan(tmp_path, {"b.txt": "SB_" + "SECRET_" + "x"})


def test_req_56_8_jwt_with_odd_header_fails(tmp_path):
    """REQ-56-8: a header that does not start with eyJ is still caught"""
    token = "eyAi" + "x" * 12 + "." + b64({"role": "anon"}) + ".c2ln" * 3
    assert scan(tmp_path, {"app/other.js": "k = '" + token + "'"})


def test_req_56_8_non_dict_jwt_payload_in_config_fails(tmp_path):
    """REQ-56-8: an undecodable or non-object payload is not an anon key"""
    for payload in (b64([1, 2, 3, 4, 5, 6]), "ey" + "A" * 12):
        token = ".".join([b64({"alg": "HS256"}), payload, "c2ln" * 5])
        cfg = "window.CONFIG = { anonKey: '" + token + "' };"
        assert scan(tmp_path, {CONFIG: cfg}), payload


def test_req_56_8_plain_word_only_allowed_in_docs(tmp_path):
    """REQ-56-8: the word may appear in docs, nowhere else"""
    word = "service" + "_role"
    docs = ("supabase/README.md", "docs/decisions/x.md", ".claude/agent-memory/a/m.md")
    for ok in docs:
        assert scan(tmp_path, {ok: word}) == [], ok
    for bad in ("README.md", "app/notes.md", "tests/x.py", "a.txt"):
        assert scan(tmp_path, {bad: word}), bad
