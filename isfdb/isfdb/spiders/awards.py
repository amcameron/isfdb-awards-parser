import logging

import scrapy


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
        # TODO: The current logic should be used as a fallback.
        #       The primary logic should check whether the row contains,
        #       "(variant of (link))", and if so, follow that link instead.
        for link in response.xpath(
            "//h2[contains(text(), 'Contents')]/following-sibling::ul/li/a/@href[contains(., 'title.cgi')]"
        ):
            yield response.follow(link, callback=self.parse_title)

    def parse_title(self, response):
        # TODO: handle variant titles
        #       (check for text in info block linking the original,
        #       and follow that link to check for awards there)
        info_texts = [
            text.strip()
            for text in response.xpath(
                "//div[@id='content']/div[contains(., 'Title:')]//text()"
            ).getall()
            if text.strip()
        ]
        try:
            title_idx = info_texts.index("Title:")
            title = info_texts[title_idx + 1]
        except (ValueError, IndexError) as exc:
            raise IsfdbParseError("Title not found") from exc

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
                dict(
                    rank=rank,
                    year=year,
                    award=award,
                    category=category,
                )
            )

        yield dict(title=title, awards=awards)
