"""
Module to provide helper methods for tests.
"""
import difflib


def assert_if_lists_different(expected_tokens, actual_tokens):
    """
    Compart two lists and make sure they are equal, asserting if not.
    """

    print("\n---")
    print("expected_tokens: " + str(expected_tokens))
    print("parsed_tokens  : " + str(actual_tokens).replace("\n", "\\n"))
    assert len(expected_tokens) == len(actual_tokens), "List lengths are not the same."
    print("---")

    # pylint: disable=consider-using-enumerate
    for element_index in range(0, len(expected_tokens)):

        expected_str = str(expected_tokens[element_index])
        actual_str = str(actual_tokens[element_index])

        print("expected_tokens(" + str(len(expected_str)) + ")>>" + expected_str + "<<")
        print("actual_tokens  (" + str(len(actual_str)) + ")>>" + actual_str + "<<")

        diff = difflib.ndiff(expected_str, actual_str)

        diff_values = "\n".join(list(diff)) + "\n---\n"

        assert expected_str == str(actual_tokens[element_index]), (
            "List items " + str(element_index) + " are not equal." + diff_values
        )
    print("---\nToken lists are equal.\n---")
    # pylint: enable=consider-using-enumerate


def assert_if_strings_different(expected_string, actual_string):
    """
    Compart two strings and make sure they are equal, asserting if not.
    """

    print(
        "expected_string(" + str(len(expected_string)) + ")>>" + expected_string + "<<"
    )
    print("actual_string  (" + str(len(actual_string)) + ")>>" + actual_string + "<<")

    diff = difflib.ndiff(expected_string, actual_string)

    diff_values = "\n".join(list(diff)) + "\n---\n"

    assert expected_string == actual_string, "Strings are not equal." + diff_values
