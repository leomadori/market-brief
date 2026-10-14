# Market Brief

**Live:** https://leomadori.github.io/market-brief/

A personal, late-90s-style dashboard of market and crypto news and Reddit chatter. Instead of checking news sites, Reddit and YouTube separately, everything relevant lands in one place. Two pages, linked by a "Go to" menu at the top:

## Market Brief (news)

Updated at 08:00, 13:00 and 18:00 (Central European Time). Headlines older than 24 hours are hidden.

- **Topics:** Stablecoin, RWA (real-world assets / tokenization), Ethereum, Bitcoin and DEFI (decentralized finance), each in its own column.
- **🔥 Trends:** terms that suddenly show up much more than usual (e.g. *Solana*, *OpenAI*) are detected automatically, get their own column, and fade after a few quiet days. Trends covering the same story or the same word are merged into one.
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
- **Reddit (Boiling Point page):** Altcoins: r/CryptoCurrency, r/CryptoMarkets, r/solana, r/defi. Stocks: r/wallstreetbets, r/stocks, r/investing, r/pennystocks, r/StockMarket, r/options.

Only headlines and links are shown. Every headline links to the original article.

## How it works

A small Python script (standard library only) runs on a schedule: it fetches the feeds, drops duplicates and spam, tags headlines by topic, detects trends and tickers, groups stories, and publishes these static pages to GitHub Pages. The script is [`fetch.py`](fetch.py) (read-only: it never posts, votes or stores user data). This repository contains the script, the published page and today's data; settings and history stay local.

## Changelog

- **2026-10-14:** Duplicate trends merged: trends sharing most of their headlines become one tab (Blur + NFT), and word variants are combined (Korea + Korean).
- **2026-10-14:** The background term counter now records how many headlines it counted each day and a log of method changes, so long-term comparisons use shares instead of raw counts.
- **2026-10-14:** Off-topic headlines filtered: Google News searches for the core topics now require crypto context ("RWA" was also matching Rwanda cricket, Indian resident associations and a stock ticker). "Price data" quote pages blocked.
- **2026-10-12:** Windows 95-style scrollbar; news updates three times a day (08:00, 13:00, 18:00) with the times shown on the page; headlines hide automatically once they pass 24 hours.
- **2026-10-12:** New DEFI topic. Trend detection now also uses Google News results for the core topics (more headlines to spot trends in) and compares each term's share of headlines with previous days.
- **2026-10-12:** Market Brief shows only news from the last 24 hours.
- **2026-10-12:** "Can you dig it?" GIF under the update time (stored in the repo, served as a 355 KB animated WebP).
- **2026-10-12:** Market Brief morning update moved from 10:00 to 08:00. If most sources fail (e.g. no internet), the update is skipped and the previous page stays live.
- **2026-10-10:** Reddit sources tuned (inactive r/SatoshiStreetBets and r/altcoin replaced by r/CryptoMarkets); safeguards so a slow Reddit run can't hang.
- **2026-10-10:** Reddit Boiling Point page (Altcoins / Stocks, ticker heat ranking, recurring threads filtered); Market Brief is now news-only; "Go to" menu; news updates twice a day, Reddit three times; term counter counts each headline once.
- **2026-10-10:** Live price ticker (top 20 coins, no stablecoins) and Fear & Greed gauge; README added; headline-counter layout fix on medium screens.
- **2026-10-10:** Pixel-orange icon for the browser tab and home screen.
- **2026-10-09:** First version: topics, trend detection, Reddit + news sources, retro design, top stories, duplicate filtering, headline odometer, mobile home-screen support.

---

*Headlines are aggregated automatically. Not financial advice.*
*Image: still from* A Clockwork Orange *(1971), © Warner Bros., used for decoration only. GIF:* The Warriors *(1979), originally from Tenor, stored here.*
