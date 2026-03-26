import sys

sys.path.insert(0, ".")

from gui.helpers.formatting_helpers import (
    format_search_display,
    normalize_chunk_for_parse,
)

# Test 1: normalize_chunk_for_parse
print("=== Test 1: normalize_chunk_for_parse ===")
result1 = normalize_chunk_for_parse("svp")
print("Input: 'svp'")
print(f"Output: {result1}")
print("Expected: ['svp']")
print(f"Match: {result1 == ['svp']}")

# Test 2: format_search_display
print("\n=== Test 2: format_search_display ===")
chunks = [["svp"]]
result2 = format_search_display(chunks)
print(f"Input: {chunks}")
print(f"Output: '{result2}'")
print("Expected: 'svp'")
print(f"Match: {result2 == 'svp'}")

# Test 3: Full flow simulation
print("\n=== Test 3: Full flow ===")
search_text = "svp"
raw_chunks = [search_text.strip()] if search_text else []
chunk_terms_lists = [normalize_chunk_for_parse(chunk) for chunk in raw_chunks]
print(f"1. search_text: '{search_text}'")
print(f"2. raw_chunks: {raw_chunks}")
print(f"3. chunk_terms_lists: {chunk_terms_lists}")
display_text = format_search_display(chunk_terms_lists)
print(f"4. display_text: '{display_text}'")
print("Expected: 'svp'")
print(f"Match: {display_text == 'svp'}")
