# Market Brief

**Live:** https://leomadori.github.io/market-brief/

A personal, late-90s-style dashboard of market and crypto news and Reddit chatter. Instead of checking news sites, Reddit and YouTube separately, everything relevant lands in one place. Two pages, linked by a "Go to" menu at the top:

## Market Brief (news)

Updated at 10:00 and 18:00.

- **Topics:** Stablecoin, RWA (real-world assets / tokenization), Ethereum and Bitcoin, each in its own column.
- **🔥 Trends:** terms that suddenly show up much more than usual (e.g. *Solana*, *OpenAI*) are detected automatically, get their own column, and fade after a few quiet days.
- **Top stories:** the same event covered by several outlets is grouped into one story, ranked by how many outlets cover it.
- **Price ticker:** a scrolling retro bar with the top 20 cryptocurrencies by market cap (stablecoins excluded) and their 24h change, loaded live from CoinGecko.
- **Fear & Greed:** the daily Crypto Fear & Greed Index (Alternative.me) as a slider and a number.
- **Pull-quote:** the day's strongest trend.
- **Headlines served:** an odometer counting every unique headline collected since day one.
- Search, and **bold = new today**.

## Reddit Boiling Point

Updated at 08:00, 14:00 and 20:00. Shows what Reddit is talking about, split into **Altcoins** and **Stocks**.

- **Heat ranking:** the most-mentioned tickers per section (e.g. `$NVDA`, `MU`, "Solana"), with how many subreddits mention them. Click a ticker to see the posts.
- Tickers are checked against real lists (US-listed stocks from Nasdaq's symbol directory, top 250 coins from CoinGecko), so words like "CEO" or "YOLO" don't count. Bitcoin is excluded from Altcoins.
- Recurring threads (daily discussions, weekly megathreads) are filtered out.
- This is a measure of attention, not a recommendation.

## Where the headlines come from

- **News:** CoinDesk, Cointelegraph, The Block, Decrypt, Bitcoin Magazine, CNBC, MarketWatch, plus Google News search per topic.
- **Reddit (Boiling Point page):** Altcoins: r/CryptoCurrency, r/altcoin, r/SatoshiStreetBets, r/solana, r/defi. Stocks: r/wallstreetbets, r/stocks, r/investing, r/pennystocks, r/StockMarket, r/options.

Only headlines and links are shown. Every headline links to the original article.

## How it works

A small Python script (standard library only) runs on a schedule: it fetches the feeds, drops duplicates and spam, tags headlines by topic, detects trends and tickers, groups stories, and publishes these static pages to GitHub Pages. The script is [`fetch.py`](fetch.py) (read-only: it never posts, votes or stores user data). This repository contains the script, the published page and today's data; settings and history stay local.

## Changelog

- **2026-10-10:** Reddit Boiling Point page (Altcoins / Stocks, ticker heat ranking, newest + hot posts, recurring threads filtered); Market Brief is now news-only; "Go to" menu; news updates twice a day, Reddit three times; term counter counts each headline once.
- **2026-10-10:** Live price ticker (top 20 coins, no stablecoins) and Fear & Greed gauge; README added; headline-counter layout fix on medium screens.
- **2026-10-10:** Pixel-orange icon for the browser tab and home screen.
- **2026-10-09:** First version: topics, trend detection, Reddit + news sources, retro design, top stories, duplicate filtering, headline odometer, mobile home-screen support.

---

*Headlines are aggregated automatically. Not financial advice.*
*Image: still from* A Clockwork Orange *(1971), © Warner Bros., used for decoration only.*
