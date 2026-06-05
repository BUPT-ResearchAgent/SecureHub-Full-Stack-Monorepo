# Status: [planned]

from typing import TypeVar

T = TypeVar("T")


def safety_review(output: T) -> T:
    return output
