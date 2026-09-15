from wcwidth import wcswidth


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


def render_terminal_word(word: str, width: int) -> str:
    if wcswidth(word) > width:
        return "Enlarge pane to read."[:width]
    focus = compute_optimal_recognition_point(word)
    padding = max(0, min(width - wcswidth(word), width // 2 - wcswidth(word[:focus])))
    return (
        " " * padding
        + word[:focus]
        + "\033[31m"
        + word[focus : focus + 1]
        + "\033[39m"
        + word[focus + 1 :]
    )
