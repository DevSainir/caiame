"""
Turning a human title into a machine-safe name.

Used for course addresses and for the names of objects in storage. Kept here rather than in
a service because both callers need exactly the same answer: two transliterations of the
same title would give two different addresses for one course.
"""

import re

# Cyrillic as it is normally written in Latin letters in Kyrgyzstan and Russia. Spelled out
# rather than pulled from a library: a library brings its own opinion about ё, щ and й, and
# a course address is not something to have change under a dependency update.
TRANSLITERATION = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
    "ң": "n",
    "ө": "o",
    "ү": "u",
}


def slugify(value: str, *, fallback: str = "item") -> str:
    """
    A lowercase name of letters, digits and single hyphens.

    Everything that is not one of those becomes a hyphen, so a name arriving from a person —
    with slashes, dots or right-to-left marks in it — cannot turn into a path of its own.
    A title made entirely of such characters would give an empty name; that is what the
    fallback is for.
    """
    lowered = value.strip().lower()
    transliterated = "".join(TRANSLITERATION.get(char, char) for char in lowered)
    cleaned = re.sub(r"[^a-z0-9]+", "-", transliterated).strip("-")
    return cleaned or fallback


def file_extension(name: str, *, fallback: str) -> str:
    """The extension of a file name, lowercase and without the dot, or the fallback."""
    _, _, tail = name.rpartition(".")
    cleaned = re.sub(r"[^a-z0-9]", "", tail.lower())
    return cleaned or fallback
