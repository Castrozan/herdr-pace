import re

PUNCTUATION_PATTERN = re.compile(r"[.!?,;:\u2014\u2013-]$")


def compute_optimal_recognition_point(word: str) -> int:
    length = len(word)
    if length <= 1:
        return 0
    if length <= 5:
        return 1
    if length <= 9:
        return 2
    if length <= 13:
        return 3
    return (length - 1) // 3


def has_trailing_punctuation(word: str) -> bool:
    return bool(PUNCTUATION_PATTERN.search(word))
