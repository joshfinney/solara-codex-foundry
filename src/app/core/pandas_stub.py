"""Lightweight pandas substitute for test environments."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Iterable, Iterator, List


class Series:
    def __init__(self, data: Iterable):
        self._data = list(data)

    def __iter__(self) -> Iterator:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __getitem__(self, index: int):
        return self._data[index]

    def __setitem__(self, index: int, value) -> None:
        self._data[index] = value

    def min(self):
        return min(self._data)

    def max(self):
        return max(self._data)

    def __ge__(self, other):
        return [value >= other for value in self._data]

    @property
    def dtype(self) -> str:
        first = next((value for value in self._data if value is not None), None)
        if isinstance(first, _dt.datetime):
            return "datetime64"
        if isinstance(first, (int, float)):
            return "numeric"
        return "object"


class _LocAccessor:
    def __init__(self, frame: "DataFrame") -> None:
        self._frame = frame

    def __getitem__(self, mask: Iterable[bool]) -> "DataFrame":
        filtered = [row for row, keep in zip(self._frame._records, mask) if keep]
        return DataFrame(filtered)


class DataFrame:
    def __init__(self, records: Iterable[dict]):
        self._records: List[dict] = [dict(row) for row in records]
        columns: List[str] = []
        for row in self._records:
            for key in row.keys():
                if key not in columns:
                    columns.append(key)
        self.columns = columns

    def to_dict(self, orient: str) -> List[dict]:
        if orient != "records":
            raise ValueError("Only 'records' orient is supported")
        return [dict(row) for row in self._records]

    def __getitem__(self, key: str) -> Series:
        return Series(row.get(key) for row in self._records)

    def __setitem__(self, key: str, value) -> None:
        values = list(value)
        for idx, row in enumerate(self._records):
            if idx < len(values):
                row[key] = values[idx]
        if key not in self.columns:
            self.columns.append(key)

    @property
    def loc(self) -> _LocAccessor:
        return _LocAccessor(self)


def to_datetime(values: Iterable) -> Series:
    converted = []
    for value in values:
        if isinstance(value, _dt.datetime):
            converted.append(value)
        elif isinstance(value, _dt.date):
            converted.append(_dt.datetime.combine(value, _dt.time.min))
        else:
            converted.append(value)
    return Series(converted)


@dataclass
class _TypeAPI:
    def is_datetime64_any_dtype(self, dtype: str) -> bool:  # noqa: D401 - mimic pandas signature
        return dtype.startswith("datetime")

    def is_numeric_dtype(self, dtype: str) -> bool:
        return dtype == "numeric"


class _API:
    types = _TypeAPI()


api = _API()
