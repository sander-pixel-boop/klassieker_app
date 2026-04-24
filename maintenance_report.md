# Maintenance Report: Auto-Scraper Investigation

## Task
Investigate the feasibility of building an "auto scraper for all the race results and startlists" to replace the manual uploading of `uitslagen.csv` and `bron_startlijsten.csv`.

## Findings
Extensive testing with `requests`, `cloudscraper`, `undetected-chromedriver`, and Playwright confirmed that the primary cycling data providers (ProCyclingStats, FirstCycling) employ strict Cloudflare anti-bot protection that consistently returns `403 Forbidden` for automated traffic.

Secondary news sites (Wielerflits, CyclingNews) either do not have standardized parseable HTML tables for all startlists and results or return 404s for expected API endpoints. Wikipedia provides easy-to-parse HTML tables for top-10 results but lacks complete startlists and naming consistency.

## Conclusion
Due to the Cloudflare restrictions, direct scraping is not feasible without a paid proxy service. The user was consulted and decided to "never mind I'll do it manually," effectively aborting the request. No code changes were merged.
