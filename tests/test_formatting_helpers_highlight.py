from gui.helpers.formatting_helpers import highlight_text


def test_highlight_text_handles_overlapping_terms_without_nested_spans():
    result = highlight_text("catapult", ["cat", "at"])
    assert result.count("<span") == 1
    assert ">cat</span>apult" in result
    assert ">at</span>" not in result


def test_highlight_text_matches_html_special_char_terms():
    result = highlight_text("<tag> alpha & beta", ["<tag>", "&"])
    expected = (
        '<span style="background-color: yellow; font-weight: bold;">&lt;tag&gt;</span>'
        " alpha "
        '<span style="background-color: yellow; font-weight: bold;">&amp;</span>'
        " beta"
    )
    assert result == expected


def test_highlight_text_applies_optional_text_color():
    result = highlight_text(
        "alpha", ["alpha"], bg_color="#000", font_weight="600", text_color="#fff"
    )
    assert "color: #fff;" in result
    assert "background-color: #000;" in result
    assert "font-weight: 600;" in result
