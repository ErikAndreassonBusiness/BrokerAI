from app.backend.storage import write_json
from app.backend.todo import missing_quarters, todo


def setup(tmp_path, stored: dict[str, list[str]]):
    write_json(tmp_path / "companies.json", [{"ticker": t} for t in stored])
    for ticker, periods in stored.items():
        if periods is not None:
            quarters = [{"period": p} for p in periods]
            write_json(
                tmp_path / "financials" / f"{ticker}.json", {"quarters": quarters}
            )


def test_missing_includes_gaps_and_is_newest_first(tmp_path):
    setup(tmp_path, {"A.ST": ["2021-Q3", "2021-Q4", "2022-Q2"]})

    assert missing_quarters(tmp_path) == {"A.ST": ["2022-Q1"]}


def test_missing_goes_up_to_the_latest_quarter_of_any_company(tmp_path):
    setup(
        tmp_path,
        {"A.ST": ["2022-Q1"], "B.ST": ["2021-Q3", "2021-Q4", "2022-Q1", "2022-Q2"]},
    )

    assert missing_quarters(tmp_path)["A.ST"] == ["2022-Q2", "2021-Q4", "2021-Q3"]
    assert missing_quarters(tmp_path)["B.ST"] == []


def test_company_without_a_file_gets_every_quarter(tmp_path):
    setup(tmp_path, {"A.ST": ["2021-Q3", "2021-Q4"], "B.ST": None})

    assert missing_quarters(tmp_path)["B.ST"] == ["2021-Q4", "2021-Q3"]


def test_todo_is_round_robin_with_caps(tmp_path):
    setup(tmp_path, {"A.ST": ["2023-Q1"], "B.ST": ["2023-Q1"]})

    items = todo(tmp_path, total=5, per_company=3)

    assert items == [
        "A.ST 2022-Q4",
        "B.ST 2022-Q4",
        "A.ST 2022-Q3",
        "B.ST 2022-Q3",
        "A.ST 2022-Q2",
    ]


def test_todo_is_empty_when_everything_is_stored(tmp_path):
    setup(tmp_path, {"A.ST": ["2021-Q3", "2021-Q4"]})

    assert todo(tmp_path) == []
