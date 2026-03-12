import dataclasses
import os
from typing import Optional


@dataclasses.dataclass
class TempFile:
    size: int
    path: str


def _cleanup_temp_file(temp: Optional[TempFile]) -> None:
    if not temp:
        return

    try:
        os.remove(temp.path)
    except FileNotFoundError:
        return


@dataclasses.dataclass
class Image:
    url: str
    temp: Optional[TempFile]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _cleanup_temp_file(self.temp)


@dataclasses.dataclass
class Audio:
    url: str
    title: str
    temp: Optional[TempFile]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _cleanup_temp_file(self.temp)


@dataclasses.dataclass
class Collection:
    images: list[Image]
    audio: Optional[Audio]

    def __enter__(self):
        for image in self.images:
            image.__enter__()

        if self.audio:
            self.audio.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for image in self.images:
            image.__exit__(exc_type, exc_val, exc_tb)

        if self.audio:
            self.audio.__exit__(exc_type, exc_val, exc_tb)


@dataclasses.dataclass
class Video:
    url: str
    temp: Optional[TempFile]
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _cleanup_temp_file(self.temp)


@dataclasses.dataclass
class Post:
    card: Image
    media: list[Image | Video]
    inlined_image_url: Optional[str] = None

    def __enter__(self):
        self.card.__enter__()
        for item in self.media:
            item.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.card.__exit__(exc_type, exc_val, exc_tb)
        for item in self.media:
            item.__exit__(exc_type, exc_val, exc_tb)
