# Surface playbooks

Read only the sections for the surfaces your program uses. Each one lists what to rehearse with, what to probe, the failures to look for, and where to look first while scouting. The tools named are starting points, not a whitelist. Check that each is still maintained before using it.

No playbook matches? The rule still applies: find the real thing and poke it with the most direct tool you have.

## Web / HTTP (scrapers, API clients, webhooks)

- **Scout first**: the site's own API, RSS/Atom feed, `sitemap.xml`, data export, or the JSON its own pages load. Then `yt-dlp` (media), `trafilatura` (article text), `playwright` (JavaScript-rendered pages), `scrapy` (large crawls).
- **Rehearse with**: `curl` using the same method, headers, cookies and body the program will send. Use a browser tool only if the program will drive a browser.
- **Probe**: status code and headers (`curl -sI`), redirects (`-L -w '%{url_effective}'`), content type, encoding, and whether the data is in the raw HTML or loaded later by JavaScript (grep the raw response for a value you can see on the page), pagination (next link, cursor, page param; what the last page returns), robots.txt and terms.
- **Failures**: 403/429 (User-Agent, rate limit: check the `Retry-After` header), captcha or login wall, JavaScript-rendered content, different markup on different pages, missing fields, a 200 status with an error page as the body, timeouts.
- **Side effects**: GET is usually 🟢. POST/PUT/DELETE are 🟡 against a test account, 🔴 against real data.

## CLI / stdin (tools, scripts others will run)

- **Scout first**: an existing CLI that already does the job. Argument parsing: the standard library (`argparse`) or `click`/`typer`, `commander`.
- **Rehearse with**: run the underlying commands the tool will wrap, one at a time, and feed the real inputs.
- **Probe**: exit codes (`; echo $?`), what goes to stdout vs stderr, behavior with no args, bad args, piped input, non-interactive terminals.
- **Failures**: a missing binary or wrong version, locale/encoding, paths with spaces, a prompt that hangs when there's no TTY.
- **Side effects**: depends on the commands; label each one.

## Files (converters, parsers, backups)

- **Scout first**: `pandoc` (documents), `csvkit`, `miller`, `duckdb` (CSV and tabular data), `jq`/`yq` (JSON/YAML), `ffmpeg` (audio/video), ImageMagick (images), `pdftotext`/`ocrmypdf` (PDF), `rclone`/`rsync` (sync and backup).
- **Rehearse with**: `file`, `head`, `wc`, `iconv`, `jq`, `sqlite3`, `csvlook` or similar viewers on *real* sample files.
- **Probe**: encoding and BOM, delimiter and quoting, line endings, header row, empty or huge files, odd rows (look at the first, middle and last lines).
- **Failures**: mixed encodings, commas inside quotes, merged cells, dates in several formats, a file locked by another process, running out of disk.
- **Side effects**: reading is 🟢. Writing is 🟡 in a temp dir. Overwriting or deleting the user's files is 🔴.

## GUI / browser (web apps, desktop apps, UI automation)

- **Scout first**: Playwright (browser automation), the app's own API or CLI (often easier than driving its UI).
- **Rehearse with**: a browser automation tool (e.g. Playwright MCP), clicking and reading as a user would.
- **Probe**: selectors on real pages, load and wait states, modals and cookie banners, login flow, different viewport sizes.
- **Failures**: elements that load late, iframes, dynamic IDs, A/B variants, session expiry.
- **Side effects**: navigation is 🟢. Submitting forms is 🟡 or 🔴 depending on what they do.

## Database / state (anything that remembers)

- **Scout first**: SQLite before a server DB, `sqlite-utils`, `duckdb`, the framework's migration tool.
- **Rehearse with**: the DB's own CLI (`sqlite3`, `psql`, `redis-cli`) against a **copy** or a test database.
- **Probe**: the schema, a first run with no data, a second run with existing data, duplicates, what a half-finished write leaves behind.
- **Failures**: a missing table on first run, unique-constraint collisions on re-run, locks, migrations.
- **Side effects**: reads are 🟢. Writes to a test DB are 🟡. Writes to production are 🔴.

## Time (schedulers, retries, timeouts)

- **Scout first**: cron, systemd timers, or a CI schedule (e.g. GitHub Actions) instead of a sleep-loop daemon; `tenacity` or the HTTP client's built-in retry for retries.
- **Rehearse with**: run the job step twice in a row by hand to simulate two scheduled runs. Check the time zone (`date`, `TZ=`).
- **Probe**: what the second run does with the first run's output, overlapping runs, DST and time zones, clock skew.
- **Failures**: duplicate work, runs that overlap, a job that silently stops.
- **Side effects**: usually 🟢 by itself. Long-horizon behavior (days or weeks) is an **unverified risk**; say so in the report.

## External services (email, payments, LLM APIs, chat and social platforms)

- **Scout first**: the service's official SDK, `apprise` (one library for notifications to many services), or a no-code automation tool if the user doesn't need code.
- **Rehearse with**: the service's sandbox or test mode, or a test account. Use `curl` against its API with test credentials.
- **Probe**: authentication, the request and response shape, error format, rate limits, webhook payloads (from the docs or a test event).
- **Failures**: expired tokens, quota exhaustion, a schema that differs from the docs, messages landing in spam.
- **Side effects**: sending, paying, or posting to real people is always 🔴. Send only to the user themself, and only with their OK.

## Hardware / OS (devices, processes, system settings)

- **Scout first**: the vendor's SDK or CLI, `pyserial` (serial devices), an existing daemon that already exposes the device.
- **Rehearse with**: read-only queries first (`ls /dev`, `lsusb`, `systemctl status`, sensor reads).
- **Probe**: permissions, device names, and the real values sensors report (they drift and are offset; keep a calibration setting).
- **Failures**: permission denied, the device is missing or busy, a different OS or distro.
- **Side effects**: changing system state or moving actuators is 🔴 unless the user is watching.
