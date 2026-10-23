"""Offline tests of the crawler: sample pages in Wiktionary's wikitext format and a fake fetcher.

Run from the project folder:  python -m tests.test_crawler
"""
from crawler.wikitext import language_section, etymology_text, parse_links, entry_title
from crawler.wiktionary_crawler import crawl_word
from crawler.languages import classify_chain

PAGES = {
    "whale": """==English==
{{wikipedia}}
===Etymology===
From {{inh|en|enm|whal}}, from {{inh|en|ang|hwæl}}, from {{inh|en|gem-pro|*hwalaz}}, possibly from
{{der|en|ine-pro|*(s)kʷálos||sheatfish}}. Cognate with {{cog|de|Wal}}, {{cog|nl|walvis}}.

===Pronunciation===
* {{IPA|en|/weɪl/}}

===Noun===
{{en-noun}}
# A large marine mammal.
""",
    "captain": """==English==
===Etymology===
From {{inh|en|enm|capitayn}}, from {{der|en|fro|capitaine}}, from {{der|en|LL.|capitāneus||chief}},
from {{der|en|la|caput||head}}. {{doublet|en|chieftain}}.

===Noun===
{{en-noun}}
""",
    "harpoon": """==English==
===Etymology===
{{bor+|en|fr|harpon}}.

===Noun===
{{en-noun}}

==French==
===Etymology===
From {{inh|fr|fro|harpon||clamp}}.
""",
    "harpon": """==French==
===Etymology===
From {{inh|fr|fro|harpon}}, from {{inh|fr|fro|harper||to grip}}.
""",
    "harper": """==Old French==
===Etymology===
From {{der|fro|frk|*harpā||hook}}.

===Verb===
{{fro-verb}}
""",
    "sky": """==English==
===Etymology 1===
From {{inh|en|enm|sky||cloud}}, from {{bor|en|non|ský||cloud}}.

===Noun===
# The atmosphere above a given point.

===Etymology 2===
From {{der|en|la|scaevus}}.
""",
    "whaleman": """==English==
===Etymology===
{{compound|en|whale|man}}

===Noun===
{{en-noun}}
""",
    "cetology": """==English==
===Etymology===
From {{af|en|ceto-|-logy}}, from {{der|en|grc|κῆτος||whale}}.
""",
    "chase": """==English==
===Etymology===
{{etyl|enm|en}} {{m|enm|chacen}}, {{etyl|fro|en}} {{m|fro|chacier}}.
""",
}


class FakeFetcher:
    def __init__(self, pages):
        self.pages, self.requested = pages, []

    def fetch(self, title):
        self.requested.append(title)
        return self.pages.get(title)

    def close(self):
        pass


def test_sections():
    page = PAGES["harpoon"]
    assert "fr|fro|harpon" not in language_section(page, "English")
    assert "fr|fro|harpon" in language_section(page, "French")
    assert language_section(PAGES["whale"], "Latin") == ""
    assert "scaevus" not in etymology_text(language_section(PAGES["sky"], "English"))  # first etymology only


def test_parse_links():
    links = parse_links(etymology_text(language_section(PAGES["whale"], "English")))
    assert [(l["lang"], l["term"]) for l in links] == [
        ("enm", "whal"), ("ang", "hwæl"), ("gem-pro", "*hwalaz"), ("ine-pro", "*(s)kʷálos")]  # cognates ignored
    assert links[0]["rel"] == "inherited"
    cap = parse_links(etymology_text(language_section(PAGES["captain"], "English")))
    assert [l["lang"] for l in cap] == ["enm", "fro", "LL.", "la"]                          # doublet ignored
    assert parse_links(etymology_text(language_section(PAGES["harpoon"], "English")))[0] == \
        {"lang": "fr", "term": "harpon", "rel": "borrowed"}
    old = parse_links(etymology_text(language_section(PAGES["chase"], "English")))
    assert [(l["lang"], l["term"]) for l in old] == [("enm", "chacen"), ("fro", "chacier")]
    comp = parse_links(etymology_text(language_section(PAGES["whaleman"], "English")))
    assert comp == [{"lang": "en", "term": "whale", "rel": "formation"}]


def test_titles():
    assert entry_title("gem-pro", "*hwalaz") == "Reconstruction:Proto-Germanic/hwalaz"
    assert entry_title("LL.", "capitāneus") == "capitaneus"        # macron removed for Latin
    assert entry_title("frk", "*harpā") == "Reconstruction:Frankish/harpā"


def test_crawl_follows_links():
    f = FakeFetcher(PAGES)
    status, chain = crawl_word("harpoon", f)
    assert status == "ok"
    # harpoon (English page) -> 'harpon' (French section) -> 'harper' (Old French section) -> Frankish
    assert [(c["lang"], c["term"]) for c in chain] == [
        ("fr", "harpon"), ("fro", "harpon"), ("fro", "harper"), ("frk", "*harpā")]
    assert f.requested[:3] == ["harpoon", "harpon", "harper"]
    assert classify_chain(chain) == ("French", "Other")

    status, chain = crawl_word("whaleman", FakeFetcher(PAGES))     # formation -> follows the base word
    assert chain[0]["term"] == "whale" and classify_chain(chain)[0] == "Germanic (native)"
    assert classify_chain(crawl_word("captain", FakeFetcher(PAGES))[1]) == ("French", "Latin")
    assert classify_chain(crawl_word("sky", FakeFetcher(PAGES))[1])[0] == "Old Norse"
    assert crawl_word("nonexistentword", FakeFetcher(PAGES))[0] == "no_page"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("passed:", name)
