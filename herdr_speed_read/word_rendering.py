import re

from wcwidth import wcswidth

ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"
ANSI_RESET = "\033[0m"

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


def format_word_with_orp_highlight(
    word: str, focus_color: int, center_width: int
) -> str:
    orp_position = compute_optimal_recognition_point(word)
    pad_left = max(0, (center_width // 2) - wcswidth(word[:orp_position]))

    before = word[:orp_position]
    focus = word[orp_position : orp_position + 1]
    after = word[orp_position + 1 :]

    focus_colored = f"\033[38;5;{focus_color}m{ANSI_BOLD}{focus}{ANSI_RESET}"

    return (
        " " * pad_left
        + f"{ANSI_DIM}{before}{ANSI_RESET}"
        + focus_colored
        + f"{ANSI_DIM}{after}{ANSI_RESET}"
    )


def has_trailing_punctuation(word: str) -> bool:
    return bool(PUNCTUATION_PATTERN.search(word))
