import pandas as pd

from interface import table_printer as tp

EXACT_TOTAL = 10
EXACT_PAGE = 5
REMAINDER_TOTAL = 13
REMAINDER_PAGE = 5
REMAINDER_LAST = 3
SIZE_ONE_TOTAL = 3


def collect_pages(df, page_size):
    return [p.copy() for p in tp.paginate_dataframe(df, page_size)] if not df.empty else []


def test_paginate_empty_df():
    df = pd.DataFrame(columns=["a"])  # vazio
    pages = collect_pages(df, 5)
    assert pages == []


def test_paginate_exact_division():
    df = pd.DataFrame({"a": list(range(EXACT_TOTAL))})
    pages = collect_pages(df, EXACT_PAGE)
    assert len(pages) == EXACT_TOTAL // EXACT_PAGE
    assert pages[0].shape == (EXACT_PAGE, 1)
    assert pages[1].shape == (EXACT_PAGE, 1)
    assert pages[0]["a"].tolist() == list(range(EXACT_PAGE))
    assert pages[1]["a"].tolist() == list(range(EXACT_PAGE, EXACT_TOTAL))


def test_paginate_with_remainder():
    df = pd.DataFrame({"a": list(range(REMAINDER_TOTAL))})
    pages = collect_pages(df, REMAINDER_PAGE)
    expected_pages = REMAINDER_TOTAL // REMAINDER_PAGE + 1
    assert len(pages) == expected_pages
    assert pages[-1].shape == (REMAINDER_LAST, 1)
    assert pages[-1]["a"].tolist() == list(range(REMAINDER_TOTAL - REMAINDER_LAST, REMAINDER_TOTAL))


def test_paginate_page_size_one():
    values = [10, 11, 12]
    df = pd.DataFrame({"a": values})
    pages = collect_pages(df, 1)
    assert len(pages) == SIZE_ONE_TOTAL
    assert [p.iloc[0, 0] for p in pages] == values
