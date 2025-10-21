import logging
import re
from functools import partial

import scrapy

from ..items import IsfdbItem, IsfdbAward


class IsfdbParseError(Exception):
    pass


class AwardsSpider(scrapy.Spider):
    name = "awards"
    allowed_domains = ["isfdb.org"]
    _awards_rows_xpath = (
        "//h3[text() = 'Awards']/following-sibling::table/tr[position() > 1]"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [
            url.strip() for url in kwargs.get("start_urls", "").split(",")
        ]

    async def start(self):
        for url in self.start_urls:
            match url:
                case u if "title.cgi" in u:
                    yield scrapy.Request(url=u, callback=self.parse_title)
                case u if "pl.cgi" in u:
                    yield scrapy.Request(url=u, callback=self.parse_collection)
                case _:
                    logging.warning(f"Unknown URL: {url}")

    def parse_collection(self, response):
        collection_variant = response.xpath(
            "//h2[contains(text(), 'Contents')]/preceding-sibling::text()[contains(., 'variant of')]/following-sibling::a[@href[contains(., 'title.cgi')]]"
        )
        if collection_variant:
            variant_title = collection_variant.xpath("string(.)").get()
            callback = partial(self.parse_title, title_override=variant_title)
            yield response.follow(
                collection_variant.xpath("./@href").get(),
                callback=callback,
            )
        else:
            href = response.xpath(
                "//h2[contains(text(), 'Contents')]/preceding-sibling::a/@href[contains(., 'title.cgi')]"
            ).get()
            yield response.follow(href, callback=self.parse_title)

        for li in response.xpath(
            "//h2[contains(text(), 'Contents')]/following-sibling::ul/li[.//a[@href[contains(., 'title.cgi')]]]"
        ):
            li_text = li.xpath("string(.)").get()
            if "• interior artwork" in li_text:
                continue
            elif "• essay" in li_text:
                continue
            variant = li.xpath(
                "text()[contains(., '(variant of')]/following-sibling::a[@href[contains(., 'title.cgi')]]/@href"
            )
            if variant:
                variant_title = li.css("a::text").get()
                callback = partial(self.parse_title, title_override=variant_title)
                yield response.follow(variant.get(), callback=callback)
            else:
                href = li.xpath(".//a[@href[contains(., 'title.cgi')]]/@href").get()
                yield response.follow(
                    href,
                    callback=self.parse_title,
                )

    def parse_title(self, response, title_override=None):
        info_texts = [
            text.strip()
            for text in response.xpath(
                "//div[@id='content']/div[contains(., 'Title:')]//text()"
            ).getall()
            if text.strip()
        ]
        try:
            title_idx = info_texts.index("Title:")
            title = title_override or info_texts[title_idx + 1]
        except (ValueError, IndexError) as exc:
            raise IsfdbParseError("Title not found") from exc

        try:
            date_idx = info_texts.index("Date:")
            date = info_texts[date_idx + 1]
            publication_year = re.search(r"[0-9]{4}", date).group(0)
        except Exception as exc:
            raise IsfdbParseError(f"Unable to parse date: {date}") from exc

        awards = []
        for row in response.xpath(self._awards_rows_xpath):
            rank = row.xpath("./td[1]/a/text()").get()
            try:
                year, award = row.xpath("./td[2]/a/text()").re("([0-9]+) (.*)")
            except ValueError:
                print(f"Failure parsing: {row.xpath('./td[2]/a/text()')}")
                continue
            category = row.xpath("./td[3]/a/text()").get()
            awards.append(
                IsfdbAward(
                    rank=rank,
                    year=year,
                    award=award,
                    category=category,
                )
            )

        yield IsfdbItem(title=title, year=publication_year, awards=awards)
