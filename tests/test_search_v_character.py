#!/usr/bin/env python
"""
Test script to verify that 'v' character is NOT processed as logical operator.

This test demonstrates that the CORRECT app_logic.py (simplified version)
does NOT have the regex bug that cuts the 'v' character.

Run this test to verify the fix:
    python tests/test_search_v_character.py

Expected: All tests PASS with 'v' character preserved in all cases.
"""

import os
import sys
from typing import Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.app_logic import parse_search_terms


def _to_search_terms(value: Any) -> list[str]:
    assert isinstance(value, list)
    return [str(item) for item in value]


def test_v_character():
    """Test that v character is preserved in search terms."""
    print("=" * 60)
    print("Testing v character preservation in search logic")
    print("=" * 60)

    test_cases = [
        {
            "input": ["svp"],
            "expected_value": "svp",
            "description": "Single term with v in middle",
        },
        {
            "input": ["servico"],
            "expected_value": "servico",
            "description": "Term with v in middle (servico)",
        },
        {
            "input": ["preventiva"],
            "expected_value": "preventiva",
            "description": "Term with v at start (preventiva)",
        },
        {
            "input": ["dev"],
            "expected_value": "dev",
            "description": "Term ending with v",
        },
        {"input": ["v"], "expected_value": "v", "description": "Single v character"},
        {
            "input": ["sistema", "servico"],
            "expected_values": ["sistema", "servico"],
            "description": "Multiple terms with v (comma-separated)",
        },
        {
            "input": ["avaliacao"],
            "expected_value": "avaliacao",
            "description": "Multiple v characters in term",
        },
    ]

    all_passed = True

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['description']}")
        print(f"  Input: {test['input']}")

        result = parse_search_terms(_to_search_terms(test["input"]))

        if "expected_values" in test:
            # Multiple terms test
            values = [term["value"] for term in result]
            expected = test["expected_values"]
            passed = values == expected
            print(f"  Output values: {values}")
            print(f"  Expected: {expected}")
        else:
            # Single term test
            if result:
                value = result[0]["value"]
                expected = test["expected_value"]
                passed = value == expected
                print(f"  Output value: {value}")
                print(f"  Expected: {expected}")
            else:
                passed = False
                print("  ERROR: No result returned!")

        if passed:
            print("  Status: PASS")
        else:
            print("  Status: FAIL")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED - v character preserved correctly!")
    else:
        print("SOME TESTS FAILED - v character being processed incorrectly!")
    print("=" * 60)

    assert all_passed, "v character not preserved correctly in some tests"


def test_no_logical_operators():
    """Test that logical operators are NOT processed."""
    print("\n" + "=" * 60)
    print("Testing that logical operators are NOT processed")
    print("=" * 60)

    test_cases = [
        {
            "input": ["termo1", "OU", "termo2"],
            "expected_count": 3,
            "description": "OU keyword should be treated as regular term",
        },
        {
            "input": ["termo1", "OR", "termo2"],
            "expected_count": 3,
            "description": "OR keyword should be treated as regular term",
        },
        {
            "input": ["termo1", "AND", "termo2"],
            "expected_count": 3,
            "description": "AND keyword should be treated as regular term",
        },
        {
            "input": ["termo1", "E", "termo2"],
            "expected_count": 3,
            "description": "E keyword should be treated as regular term",
        },
    ]

    all_passed = True

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['description']}")
        print(f"  Input: {test['input']}")

        result = parse_search_terms(_to_search_terms(test["input"]))
        count = len(result)
        expected = test["expected_count"]
        passed = count == expected

        print(f"  Output count: {count}")
        print(f"  Expected count: {expected}")
        print(f"  Parsed terms: {[t['value'] for t in result]}")

        # All terms should be in group 0 (AND logic)
        groups = set(t["group"] for t in result)
        if groups != {0}:
            print(f"  ERROR: Multiple groups found: {groups} (expected only group 0)")
            passed = False

        if passed:
            print("  Status: PASS")
        else:
            print("  Status: FAIL")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED - Logical operators NOT processed!")
    else:
        print("SOME TESTS FAILED - Logical operators being processed!")
    print("=" * 60)

    assert all_passed, "Logical operators not ignored correctly in some tests"


if __name__ == "__main__":
    print("\nSearch Logic v Character Test")
    print("Verifying fix for intermittent v character disappearing bug\n")

    try:
        test_v_character()
        test1_passed = True
    except AssertionError:
        test1_passed = False

    try:
        test_no_logical_operators()
        test2_passed = True
    except AssertionError:
        test2_passed = False

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"v character preservation: {'PASS' if test1_passed else 'FAIL'}")
    print(f"Logical operators ignored: {'PASS' if test2_passed else 'FAIL'}")

    if test1_passed and test2_passed:
        print("\nALL TESTS PASSED - Search simplification working correctly!")
        sys.exit(0)
    else:
        print("\nSOME TESTS FAILED - Issues detected!")
        sys.exit(1)
