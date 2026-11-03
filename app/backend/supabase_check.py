"""Static checks for the Supabase setup (issue #56, ADR 0005). No database, no network.

Run: uv run python -m app.backend.supabase_check
"""

import base64
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = "app/frontend/client/config.js"
VENDOR = "app/frontend/client/vendor/"
SELF_TEST = "tests/test_supabase.py"  # names the forbidden strings on purpose
APPEND_ONLY = "valuations"

JWT = re.compile(r"eyJ[A-Za-z0-9_-]+\.(eyJ[A-Za-z0-9_-]+)\.[A-Za-z0-9_-]+")
CREATE_TABLE = re.compile(
    r"create table (?:if not exists )?(?:public\.)?(\w+)", re.IGNORECASE
)
ENABLE_RLS = re.compile(
    r"alter table (?:public\.)?(\w+)\s+enable row level security", re.IGNORECASE
)
POLICY = re.compile(
    r"create policy\s+\w+\s+on\s+(?:public\.)?(\w+)(.*?);", re.IGNORECASE | re.DOTALL
)


def check_migrations(migrations_dir: Path) -> list[str]:
    """Return problems found in the SQL files; each names the table or file."""
    problems = []
    tables, rls, policies = set(), set(), []
    for f in sorted(migrations_dir.glob("*.sql")):
        sql = f.read_text()
        tables.update(t.lower() for t in CREATE_TABLE.findall(sql))
        rls.update(t.lower() for t in ENABLE_RLS.findall(sql))
        policies += [(t.lower(), body) for t, body in POLICY.findall(sql)]
        if re.search(r"disable\s+row\s+level\s+security", sql, re.IGNORECASE):
            problems.append(f"{f.name}: disables row level security")
    for table in sorted(tables):
        if table not in rls:
            problems.append(f"{table}: row level security is not enabled")
        if not any(
            t == table and re.search(r"for\s+select", b, re.IGNORECASE)
            for t, b in policies
        ):
            problems.append(f"{table}: no select policy")
    for table, body in policies:
        if re.search(r"\bto\s+anon\b", body, re.IGNORECASE):
            problems.append(f"{table}: policy grants access to anon")
        if re.search(r"using\s*\(\s*true\s*\)", body, re.IGNORECASE):
            problems.append(f"{table}: policy uses (true)")
        if not re.search(r"auth\.uid\(\)\s*=\s*user_id", body, re.IGNORECASE):
            problems.append(f"{table}: policy does not match auth.uid() = user_id")
        if table == APPEND_ONLY and re.search(
            r"for\s+(update|delete|all)", body, re.IGNORECASE
        ):
            problems.append(f"{table}: is append-only, no update/delete policy allowed")
    return problems


def _jwt_role(payload: str) -> str | None:
    try:
        return json.loads(
            base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        ).get("role")
    except ValueError:
        return None


def scan_secrets(root: Path, files: list[str]) -> list[str]:
    """Return problems for tracked files holding secret keys; each names the file."""
    problems = []
    for name in files:
        if name.startswith(VENDOR) or name == SELF_TEST:
            continue
        try:
            text = (root / name).read_text()
        except (UnicodeDecodeError, OSError):
            continue
        if "service_role" in text and not name.endswith(".md"):  # docs may name it
            problems.append(f"{name}: mentions service_role")
        if "sb_secret_" in text:
            problems.append(f"{name}: contains a secret key (sb_secret_)")
        for m in JWT.finditer(text):
            if name != CONFIG:
                problems.append(f"{name}: contains a JWT outside {CONFIG}")
            elif _jwt_role(m.group(1)) != "anon":
                problems.append(f"{name}: JWT is not an anon key")
    return problems


def main() -> int:
    files = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    problems = check_migrations(ROOT / "supabase" / "migrations") + scan_secrets(
        ROOT, files
    )
    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
