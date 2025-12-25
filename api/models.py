import dataclasses
import os
from typing import Optional


@dataclasses.dataclass
class TempFile:
    size: int
    path: str


@dataclasses.dataclass
class Image:
    url: str
    temp: Optional[TempFile]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.remove(self.temp.path)


@dataclasses.dataclass
class Audio:
    url: str
    title: str
    temp: Optional[TempFile]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.remove(self.temp.path)


@dataclasses.dataclass
class Collection:
    images: list[Image]
    audio: Optional[Audio]

    def __enter__(self):
        for image in self.images:
            image.__enter__()

        self.audio.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for image in self.images:
            image.__exit__(exc_type, exc_val, exc_tb)

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
        os.remove(self.temp.path)
