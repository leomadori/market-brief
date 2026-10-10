#!/usr/bin/env python3
"""Headline fetcher for the market dashboard.

news mode:   news RSS feeds + Google News, grouped by keyword, with trends and
             top stories -> data/latest.json (+ latest.js for index.html)
reddit mode: hot posts from the subreddits in config "reddit_sections"
             -> data/reddit.json (+ reddit.js for reddit.html)

Usage:  python3 fetch.py [news|reddit]
"""

import fcntl
import html
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
HISTORY = DATA / "history"
STATE_FILE = DATA / "state.json"
REDDIT_STATE = DATA / "reddit_state.json"
TERM_STATS = DATA / "term_stats.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) market-dashboard/0.1"
NOW = datetime.now(timezone.utc)

# Words that never count as a trend: plain English plus generic headline/market vocabulary.
STOPWORDS = set("""
a about above after again against all almost also am among an and any are aren't around as at back be because been
before being below between both but by can can't could did didn't do does doesn't doing don't down during each even
ever every few for from further get gets getting go goes going gone got had has hasn't have haven't having he her here
hers him his how however i if in into is isn't it it's its just know like made make makes making many may me might more
most much must my near need new news next no nor not now of off on once one only or other our out over own per put
really said same say says see seen she should since so some still such take takes than that that's the their them then
there these they thing things think this those though through to today too top under until up upon us use used very via
want wants was wasn't way we week weeks well were what when where whether which while who whom why will with without
won't would year years yet you your yours day days time first last two three four five six ten big just amid
price prices market markets crypto cryptocurrency cryptocurrencies coin coins token tokens stock stocks trading trade
trader traders investor investors investing investment buy sell bought sold rally rallies surge surges drop drops fall
falls rise rises gains gain loss losses high low higher lower record update daily weekly report reports analysis help
discussion question thoughts anyone someone people guys why's what's here's let's i'm i've you're we're they're dd yolo
billion million trillion percent new latest live breaking says said could should would back first again amid ahead
look looks looking long short term news via official end start set sets hits hit near way best worst good bad still
january february march april june july august september october november december monday tuesday wednesday thursday
friday saturday sunday tomorrow yesterday tonight u.s u.k us uk
""".split())


# ---------- fetching & parsing ----------

def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def reddit_get(url):
    """GET that respects Reddit's rate-limit headers (unauthenticated ≈ 1 request / 30s)."""
    for attempt in range(3):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                body = r.read()
                if float(r.headers.get("x-ratelimit-remaining", 1)) < 1:
                    reddit_get.wait = float(r.headers.get("x-ratelimit-reset", 30)) + 1
                else:
                    reddit_get.wait = 2
                return body
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 2:
                raise
            wait = float(e.headers.get("retry-after") or e.headers.get("x-ratelimit-reset") or 30) + 1
            print(f"    Reddit rate limit, waiting {wait:.0f}s…")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def reddit_pause():
    time.sleep(getattr(reddit_get, "wait", 2))


def local(tag):
    return tag.rsplit("}", 1)[-1]


def child(el, name):
    for c in el:
        if local(c.tag) == name:
            return c
    return None


def parse_date(text):
    if not text:
        return None
    text = text.strip()
    try:
        d = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()


def parse_feed(raw):
    """Parse RSS or Atom into a list of {title, url, published, source_hint}."""
    root = ET.fromstring(raw)
    out = []
    for el in root.iter():
        if local(el.tag) not in ("item", "entry"):
            continue
        t = child(el, "title")
        link = child(el, "link")
        url = ""
        if link is not None:
            url = link.get("href") or (link.text or "")
        date_el = next((d for d in (child(el, n) for n in ("pubDate", "published", "updated"))
                        if d is not None), None)
        src = child(el, "source")
        out.append({
            "title": clean(t.text if t is not None else ""),
            "url": url.strip(),
            "published": parse_date(date_el.text if date_el is not None else None),
            "source_hint": clean(src.text) if src is not None and src.text else None,
        })
    return [i for i in out if i["title"] and i["url"]]


def fetch_news(cfg, status):
    items = []
    for name, url in cfg["news_feeds"].items():
        try:
            for i in parse_feed(http_get(url)):
                items.append({**i, "source": name, "type": "news"})
            status[name] = "ok"
        except Exception as e:
            status[name] = f"error: {e}"
    return items


def fetch_reddit(cfg, status):
    items = []
    for section, subs in cfg["reddit_sections"].items():
        for sub in subs:
            # "hot" only: the login-free "new" feed is delayed hours and added almost nothing (tested 2026-10-10).
            print(f"  r/{sub}")
            url = f"https://www.reddit.com/r/{sub}/hot/.rss?limit=50"
            try:
                for i in parse_feed(reddit_get(url)):
                    if "/comments/" in i["url"]:
                        items.append({**i, "source": f"r/{sub}", "type": "reddit", "section": section})
                status[f"r/{sub}"] = "ok"
            except Exception as e:
                status[f"r/{sub}"] = f"error: {e}"
            reddit_pause()
    return items


def fetch_google_news(cfg, topic, aliases, status, scoped=False):
    q = " OR ".join(f'"{a}"' for a in aliases[:4])
    if scoped:  # trend terms are generic; keep results about markets/crypto
        q = f"({q}) (crypto OR bitcoin OR stocks OR markets OR blockchain)"
    q += " when:1d"
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    items = []
    try:
        for i in parse_feed(http_get(url))[: cfg["settings"]["google_news_per_keyword"]]:
            source = i["source_hint"] or "Google News"
            title = re.sub(r"\s+-\s+" + re.escape(source) + r"$", "", i["title"]) if i["source_hint"] else i["title"]
            items.append({**i, "title": title, "source": source, "type": "news"})
    except Exception as e:
        status[f"Google News: {topic}"] = f"error: {e}"
    return items


# ---------- matching ----------

def alias_regex(aliases):
    parts = [r"\b" + re.escape(a).replace(r"\ ", r"[\s\-]") + r"\b" for a in aliases]
    # Short all-caps aliases (ETH, BTC, RWA) must match case-sensitively to avoid false hits.
    strict = [p for a, p in zip(aliases, parts) if a.isupper() and len(a) <= 5]
    loose = [p for a, p in zip(aliases, parts) if not (a.isupper() and len(a) <= 5)]
    rs = []
    if loose:
        rs.append(re.compile("|".join(loose), re.I))
    if strict:
        rs.append(re.compile("|".join(strict)))
    return rs


def matches(title, regexes):
    return any(r.search(title) for r in regexes)


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def same_story(a, b):
    """Near-duplicate titles: one contains the other ("SOL news: X" vs "X"), or ≥80% word overlap."""
    if a["norm"] in b["norm"] or b["norm"] in a["norm"]:
        return min(len(a["words"]), len(b["words"])) >= 5
    return len(a["words"] & b["words"]) / len(a["words"] | b["words"]) >= 0.8


def dedupe(items):
    seen_url, kept, out = set(), [], []
    for i in items:
        u = i["url"].split("?")[0].rstrip("/")
        t = norm_title(i["title"])
        cand = {"norm": t, "words": set(t.split())}
        if u in seen_url or not cand["words"] or any(same_story(cand, k) for k in kept):
            continue
        seen_url.add(u)
        kept.append(cand)
        out.append(i)
    return out


# ---------- story clusters ----------

def story_words(title):
    return {w for w in norm_title(title).split() if (len(w) >= 3 or w.isdigit()) and w not in STOPWORDS}


def cluster_stories(items, threshold=0.25, min_outlets=3, limit=10):
    """Group headlines about the same event (e.g. 9 outlets on Thailand's ETF rules).

    Similarity is word overlap weighted by rarity (IDF): "Thailand" or "Securitize"
    identify a story, "bitcoin" barely does. 0.25 was tuned on real headlines:
    0.3 split stories in two, 0.2 started merging generic market round-ups.
    """
    W = [story_words(i["title"]) for i in items]
    n = len(items)
    df = Counter(w for ws in W for w in ws)
    idf = {w: math.log(n / c) for w, c in df.items()}
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    sim = {}
    for a in range(n):
        for b in range(a + 1, n):
            shared = W[a] & W[b]
            if len(shared) < 2:
                continue
            s_ab = sum(idf[w] for w in shared) / sum(idf[w] for w in W[a] | W[b])
            if s_ab >= threshold:
                sim[a, b] = s_ab
                parent[find(a)] = find(b)

    groups = defaultdict(list)
    for k in range(n):
        groups[find(k)].append(k)
    stories = []
    for members in groups.values():
        outlets = {items[k]["source"] for k in members}
        if len(outlets) < min_outlets:
            continue
        # Headline: the news (not Reddit) title most similar to the rest of its group.
        def centrality(k):
            return sum(sim.get((min(k, j), max(k, j)), 0) for j in members if j != k)
        best = max(members, key=lambda k: (items[k]["type"] == "news", centrality(k)))
        members.sort(key=lambda k: items[k]["published"] or "", reverse=True)
        stories.append({
            "title": items[best]["title"],
            "outlets": len(outlets),
            "topics": sorted({t for k in members for t in items[k]["topics"]}),
            "items": [{key: items[k][key] for key in ("title", "url", "source", "type", "published")}
                      for k in members],
        })
    stories.sort(key=lambda st: (st["outlets"], len(st["items"])), reverse=True)
    return stories[:limit]


# ---------- reddit heat (ticker mentions) ----------

TICKER_CACHE = DATA / "ticker_lists.json"
REDDIT_HISTORY = DATA / "reddit_history"
# Uppercase words that are valid tickers on paper but almost always mean something else in a title.
NOT_TICKERS = set("""
A I AI AM AN ARE AT BE BIG BY CAN CEO CFO CPI DD DM EPS ETF ETFS EU FED FOR FOMO FUD GDP GO HAS HE IF IMO IN IPO
IRS IS IT ITS LOL MOM NEW NFT NO NOW OF OK ON ONE OR OUT PM PT Q1 Q2 Q3 Q4 RE SEC SO TA THE TO UK UP US USA USD VS
WE YOLO ATH APY TVL DEX CEX USDT USDC AND ALL ANY BEST BUY SELL HOLD LONG PUT CALL OPEN NEXT WHO WHY HOW WHAT WHEN
TV EV OP REAL TIME TOP GOOD LOW HIGH JUST LIKE LSE NYSE ASH FDA JAN FEB MAR APR MAY JUN JUL AUG SEP SEPT OCT NOV DEC
MON TUE WED THU FRI SAT SUN
""".split())


def load_ticker_lists():
    """US stock symbols (Nasdaq Trader directory) + top-250 non-stablecoin coins (CoinGecko), cached for a week."""
    if TICKER_CACHE.exists() and NOW.timestamp() - TICKER_CACHE.stat().st_mtime < 7 * 86400:
        return json.loads(TICKER_CACHE.read_text())
    try:
        stocks = {}
        for f in ("nasdaqlisted", "otherlisted"):
            lines = http_get(f"https://www.nasdaqtrader.com/dynamic/SymDir/{f}.txt").decode().splitlines()
            hdr = lines[0].split("|")
            sym, name, test = hdr.index("Symbol" if "Symbol" in hdr else "ACT Symbol"), hdr.index("Security Name"), hdr.index("Test Issue")
            for ln in lines[1:]:
                p = ln.split("|")
                if len(p) > test and p[test] == "N":
                    stocks[p[sym]] = p[name].split(" - ")[0]
        api = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc"
        stable = {c["id"] for c in json.loads(http_get(api + "&category=stablecoins&per_page=100"))}
        top = [c for c in json.loads(http_get(api + "&per_page=250")) if c["id"] not in stable]
        lists = {"stocks": stocks,
                 "coins": {c["symbol"].upper(): c["name"] for c in top},
                 "coin_names": {c["name"].lower(): c["symbol"].upper() for c in top
                                if len(c["name"]) >= 5 and " " not in c["name"]}}
        TICKER_CACHE.write_text(json.dumps(lists))
        return lists
    except Exception as e:
        if TICKER_CACHE.exists():  # stale list beats no list
            print(f"  ticker lists: refresh failed ({e}), using cached copy")
            return json.loads(TICKER_CACHE.read_text())
        raise


def find_tickers(title, section, lists):
    """Cashtags ($NVDA) and uppercase symbols checked against the real lists; coin names for altcoins."""
    known = lists["coins"] if section == "Altcoins" else lists["stocks"]
    found = {t.upper() for t in re.findall(r"\$([A-Za-z]{1,6})\b", title) if t.upper() in known}
    found |= {t for t in re.findall(r"\b([A-Z]{2,6})\b", title) if t in known and t not in NOT_TICKERS}
    if section == "Altcoins":
        found |= {lists["coin_names"][w.lower()] for w in re.findall(r"\b([A-Z][a-z]{4,})\b", title)
                  if w.lower() in lists["coin_names"]}
        found.discard("BTC")  # altcoins = everything except Bitcoin
    return found


def reddit_heat(items, section, lists, limit=10):
    hits = defaultdict(list)
    for k, i in enumerate(items):
        for t in find_tickers(i["title"], section, lists):
            hits[t].append(k)
    known = lists["coins"] if section == "Altcoins" else lists["stocks"]
    heat = [{"ticker": t, "name": known.get(t, ""), "mentions": len(ks),
             "subs": len({items[k]["source"] for k in ks}), "posts": ks} for t, ks in hits.items()]
    heat.sort(key=lambda h: (h["mentions"], h["subs"]), reverse=True)
    return heat, {h["ticker"]: h["mentions"] for h in heat}


# ---------- trend detection ----------

def tokenize(title):
    words = re.findall(r"[A-Za-z0-9$][A-Za-z0-9$'\-\.]*[A-Za-z0-9]|[A-Za-z]", title)
    out = []
    for w in words:
        w = re.sub(r"'s$", "", w)
        low = w.lower()
        if len(low) < 3 or low in STOPWORDS or re.fullmatch(r"[\d\.\-$%,]+", low):
            out.append(None)  # break bigrams across stopwords
        else:
            out.append((low, w))
    return out


def is_title_case(title):
    words = [w for w in re.findall(r"[A-Za-z]{4,}", title)[1:]]
    return bool(words) and sum(w[0].isupper() for w in words) / len(words) >= 0.7


def extract_terms(items):
    """Count, per term, how many headlines mention it and from which sources.

    `caps` tracks, for sentence-case headlines only, how often a word is capitalised:
    that's how we tell names ("Solana") from ordinary words ("moves").
    """
    count, sources, forms = Counter(), defaultdict(set), defaultdict(Counter)
    by_type = defaultdict(Counter)
    caps = defaultdict(lambda: [0, 0])
    for i in items:
        toks = tokenize(i["title"])
        if not is_title_case(i["title"]):
            first = next((k for k, t in enumerate(toks) if t), None)
            for k, t in enumerate(toks):
                if t and k != first:  # first word is capitalised regardless
                    caps[t[0]][0] += t[1][0].isupper()
                    caps[t[0]][1] += 1
        terms = set()
        for idx, tok in enumerate(toks):
            if not tok:
                continue
            terms.add(tok[0])
            forms[tok[0]][tok[1]] += 1
            nxt = toks[idx + 1] if idx + 1 < len(toks) else None
            if nxt:
                bg = f"{tok[0]} {nxt[0]}"
                terms.add(bg)
                forms[bg][f"{tok[1]} {nxt[1]}"] += 1
        for t in terms:
            count[t] += 1
            sources[t].add(i["source"])
            by_type[t][i["type"]] += 1
    return count, sources, forms, caps, by_type


def looks_like_name(term, forms, caps):
    """Single words must be names/tickers; two-word phrases are specific enough already."""
    if " " in term:
        return True
    if any(f.isupper() and len(f) >= 2 for f in forms):  # ETF, SEC, XRP
        return True
    up, total = caps.get(term, (0, 0))
    return total > 0 and up / total >= 0.6


def load_baseline(days):
    totals, n = Counter(), 0
    for f in sorted(HISTORY.glob("terms-*.json"))[-days:]:
        if f.stem == f"terms-{NOW:%Y-%m-%d}":
            continue
        totals.update(json.loads(f.read_text()))
        n += 1
    return {t: c / n for t, c in totals.items()} if n else {}, n


def display_form(forms):
    """Prefer the capitalised spelling (e.g. 'BlackRock' over 'blackrock')."""
    best = max(forms.items(), key=lambda kv: (kv[1], sum(ch.isupper() for ch in kv[0])))[0]
    return best if any(ch.isupper() for ch in best) else best.title()


def detect_trends(pool, cfg, core_regexes):
    tc = cfg["trends"]
    count, sources, forms, caps, _ = extract_terms(pool)
    baseline, base_days = load_baseline(tc["baseline_days"])
    blocked = {b.lower() for b in tc["blocked"]}

    cands = []
    for term, c in count.items():
        if c < tc["min_mentions"] or len(sources[term]) < tc["min_sources"] or term in blocked:
            continue
        if not looks_like_name(term, forms[term], caps):
            continue
        name = display_form(forms[term])
        if any(matches(name, rs) for rs in core_regexes.values()):
            continue  # already a core keyword
        avg = baseline.get(term, 0.0)
        ratio = c / (avg + 1.0)
        # With little history, demand a stronger signal so common words don't sneak in.
        need = tc["min_ratio_vs_baseline"] if base_days >= 3 else tc["min_ratio_vs_baseline"] + 1
        if ratio < need:
            continue
        cands.append({"key": term, "term": name, "count": c, "sources": sorted(sources[term]),
                      "baseline": round(avg, 2), "ratio": round(ratio, 2)})

    # If a phrase ("Strategic Reserve") trends, drop its single words when they add little.
    keys = {c["key"]: c for c in cands}
    for c in list(cands):
        if " " in c["key"]:
            for w in c["key"].split():
                if w in keys and keys[w]["count"] <= c["count"] * 1.5:
                    keys.pop(w, None)
    cands = sorted(keys.values(), key=lambda c: (c["ratio"], c["count"]), reverse=True)

    # Persist today's counts as tomorrow's baseline (only terms seen at least twice, to stay small).
    HISTORY.mkdir(parents=True, exist_ok=True)
    (HISTORY / f"terms-{NOW:%Y-%m-%d}.json").write_text(
        json.dumps({t: c for t, c in count.items() if c >= 2}))
    return cands, base_days


def update_term_stats(state, items):
    """Running per-term counter (every term, not just keywords), for later signal-vs-noise analysis.

    Each headline is counted once, on the day it is first seen (`state["counted"]`), so
    overlapping fetch windows and several runs per day don't double-count.
    Per-day counts are [headlines, news, reddit]; totals are derived from them.
    """
    # Migration: before `counted` existed, today's run was already counted the old way; record, don't re-add.
    migrating = "counted" not in state and TERM_STATS.exists()
    counted = state.setdefault("counted", {})
    new = [i for i in items if i["url"].split("?")[0] not in counted]
    if migrating:
        for i in new:
            counted[i["url"].split("?")[0]] = NOW.isoformat()
        new = []
    for i in new:
        counted[i["url"].split("?")[0]] = NOW.isoformat()
    week_ago_iso = (NOW - timedelta(days=7)).isoformat()
    state["counted"] = {k: v for k, v in counted.items() if v >= week_ago_iso}

    stats = json.loads(TERM_STATS.read_text()) if TERM_STATS.exists() else {}
    today = NOW.strftime("%Y-%m-%d")
    count, _, forms, _, by_type = extract_terms(new)
    for term, c in count.items():
        entry = stats.setdefault(term, {"term": display_form(forms[term]), "daily": {}})
        t, n, r = entry["daily"].get(today, [0, 0, 0])
        entry["daily"][today] = [t + c, n + by_type[term]["news"], r + by_type[term]["reddit"]]
    week_ago = (NOW - timedelta(days=7)).strftime("%Y-%m-%d")
    for key in list(stats):
        e = stats[key]
        # One-off terms that never came back within a week are pure noise; drop them to keep the file small.
        if not e["daily"] or (e.get("total", 1) == 1 and max(e["daily"]) < week_ago):
            del stats[key]
            continue
        days = sorted(e["daily"])
        e.update(total=sum(d[0] for d in e["daily"].values()),
                 news=sum(d[1] for d in e["daily"].values()),
                 reddit=sum(d[2] for d in e["daily"].values()),
                 days_seen=len(days), first_seen=days[0], last_seen=days[-1])
    TERM_STATS.write_text(json.dumps(stats, separators=(",", ":")))
    return len(stats)


def update_tracked(state, cands, cfg):
    """Add new trends, refresh active ones, expire faded ones. Returns active trend list."""
    tc = cfg["trends"]
    tracked = state.setdefault("trends", {})
    today = NOW.strftime("%Y-%m-%d")
    for c in cands[: tc["max_active"]]:
        t = tracked.setdefault(c["key"], {"term": c["term"], "first_seen": today})
        t.update(last_trending=today, term=c["term"], count=c["count"], ratio=c["ratio"])
    blocked = {b.lower() for b in tc["blocked"]}
    cutoff = (NOW - timedelta(days=tc["expire_after_days"])).strftime("%Y-%m-%d")
    for key in list(tracked):
        if key in blocked or tracked[key]["last_trending"] < cutoff:
            del tracked[key]
    active = sorted(tracked.values(), key=lambda t: (t["last_trending"], t.get("ratio", 0)), reverse=True)
    return active[: tc["max_active"]]


# ---------- main ----------

def to_out(i, topics, first_seen):
    return {
        "title": i["title"],
        "url": i["url"],
        "source": i["source"],
        "type": i["type"],
        "published": i["published"].isoformat() if i["published"] else None,
        "first_seen": first_seen,
        "topics": topics,
    }


def main(mode):
    cfg = json.loads((ROOT / "config.json").read_text())
    DATA.mkdir(exist_ok=True)
    state_file = REDDIT_STATE if mode == "reddit" else STATE_FILE
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    first_run = "seen" not in state
    status = {}
    cutoff = NOW - timedelta(hours=cfg["settings"]["max_age_hours"])

    ex_sources = {x.lower() for x in cfg.get("exclude", {}).get("sources", [])}
    ex_titles = [re.compile(x, re.I) for x in cfg.get("exclude", {}).get("title_patterns", [])]

    def fresh(items):
        return [i for i in items
                if (i["published"] is None or i["published"] >= cutoff)
                and i["source"].lower() not in ex_sources
                and not any(r.search(i["title"]) for r in ex_titles)]

    if mode == "reddit":
        return run_reddit(cfg, state, fresh, status, first_run)

    print("Fetching news feeds…")
    news = fresh(fetch_news(cfg, status))

    # Trend detection runs on the broad pool only (not keyword searches), so a
    # trend can't keep itself alive just because we searched for it.
    pool = dedupe(news)
    core_regexes = {k: alias_regex(v) for k, v in cfg["keywords"].items()}
    print(f"Detecting trends across {len(pool)} headlines…")
    cands, base_days = detect_trends(pool, cfg, core_regexes)
    n_terms = update_term_stats(state, pool)
    active = update_tracked(state, cands, cfg)

    topics = [{"name": k, "kind": "core", "aliases": v} for k, v in cfg["keywords"].items()]
    pinned = {p.lower() for p in cfg["trends"]["pinned"]}
    for p in cfg["trends"]["pinned"]:
        topics.append({"name": p, "kind": "pinned", "aliases": [p]})
    for t in active:
        if t["term"].lower() not in pinned:
            topics.append({"name": t["term"], "kind": "trend", "aliases": [t["term"]],
                           "first_seen": t["first_seen"], "count": t.get("count"), "ratio": t.get("ratio")})

    print("Searching Google News per topic…")
    searched = []
    for tp in topics:
        searched += fetch_google_news(cfg, tp["name"], tp["aliases"], status, scoped=tp["kind"] != "core")
    all_items = dedupe(pool + fresh(searched))

    # Tag each headline with every topic it mentions; remember when we first saw it.
    seen = state.setdefault("seen", {})
    served = state.get("headlines_served", len(seen))  # odometer: unique headlines since day one
    regexes = {tp["name"]: alias_regex(tp["aliases"]) for tp in topics}
    out_items = []
    for i in all_items:
        tags = [name for name, rs in regexes.items() if matches(i["title"], rs)]
        if not tags:
            continue
        key = i["url"].split("?")[0]
        if key not in seen:
            served += 1
            seen[key] = NOW.isoformat()
        out_items.append(to_out(i, tags, seen[key]))
    week_ago = (NOW - timedelta(days=7)).isoformat()
    state["seen"] = {k: v for k, v in seen.items() if v >= week_ago}
    state["headlines_served"] = served

    out_items.sort(key=lambda i: i["published"] or i["first_seen"], reverse=True)
    for tp in topics:
        tp["item_count"] = sum(tp["name"] in i["topics"] for i in out_items)

    result = {
        "generated_at": NOW.isoformat(),
        "first_run": first_run,
        "topics": topics,
        "items": out_items,
        "stories": cluster_stories(out_items),
        "headlines_served": served,
        "trend_candidates": cands[:20],
        "baseline_days": base_days,
        "sources": status,
    }
    (DATA / "latest.json").write_text(json.dumps(result, indent=1))
    (DATA / "latest.js").write_text("window.DASHBOARD_DATA = " + json.dumps(result) + ";\n")
    STATE_FILE.write_text(json.dumps(state, indent=1))

    errors = {k: v for k, v in status.items() if v != "ok"}
    print(f"\nDone: {len(out_items)} headlines across {len(topics)} topics "
          f"({len(pool)} scanned for trends, {base_days} day(s) of trend history, "
          f"{n_terms} terms in the running counter).")
    for tp in topics:
        flag = {"core": "  ", "pinned": "📌", "trend": "🔥"}[tp["kind"]]
        print(f"  {flag} {tp['name']:<22} {tp['item_count']:>3}")
    if errors:
        print("\nSource problems:")
        for k, v in errors.items():
            print(f"  {k}: {v}")


def run_reddit(cfg, state, fresh, status, first_run):
    # One Reddit fetch at a time: two runs share the same rate limit and stall each other (seen 2026-10-10).
    lock = open(DATA / "reddit.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit("Another Reddit fetch is already running; skipping this one.")
    print("Fetching Reddit (paced to respect its rate limit)…")
    recurring = [re.compile(x, re.I) for x in cfg.get("reddit_exclude_titles", [])]
    posts = [i for i in dedupe(fresh(fetch_reddit(cfg, status)))
             if not any(r.search(i["title"]) for r in recurring)]
    n_terms = update_term_stats(state, posts)
    seen = state.setdefault("seen", {})
    for i in posts:
        seen.setdefault(i["url"].split("?")[0], NOW.isoformat())
    week_ago = (NOW - timedelta(days=7)).isoformat()
    state["seen"] = {k: v for k, v in seen.items() if v >= week_ago}

    lists = load_ticker_lists()
    sections, history = [], {}
    for name, subs in cfg["reddit_sections"].items():
        items = [{**to_out(i, [], seen[i["url"].split("?")[0]]), "section": name}
                 for i in posts if i["section"] == name]
        items.sort(key=lambda i: i["published"] or i["first_seen"], reverse=True)
        heat, history[name] = reddit_heat(items, name, lists)
        sections.append({"name": name, "subreddits": subs, "items": items, "heat": heat[:10]})
    # Daily mention counts, kept for a future "vs. normal level" comparison (later runs today replace it).
    REDDIT_HISTORY.mkdir(parents=True, exist_ok=True)
    (REDDIT_HISTORY / f"{NOW:%Y-%m-%d}.json").write_text(json.dumps(history))

    result = {"generated_at": NOW.isoformat(), "first_run": first_run,
              "sections": sections, "sources": status}
    (DATA / "reddit.json").write_text(json.dumps(result, indent=1))
    (DATA / "reddit.js").write_text("window.REDDIT_DATA = " + json.dumps(result) + ";\n")
    REDDIT_STATE.write_text(json.dumps(state, indent=1))

    print(f"\nDone: {len(posts)} posts ({n_terms} terms in the running counter).")
    for sec in sections:
        print(f"  {sec['name']:<10} {len(sec['items']):>4}")
    errors = {k: v for k, v in status.items() if v != "ok"}
    if errors:
        print("\nSource problems:")
        for k, v in errors.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "news")
