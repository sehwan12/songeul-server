from math import isfinite
from typing import TYPE_CHECKING

from aiModel.utils.stroke_utils import (
    CHOSUNG_LIST,
    JUNGSUNG_LIST,
    STROKE_DIRECTION_RULES,
    decompose_hangul,
)

if TYPE_CHECKING:
    from dto.resultDTO import ResultCreate


STANDALONE_JAMO = set(CHOSUNG_LIST + JUNGSUNG_LIST)
# These compound jamo have a stroke count in the app but no direction rule yet.
COMPOUND_STROKE_COUNTS = {"ㅙ": 5, "ㄼ": 7}


def _stroke_count(jamo: str) -> int:
    return COMPOUND_STROKE_COUNTS.get(jamo, len(STROKE_DIRECTION_RULES.get(jamo, {})))


def _writable_cells(text: str) -> dict[str, tuple[str, list[int]]]:
    cells = {}
    cell = 0
    for character in text:
        jamo = decompose_hangul(character)
        if isinstance(jamo, tuple):
            cells[str(cell)] = (character, [_stroke_count(part) for part in jamo])
        elif character in STANDALONE_JAMO:
            # The Flutter client sends standalone jamo as one stroke group.
            cells[str(cell)] = (character, [_stroke_count(character), 0, 0])
        # Flutter's grid uses UTF-16 code unit offsets.
        cell += 2 if ord(character) > 0xFFFF else 1
    return cells


def validate_submission(
    payload: "ResultCreate", step_text: str
) -> dict[str, tuple[str, list[int]]]:
    if payload.practice_text != step_text:
        raise ValueError("연습 문장이 미션과 일치하지 않습니다.")

    cells = _writable_cells(step_text)
    if not cells or payload.cell_images.keys() != cells.keys():
        raise ValueError("필기해야 하는 모든 칸을 완성해 주세요.")
    if payload.firstandlast_stroke.keys() != cells.keys():
        raise ValueError("제출한 이미지와 획 좌표의 칸이 일치하지 않습니다.")

    for cell, (_, expected_counts) in cells.items():
        if payload.detailed_strokecounts.get(cell) != expected_counts:
            raise ValueError(f"{int(cell) + 1}번째 칸의 자모별 획수가 올바르지 않습니다.")
        stroke_count = sum(expected_counts)
        points = payload.firstandlast_stroke[cell]
        if len(payload.cell_images[cell]) != stroke_count or len(points) != stroke_count * 2:
            raise ValueError(f"{int(cell) + 1}번째 칸의 이미지와 획 좌표 수가 올바르지 않습니다.")
        if not all(isfinite(point.x) and isfinite(point.y) for point in points):
            raise ValueError(f"{int(cell) + 1}번째 칸의 획 좌표가 올바르지 않습니다.")

    return cells
