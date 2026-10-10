# Market Brief

**Live:** https://leomadori.github.io/market-brief/

A personal, late-90s-style dashboard of market and crypto headlines, updated once a day. Instead of checking news sites, Reddit and YouTube separately, everything relevant lands on one page.

## What's on the page

- **Topics:** Stablecoin, RWA (real-world assets / tokenization), Ethereum and Bitcoin, each in its own column.
- **🔥 Trends:** terms that suddenly show up much more than usual (e.g. *Solana*, *OpenAI*) are detected automatically, get their own column, and fade after a few quiet days.
- **Top stories:** the same event covered by several outlets is grouped into one story, ranked by how many outlets cover it.
- **Price ticker:** a scrolling retro bar with the top 20 cryptocurrencies by market cap (stablecoins excluded) and their 24h change, loaded live from CoinGecko.
- **Fear & Greed:** the daily Crypto Fear & Greed Index (Alternative.me) as a slider and a number.
- **Pull-quote:** the day's strongest trend.
- **Headlines served:** an odometer counting every unique headline collected since day one.
- Filters for News / Reddit, search, and **bold = new today**.

## Where the headlines come from

- **News:** CoinDesk, Cointelegraph, The Block, Decrypt, Bitcoin Magazine, CNBC, MarketWatch, plus Google News search per topic.
- **Reddit:** r/wallstreetbets, r/CryptoCurrency, r/Bitcoin, r/ethereum, r/stocks, r/investing.

Only headlines and links are shown. Every headline links to the original article.

## How it works

A small Python script (standard library only) runs every morning: it fetches the feeds, drops duplicates and spam, tags headlines by topic, detects trends, groups stories, and publishes this static page to GitHub Pages. This repository only contains the published page and today's data.

## Changelog

- **2026-10-10:** Live price ticker (top 20 coins, no stablecoins) and Fear & Greed gauge; README added; headline-counter layout fix on medium screens.
- **2026-10-10:** Pixel-orange icon for the browser tab and home screen.
- **2026-10-09:** First version: topics, trend detection, Reddit + news sources, retro design, top stories, duplicate filtering, headline odometer, mobile home-screen support.

---

*Headlines are aggregated automatically. Not financial advice.*
*Image: still from* A Clockwork Orange *(1971), © Warner Bros., used for decoration only.*
