from __future__ import annotations

__all__ = ["BreakText", "BreakTextChunk", "break_text_never", "break_text_icu_line"]

# python
import os
import subprocess
from ctypes import CDLL
from ctypes import POINTER
from ctypes import byref
from ctypes import c_char_p
from ctypes import c_int
from ctypes import c_int32
from ctypes import c_int64
from ctypes import c_void_p
from platform import system
from typing import Any
from typing import Callable
from typing import Final
from typing import Generator
from typing import NamedTuple
from typing import TypeAlias


class BreakTextChunk(NamedTuple):
    text: str
    force_break: bool


BreakText: TypeAlias = Callable[[str], Generator[BreakTextChunk, None, None]]


def break_text_never(text: str) -> Generator[BreakTextChunk, None, None]:
    if not text:
        return
    yield BreakTextChunk(text, False)


def break_text_icu_line(text: str) -> Generator[BreakTextChunk, None, None]:
    with _UBreakIterator(text) as u_break_iterator:
        yield from u_break_iterator


if system() == "Windows":
    _LIB_NAME = "icuuc.dll"
    _POSTFIX = ""
else:
    if system() == "Darwin":
        _HOMEBREW_REPOSITORY = os.environ.get("HOMEBREW_REPOSITORY", "/usr/local")
        _LIB_NAME = f"{_HOMEBREW_REPOSITORY}/opt/icu4c/lib/libicuuc.dylib"
        _UCONV_NAME = f"{_HOMEBREW_REPOSITORY}/opt/icu4c/bin/uconv"
    else:
        _LIB_NAME = "libicuuc.so"
        _UCONV_NAME = "uconv"
    _uconv_result = subprocess.run([_UCONV_NAME, "-V"], capture_output=True, check=True)
    _POSTFIX = "_" + _uconv_result.stdout.decode("utf8").split(" ")[-1].split(".")[0]


_icuuc = CDLL(_LIB_NAME)

_UBRK_LINE: Final = 2
_U_ZERO_ERROR: Final = 0
_UBRK_DONE: Final = -1
_UBRK_LINE_HARD: Final = 100

_uloc_getDefault = getattr(_icuuc, f"uloc_getDefault{_POSTFIX}")
_uloc_getDefault.restype = c_char_p

_utext_openUTF8 = getattr(_icuuc, f"utext_openUTF8{_POSTFIX}")
_utext_openUTF8.argtypes = [c_void_p, c_char_p, c_int64, POINTER(c_int)]
_utext_openUTF8.restype = c_void_p

_utext_close = getattr(_icuuc, f"utext_close{_POSTFIX}")
_utext_close.argtypes = [c_void_p]

_ubrk_open = getattr(_icuuc, f"ubrk_open{_POSTFIX}")
_ubrk_open.argtypes = [c_int, c_char_p, c_void_p, c_int32, POINTER(c_int)]
_ubrk_open.restype = c_void_p

_ubrk_setUText = getattr(_icuuc, f"ubrk_setUText{_POSTFIX}")
_ubrk_setUText.argtypes = [c_void_p, c_void_p, POINTER(c_int)]

_ubrk_first = getattr(_icuuc, f"ubrk_first{_POSTFIX}")
_ubrk_first.argtypes = [c_void_p]

_ubrk_next = getattr(_icuuc, f"ubrk_next{_POSTFIX}")
_ubrk_next.argtypes = [c_void_p]
_ubrk_next.restype = c_int32

_ubrk_getRuleStatus = getattr(_icuuc, f"ubrk_getRuleStatus{_POSTFIX}")
_ubrk_getRuleStatus.argtypes = [c_void_p]
_ubrk_getRuleStatus.restype = c_int32

_ubrk_close = getattr(_icuuc, f"ubrk_close{_POSTFIX}")
_ubrk_close.argtypes = [c_void_p]

_DEFAULT_ULOC: Final = _uloc_getDefault()


class _UBreakIterator:
    _previous_chunk_index: int = 0
    _urbrk: c_void_p | None = None
    _c_text: c_char_p | None = None

    def __init__(self, text: str) -> None:
        self._utf8_text = text.encode("utf8")

    def __iter__(self) -> _UBreakIterator:
        return self

    def __next__(self) -> BreakTextChunk:
        next_chunk_index = _ubrk_next(self._urbrk)
        if next_chunk_index == _UBRK_DONE:
            raise StopIteration()

        chunk = self._utf8_text[self._previous_chunk_index : next_chunk_index]
        hard_break = _ubrk_getRuleStatus(self._urbrk) == _UBRK_LINE_HARD
        self._previous_chunk_index = next_chunk_index

        return BreakTextChunk(chunk.decode("utf8"), hard_break)

    def __enter__(self) -> _UBreakIterator:
        error = c_int()

        self._c_text = c_char_p(self._utf8_text)

        self._urbrk = _ubrk_open(_UBRK_LINE, _DEFAULT_ULOC, 0, 0, byref(error))
        if error.value > _U_ZERO_ERROR:
            self._urbrk = None
            raise RuntimeError("icu ubrk_open error: {error.value}")

        utext = _utext_openUTF8(0, self._c_text, len(self._utf8_text), byref(error))
        if error.value > _U_ZERO_ERROR:
            raise RuntimeError("icu utext_openUTF8 error: {error.value}")
        try:
            _ubrk_setUText(self._urbrk, utext, byref(error))
            if error.value > _U_ZERO_ERROR:
                raise RuntimeError("icu ubrk_setUText error: {error.value}")
        finally:
            _utext_close(utext)

        return self

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        if self._urbrk is not None:
            _ubrk_close(self._urbrk)
            self._urbrk = None

        self._c_text = None
