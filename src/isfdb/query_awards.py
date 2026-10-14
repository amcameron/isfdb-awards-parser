import argparse
import json
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from itemadapter import ItemAdapter

from .items import IsfdbItem, IsfdbAward
from .pipelines import IsfdbPipeline

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Query ISFDB for award information.")
    parser.add_argument(
        "command", choices=["pub", "title"], help="The type of lookup to execute."
    )
    parser.add_argument("id", type=int, help="The ID for the lookup.")
    parser.add_argument("-o", "--output", help="The output file for the JSON results.")
    args = parser.parse_args()

    db_user = os.environ.get("DB_USER")
    db_password = os.environ.get("DB_PASSWORD")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_name = os.environ.get("DB_NAME")

    if not all([db_user, db_password, db_name]):
        raise ValueError(
            "DB_USER, DB_PASSWORD, and DB_NAME environment variables are required"
        )

    engine = create_engine(
        f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}", echo=False
    )

    with Session(engine) as session:
        if args.command == "pub":
            query = f"""
            WITH resolved_titles AS (
  SELECT t.title_id AS oid, p.*
  FROM titles t
  JOIN titles p ON t.title_parent = p.title_id
  WHERE t.title_parent != 0
  UNION ALL
  SELECT t.title_id AS oid, t.*
  FROM titles t
  WHERE t.title_parent = 0
)
SELECT
    t.title_title as title, year(t.title_copyright) as year,
    CASE
        WHEN a.award_level = 71 THEN 'no winner -- insufficient votes'
        WHEN a.award_level = 72 THEN 'not on ballot -- insufficient nominations'
        WHEN a.award_level = 73 THEN 'no award given this year'
        WHEN a.award_level = 81 THEN 'withdrawn'
        WHEN a.award_level = 82 THEN 'withdrawn -- nomination declined'
        WHEN a.award_level = 83 THEN 'withdrawn -- conflict of interest'
        WHEN a.award_level = 84 THEN 'withdrawn -- official publication in a previous year'
        WHEN a.award_level = 85 THEN 'withdrawn -- ineligible'
        WHEN a.award_level = 90 THEN 'finalist'
        WHEN a.award_level = 91 THEN 'made first ballot'
        WHEN a.award_level = 92 THEN 'preliminary nominee'
        WHEN a.award_level = 93 THEN 'honorable mention'
        WHEN a.award_level = 98 THEN 'early submission'
        WHEN a.award_level = 99 THEN 'nomination below cutoff'
        WHEN awt.award_type_poll = 'No' AND a.award_level > 1 THEN 'nominee'
        WHEN awt.award_type_poll = 'No' AND a.award_level = 1 THEN 'winner'
        ELSE a.award_level
    END AS rank, 
    YEAR(a.award_year) AS award_year, awt.award_type_short_name as award_type_name, ac.award_cat_name
FROM pub_content pc
JOIN pubs p USING (pub_id)
JOIN resolved_titles t ON (pc.title_id = t.oid)
LEFT JOIN title_awards ta ON (pc.title_id = ta.title_id)
LEFT JOIN awards a USING (award_id)
LEFT JOIN award_cats ac USING (award_cat_id)
LEFT JOIN award_types awt USING (award_type_id)
WHERE pc.pub_id = {args.id}
ORDER BY CONVERT(pc.pubc_page, SIGNED) ASC;
            """
        elif args.command == "title":
            query = f"""
            WITH resolved_titles AS (
  SELECT t.title_id AS oid, p.*
  FROM titles t
  JOIN titles p ON t.title_parent = p.title_id
  WHERE t.title_parent != 0
  UNION ALL
  SELECT t.title_id AS oid, t.*
  FROM titles t
  WHERE t.title_parent = 0
)
SELECT
    t.title_title as title, year(t.title_copyright) as year,
    CASE
        WHEN a.award_level = 71 THEN 'no winner -- insufficient votes'
        WHEN a.award_level = 72 THEN 'not on ballot -- insufficient nominations'
        WHEN a.award_level = 73 THEN 'no award given this year'
        WHEN a.award_level = 81 THEN 'withdrawn'
        WHEN a.award_level = 82 THEN 'withdrawn -- nomination declined'
        WHEN a.award_level = 83 THEN 'withdrawn -- conflict of interest'
        WHEN a.award_level = 84 THEN 'withdrawn -- official publication in a previous year'
        WHEN a.award_level = 85 THEN 'withdrawn -- ineligible'
        WHEN a.award_level = 90 THEN 'finalist'
        WHEN a.award_level = 91 THEN 'made first ballot'
        WHEN a.award_level = 92 THEN 'preliminary nominee'
        WHEN a.award_level = 93 THEN 'honorable mention'
        WHEN a.award_level = 98 THEN 'early submission'
        WHEN a.award_level = 99 THEN 'nomination below cutoff'
        WHEN awt.award_type_poll = 'No' AND a.award_level > 1 THEN 'nominee'
        WHEN awt.award_type_poll = 'No' AND a.award_level = 1 THEN 'winner'
        ELSE a.award_level
    END AS rank, 
    YEAR(a.award_year) AS award_year, awt.award_type_short_name as award_type_name, ac.award_cat_name
FROM resolved_titles t
LEFT JOIN title_awards ta ON (t.title_id = ta.title_id OR t.oid = ta.title_id)
LEFT JOIN awards a USING (award_id)
LEFT JOIN award_cats ac USING (award_cat_id)
LEFT JOIN award_types awt USING (award_type_id)
WHERE t.oid = {args.id}
ORDER BY a.award_year ASC;
            """
        else:
            raise ValueError(f"Unknown command: {args.command}")

        result = session.execute(text(query))

        items_map: dict[tuple[str, str], IsfdbItem] = dict()

        for row in result:
            title_key = (row.title, str(row.year))

            item = items_map.setdefault(
                title_key, IsfdbItem(title=row.title, year=str(row.year))
            )

            # Only add award if award_type_name is not None (i.e., there was an award for this row)
            if row.award_type_name:
                award = IsfdbAward(
                    rank=str(row.rank),
                    year=str(row.award_year),
                    award=row.award_type_name,
                    category=row.award_cat_name,
                )
                item.awards.append(award)

    pipeline = IsfdbPipeline()
    processed_items = []
    for item in items_map.values():
        processed_item = pipeline.process_item(item)
        processed_items.append(ItemAdapter(processed_item).asdict())

    if args.output:
        with open(args.output, "w") as f:
            json.dump(processed_items, f)
    else:
        print(json.dumps(processed_items))


if __name__ == "__main__":
    main()
