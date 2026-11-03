"""Tests for issue #48: revenue breakdown (validate.py rules, todo.py refill, AGENT.md)."""

from pathlib import Path

import pytest

from app.backend import todo as todo_module
from app.backend.storage import write_json
from app.backend.todo import refill
from app.backend.validate import LINE_ITEMS, validate

ROOT = Path(__file__).parent.parent
COMPANY = {
    "ticker": "A.ST",
    "name": "Alpha",
    "currency": "SEK",
    "report_currency": "SEK",
    "ir_url": "https://example.com/ir",
}
URL = "https://example.com/2026-Q1.pdf"


def quarter(period="2026-Q1", revenue=1000, **extra):
    values = dict.fromkeys(LINE_ITEMS, 100.0)
    values["revenue"] = revenue
    q = {
        "period": period,
        "report_date": "2026-07-17",
        "source_url": f"https://example.com/{period}.pdf",
        "values": values,
    }
    q.update(extra)
    return q


def write_data(tmp_path, quarters):
    write_json(tmp_path / "companies.json", [COMPANY])
    write_json(
        tmp_path / "financials" / "A.ST.json",
        {"ticker": "A.ST", "currency": "SEK", "quarters": quarters},
    )


def breakdown_errors(tmp_path, **q_kwargs):
    write_data(tmp_path, [quarter(**q_kwargs)])
    return [e for e in validate(tmp_path) if "breakdown" in e.lower()]


def test_req_48_2_valid_geography_passes(tmp_path):
    """REQ-48-2"""
    bd = {"geography": {"Sverige": 410, "Norden": 220, "Övrigt": 370}}
    write_data(tmp_path, [quarter(breakdown=bd)])
    assert validate(tmp_path) == []


def test_req_48_2_quarter_without_breakdown_passes(tmp_path):
    """REQ-48-2"""
    write_data(tmp_path, [quarter()])
    assert validate(tmp_path) == []


def test_req_48_2_null_dimension_passes(tmp_path):
    """REQ-48-2"""
    bd = {"geography": None, "segment": {"A": 600, "B": 400}}
    write_data(tmp_path, [quarter(breakdown=bd)])
    assert validate(tmp_path) == []


def test_req_48_2_both_dimensions_null_passes(tmp_path):
    """REQ-48-2"""
    write_data(tmp_path, [quarter(breakdown={"geography": None, "segment": None})])
    assert validate(tmp_path) == []


def test_req_48_1_unknown_key_is_an_error(tmp_path):
    """REQ-48-1"""
    bd = {"geography": None, "region": {"A": 1000}}
    assert breakdown_errors(tmp_path, breakdown=bd)


@pytest.mark.parametrize(
    "dimension",
    [{}, {"x" * 61: 1000}, {"A": "1000"}, {"A": True}, [1000], "Sverige"],
    ids=["empty-map", "long-name", "string-amount", "bool-amount", "list", "string"],
)
def test_req_48_2_bad_dimension_is_an_error(tmp_path, dimension):
    """REQ-48-2"""
    assert breakdown_errors(tmp_path, breakdown={"geography": dimension})


def test_req_48_2_name_of_60_characters_is_allowed(tmp_path):
    """REQ-48-2"""
    write_data(tmp_path, [quarter(breakdown={"segment": {"x" * 60: 1000}})])
    assert validate(tmp_path) == []


def test_req_48_2_breakdown_must_be_an_object(tmp_path):
    """REQ-48-2"""
    assert breakdown_errors(tmp_path, breakdown=[1, 2])


def test_req_48_3_sum_off_is_an_error_naming_quarter_and_dimension(tmp_path):
    """REQ-48-3"""
    errors = breakdown_errors(tmp_path, breakdown={"geography": {"A": 500, "B": 400}})
    assert len(errors) == 1
    assert "2026-Q1" in errors[0]
    assert "geography" in errors[0]


def test_req_48_3_segment_sum_off_is_an_error(tmp_path):
    """REQ-48-3"""
    errors = breakdown_errors(tmp_path, breakdown={"segment": {"A": 1100}})
    assert len(errors) == 1
    assert "segment" in errors[0]


def test_req_48_3_sum_within_tolerance_passes(tmp_path):
    """REQ-48-3: 985 vs 1000 is 1.5 %"""
    write_data(tmp_path, [quarter(breakdown={"geography": {"A": 600, "B": 385}})])
    assert validate(tmp_path) == []


def test_req_48_3_exactly_two_percent_passes(tmp_path):
    """REQ-48-3: a difference equal to the tolerance is not "more than" """
    write_data(tmp_path, [quarter(breakdown={"geography": {"A": 600, "B": 380}})])
    assert validate(tmp_path) == []


def test_req_48_3_just_over_two_percent_fails(tmp_path):
    """REQ-48-3"""
    assert breakdown_errors(tmp_path, breakdown={"geography": {"A": 600, "B": 379}})


def test_req_48_3_tolerance_is_at_least_the_number_of_parts(tmp_path):
    """REQ-48-3: revenue 10 -> 2 % is 0.2, but 3 parts allow a difference of 3"""
    edge = {"geography": {"A": 3, "B": 3, "C": 1}}  # sum 7, diff 3 == parts
    write_data(tmp_path, [quarter(revenue=10, breakdown=edge)])
    assert validate(tmp_path) == []
    over = {"geography": {"A": 3, "B": 3, "C": 0}}  # sum 6, diff 4 > 3
    assert breakdown_errors(tmp_path, revenue=10, breakdown=over)


def test_req_48_4_null_part_skips_the_sum_check(tmp_path):
    """REQ-48-4"""
    write_data(tmp_path, [quarter(breakdown={"geography": {"A": 100, "B": None}})])
    assert validate(tmp_path) == []


def test_req_48_4_null_revenue_skips_the_sum_check(tmp_path):
    """REQ-48-4"""
    write_data(
        tmp_path, [quarter(revenue=None, breakdown={"segment": {"A": 1, "B": 2}})]
    )
    assert validate(tmp_path) == []


def test_req_48_4_missing_revenue_skips_the_sum_check(tmp_path):
    """REQ-48-4"""
    q = quarter(breakdown={"segment": {"A": 1}})
    del q["values"]["revenue"]
    write_data(tmp_path, [q])
    assert validate(tmp_path) == []


# --- todo.py --refill ---


def setup_refill(tmp_path, quarters):
    write_json(tmp_path / "companies.json", [{"ticker": "A.ST"}])
    write_json(tmp_path / "financials" / "A.ST.json", {"quarters": quarters})


def periods(n):
    """n quarters ending 2026-Q4, oldest first."""
    out = []
    year, q = 2026, 4
    for _ in range(n):
        out.append(f"{year}-Q{q}")
        year, q = (year - 1, 4) if q == 1 else (year, q - 1)
    return list(reversed(out))


def test_req_48_6_depth_constant_is_8():
    """REQ-48-6"""
    assert todo_module.BREAKDOWN_DEPTH == 8


def test_req_48_5_48_6_only_newest_8_quarters_newest_first(tmp_path):
    """REQ-48-5, REQ-48-6"""
    ps = periods(10)
    setup_refill(tmp_path, [quarter(p) for p in ps])

    items = refill(tmp_path, total=50)

    assert [i.split(" |")[0] for i in items] == [f"A.ST {p}" for p in reversed(ps[2:])]
    for item in items:
        assert item.split(" | ")[1] == "breakdown.geography, breakdown.segment"


def test_req_48_5_lists_only_the_absent_dimension(tmp_path):
    """REQ-48-5"""
    bd = {"geography": {"A": 1000}}
    setup_refill(tmp_path, [quarter("2026-Q1", breakdown=bd)])

    assert refill(tmp_path) == [
        "A.ST 2026-Q1 | breakdown.segment | https://example.com/2026-Q1.pdf"
    ]


def test_req_48_5_empty_breakdown_object_lists_both(tmp_path):
    """REQ-48-5"""
    setup_refill(tmp_path, [quarter("2026-Q1", breakdown={})])

    assert refill(tmp_path) == [
        ("A.ST 2026-Q1 | breakdown.geography, breakdown.segment | " + URL),
    ]


def test_req_48_7_null_dimensions_are_not_listed(tmp_path):
    """REQ-48-7"""
    bd = {"geography": None, "segment": None}
    setup_refill(tmp_path, [quarter("2026-Q1", breakdown=bd)])

    assert refill(tmp_path) == []


def test_req_48_7_only_the_absent_dimension_is_listed_next_to_a_null_one(tmp_path):
    """REQ-48-7"""
    setup_refill(tmp_path, [quarter("2026-Q1", breakdown={"geography": None})])

    assert refill(tmp_path) == [
        "A.ST 2026-Q1 | breakdown.segment | https://example.com/2026-Q1.pdf"
    ]


def test_req_48_5_line_items_and_breakdown_keys_share_one_line(tmp_path):
    """REQ-48-5: existing line format, line-item keys first"""
    q = quarter("2026-Q1")
    del q["values"]["cash"]
    setup_refill(tmp_path, [q])

    assert refill(tmp_path) == [
        ("A.ST 2026-Q1 | cash, breakdown.geography, breakdown.segment | " + URL),
    ]


def test_req_48_6_depth_limit_applies_to_breakdown_keys_only(tmp_path):
    """REQ-48-6: an old quarter with a missing line item is still listed"""
    ps = periods(10)
    quarters = [quarter(p) for p in ps]
    del quarters[0]["values"]["cash"]
    setup_refill(tmp_path, quarters)

    items = refill(tmp_path, total=50)

    assert items[-1] == f"A.ST {ps[0]} | cash | https://example.com/{ps[0]}.pdf"


# --- AGENT.md ---


@pytest.fixture(scope="module")
def agent_md():
    return (ROOT / "AGENT.md").read_text(encoding="utf-8").lower()


@pytest.mark.parametrize("phrase", ["breakdown.geography", "breakdown.segment"])
def test_req_48_8_agent_md_mentions_the_refill_keys(agent_md, phrase):
    """REQ-48-8"""
    assert phrase in agent_md


def test_req_48_8_agent_md_has_the_name_and_null_rules(agent_md):
    """REQ-48-8: reuse stored names, new/merged parts new names, null when not given"""
    section = agent_md[agent_md.index("breakdown") :]
    assert "reuse" in section
    assert "null" in section
    assert "merged" in section
    assert "rewrite" in section or "never change" in section
