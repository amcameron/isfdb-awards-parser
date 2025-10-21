import json
from enum import Enum, auto
from itertools import chain

from .items import IsfdbItem, IsfdbAward


class FormatTarget(Enum):
    DESCRIPTION = auto()
    TAGS = auto()


def fmt(target: FormatTarget, items: list[IsfdbItem]):
    collection, items = items[0], items[1:]

    match target:
        case FormatTarget.DESCRIPTION:
            _format_for_desc(items, collection)
        case FormatTarget.TAGS:
            _format_for_tags(items, collection)
        case _:
            raise ValueError(f"unknown target: {target}")


def _format_for_desc(collection_items: list[IsfdbItem], collection: IsfdbItem):
    for item in collection_items:
        if not item.awards:
            print(f"{item.title} ({item.year})")
            continue

        # Group awards by category
        awards_by_category: dict[str, list[IsfdbAward]] = {}
        for award in item.awards:
            award.category = (
                award.category.removeprefix("Best ")
                .removeprefix("Superior Achievement in a ")
                .removeprefix("Superior Achievement in ")
            )
            award.award = award.award.removesuffix(" Awards").removesuffix(" Award")
            awards_by_category.setdefault(award.category, []).append(award)

        print(f"{item.title} ({item.year}. ", end="")

        category_strings = []
        for category, cat_awards in awards_by_category.items():
            award_strings = [f"{award.award} ({award.rank})" for award in cat_awards]
            category_strings.append(f"{category}: {', '.join(award_strings)}")

        print(f"{'; '.join(category_strings)})")


def _format_for_tags(collection_items: list[IsfdbItem], collection: IsfdbItem):
    all_awards = chain(
        collection.awards,
        chain.from_iterable(item.awards for item in collection_items),
    )

    print(", ".join(map(_format_award_for_tags, all_awards)))


def _format_award_for_tags(award: IsfdbAward) -> str:
    rank_suffix = " place" if award.rank[0] in "123456789" else ""
    return f"{award.award}.{award.category}.{award.year}.{award.rank}{rank_suffix}"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Format ISFDB award data.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-t", "--tags", action="store_true", help="Format as tags")
    group.add_argument(
        "-d",
        "--description",
        action="store_true",
        help="Format for book description (default)",
    )
    parser.add_argument(
        "input_file", help="Path to the input JSON file containing ISFDB items"
    )

    args = parser.parse_args()

    target = FormatTarget.TAGS if args.tags else FormatTarget.DESCRIPTION

    with open(args.input_file, "r") as f:
        data = json.load(f)

    items = [IsfdbItem(**item) for item in data]
    fmt(target, items)


if __name__ == "__main__":
    main()
