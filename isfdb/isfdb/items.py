# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IsfdbItem:
    title: str
    year: str
    awards: list[IsfdbAward] = field(default_factory=list)


@dataclass
class IsfdbAward:
    rank: str
    year: str
    award: str
    category: str
