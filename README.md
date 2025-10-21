In brief:
1. Install the project (e.g. `uv pip install .` from the project root, or your preferred build system);
2. Choose a publication page for a given collection and make a note of the URL, e.g. https://www.isfdb.org/cgi-bin/pl.cgi?105271;
3. Run scrapy from inside the `src/` directory, saving to a convenient file, e.g. `scrapy crawl awards -a start_urls="https://www.isfdb.org/cgi-bin/pl.cgi?105271" -O output.json`
4. Run the `isfdb-format` executable on the output. `isfdb-format --help` for details. e.g. `isfdb-format --description output.json`

Example output:

```
Semley's Necklace (1964)
April in Paris (1962)
The Masters (1963)
Darkness Box (1963)
The Word of Unbinding (1964)
The Rule of Names (1964)
Winter's King (1969. Short Story: Hugo (5th))
The Good Trip (1970)
Nine Lives (1969. Novelette: Nebula (nominee))
Things (1970)
A Trip to the Head (1970)
Vaster Than Empires and More Slow (1971. Short Fiction: Locus (14th); Short Story: Hugo (2nd))
The Stars Below (1974. Short Story: Locus (12th))
The Field of Vision (1973. Short Fiction: Locus (11th))
The Direction of the Road (1973)
The Ones Who Walk Away from Omelas (1973. Short Story: Hugo (winner); Short Fiction: Locus (6th))
The Day Before the Revolution (1974. Short Story: Locus (winner), Nebula (winner), Hugo (finalist))
```
