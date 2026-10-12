# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import logging
import re
from collections.abc import Iterable
from functools import reduce

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

from .items import IsfdbAward


def _contains_any(haystack: str, needles: Iterable[str]):
    return any(needle in haystack for needle in needles)


class IsfdbPipeline:
    _ignored_award_names = (
        "aml award",
        "balrog",
        "beehive",
        "brandon",
        "canopus",
        "deathrealm",
        "ditmar",
        "endeavour",
        "gandalf",
        "gaylactic",
        "goodreads",
        "ifa",
        "ignotus",
        "ihg",
        "imaginaire",
        "itogi",
        "lambda",
        "lasswitz",
        "locus online",
        "lodestar",
        "mythopoeic",
        "neffy",
        "prometheus",
        "seiun",
        "sfbc",
        "shelley",
        "utopia",
        "wellman",
    )
    _ignored_categories = ("ravenheart",)
    _ignored_ranks = (
        "below cutoff",
        "early submission",
        "insufficient",
        "made first",
        "no award given",
        "preliminary",
        "withdraw",
    )

    def process_item(self, item, spider=None):
        adapter = ItemAdapter(item)
        processed_awards = []
        for award in adapter["awards"]:
            try:
                processed_awards.append(IsfdbPipeline.process_award(award))
            except DropItem as exc:
                logging.info(f"Dropped award: {award}: {exc.args[0]}")
                continue
        adapter["awards"] = processed_awards
        return item

    @staticmethod
    def process_award(award: IsfdbAward):
        processed_award_name = IsfdbPipeline.process_award_name(award.award)
        return IsfdbAward(
            year=award.year,
            rank=IsfdbPipeline.process_rank(award.rank),
            category=IsfdbPipeline.process_category(
                award.category, processed_award_name
            ),
            award=processed_award_name,
        )

    @staticmethod
    def process_rank(rank: str):
        if not rank:
            raise DropItem("Rank is missing or empty")

        rank_lower = rank.lower()
        if _contains_any(rank_lower, IsfdbPipeline._ignored_ranks):
            raise DropItem(f"Ignoring rank: {rank}")

        if "nomin" in rank_lower:
            return "nominee"
        if "win" in rank_lower:
            return "winner"
        if "finalist" in rank_lower:
            return "finalist"
        if "honorable" in rank_lower:
            return "honorable mention"

        try:
            n = int(rank, base=10)
        except ValueError:
            raise DropItem(f"Unrecognized rank: {rank}")

        if n < 1:
            raise DropItem(f"Unrecognized rank: {rank}")

        if n == 1:
            return "winner"

        # Suffix calculation
        if 11 <= (n % 100) <= 13:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

        return f"{n}{suffix}"

    @staticmethod
    def process_category(category: str, award: str):
        category_lower = category.lower()
        if _contains_any(category_lower, IsfdbPipeline._ignored_categories):
            raise DropItem(f"Ignoring category: {category}")

        if re.search(r"Compton Crook", category):
            return "Best First Novel"

        replacements: list[tuple[str, str]] = [
            (r"LGBT.*Fiction.*", "LGBTQ Speculative Fiction"),
            ("Science Fiction", "SF"),
            (r" – English$", ""),
            (r" - Adult$", ""),
            ("Eugie Award", "Best Short Fiction"),
        ]

        award_lower = award.lower()
        if "aurora" in award_lower:
            replacements.extend(
                [
                    ("Best", "Best Canadian"),
                    ("Long-Form Work in English.*", "Novel"),
                    ("Short-Form Work in English.*", "Short Fiction"),
                ]
            )
        if "british fantasy" in award_lower:
            replacements.extend(
                [
                    (r".*(Best Horror Novel)", r"\1"),
                    (r".*Fantasy.*", "Best Fantasy Novel"),
                    (r".*(Best Newcomer).*", r"\1"),
                ]
            )
        if "chesley" in award_lower:
            if _contains_any(category_lower, ("achievement", "contribution")):
                raise DropItem(f"Ignoring category: {category}")
            replacements.append((" - .*$", ""))
        if "dick" in award_lower:
            replacements.append((r".*", "Best SF Paperback (US)"))
        if "gemmell" in award_lower:
            replacements.extend(
                [
                    ("Legend Award", "Best Fantasy Novel"),
                    ("Morningstar Award", "Best Fantasy Newcomer"),
                ]
            )
        if any(word in award_lower for word in ("nebula", "sf chronicle", "homer")):
            replacements.append((r"^", "Best "))
        if "sunburst" in award_lower:
            replacements.extend(
                [
                    (r".*Canadian.*", "Novel"),
                    (r"^Adult$", "Novel"),
                    (r"^Young Adult.*", "Novel (YA)"),
                    (r"^", "Best Canadian "),
                ]
            )
        if "le guin" in award_lower:
            replacements.append((r".*(Le Guin Prize).*", r"\1"))

        processed_category = reduce(
            lambda acc, val: re.sub(*val, acc, count=1), replacements, category
        )

        return processed_category

    @staticmethod
    def process_award_name(name: str):
        if not name:
            return ""

        name_lower = name.lower()
        if _contains_any(name_lower, IsfdbPipeline._ignored_award_names):
            raise DropItem(f"Ignoring award name: {name}")

        replacements = [
            ("BFA", "British Fantasy"),
            ("BSFA", "British Science Fiction"),
            ("Brandon", "Carl Brandon Society"),
            ("Campbell Memorial", "John W Campbell Memorial"),
            ("Clarke", "Arthur C Clarke"),
            ("Crook", "Compton Crook Memorial"),
            ("Dick", "Philip K Dick"),
            ("Gemmell", "David Gemmell Legend"),
            ("Le Guin", "Ursula K Le Guin Prize"),
            ("Locus Poll", "Locus"),
            ("Norton", "Andre Norton"),
            ("Stoker", "Bram Stoker"),
            ("Sturgeon", "Theodore Sturgeon Memorial"),
        ]

        processed_name = reduce(lambda acc, val: acc.replace(*val), replacements, name)

        if not any(
            processed_name.endswith(suffix) for suffix in ("Award", "Awards", "Prize")
        ):
            processed_name = f"{processed_name} Award"

        return processed_name
