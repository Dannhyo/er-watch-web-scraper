# ER Watch Scraper
[![Run My Scraper](https://github.com/ahmaad-ansari/er-watch-scraper/actions/workflows/scraper.yml/badge.svg)](https://github.com/ahmaad-ansari/er-watch-scraper/actions/workflows/scraper.yml)

**ER Watch Scraper** is an async web scraping system that collects real-time emergency room wait times from hospitals across Ontario. It supports multiple data sources including REST APIs, HTML pages, and Power BI dashboards, storing results in a PostgreSQL database.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Setup & Installation](#setup--installation)
5. [Database Migrations](#database-migrations)
6. [Usage](#usage)
7. [Run Summary & Failure Notifications](#run-summary--failure-notifications)
8. [Environment Variables](#environment-variables)
9. [Extending the Project](#extending-the-project)
10. [License](#license)

---

## Overview

### Key Goals

- **Real-Time Data**: Collects the latest ER wait times from multiple sources every 15 minutes.
- **Async Concurrent Execution**: Uses `asyncio` and `aiohttp` for fast parallel scraping.
- **Clear Failure Notifications**: Detailed run summaries show exactly which hospitals failed and why.
- **Reliable Persistence**: Stores scraped data in PostgreSQL with an UPSERT pattern.
- **Maintainable Architecture**: Organized into logical modules (Scrapers, Parsers, Repository, Utils).

---

## Features

- **Async HTTP Client**: Shared `aiohttp` session with connection pooling for efficient requests
- **Concurrent Scraping**: Configurable concurrency limits per scraper type (API: 20, HTML: 20, PBI: 3)
- **Retry Logic**: Exponential backoff with configurable retries for failed requests
- **Detailed Logging**: Hospital ID context in all log messages for easy debugging
- **Run Summary**: After each run, displays success/failure counts and detailed error information
- **Database Migrations**: Alembic-based schema management

---

## Project Structure

```
er-watch-scraper/
├── scraper/
│   ├── __init__.py
│   ├── main.py                 # Entry point - orchestrates scraping and displays run summary
│   ├── aggregator.py           # Concurrent execution with failure tracking
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py       # SQLAlchemy async database connection
│   │   └── models.py           # SQLAlchemy ORM models
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base_parser.py
│   │   ├── api_parser.py       # JSON/text API response parser
│   │   └── html_parser.py      # BeautifulSoup HTML parser
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base_scraper.py     # Abstract base class with common logic
│   │   ├── api_scraper.py      # Async API scraper using aiohttp
│   │   ├── html_scraper.py     # Async HTML scraper using aiohttp
│   │   └── pbi_scraper.py      # Power BI scraper using Playwright
│   ├── repository/
│   │   ├── __init__.py
│   │   └── supabase_repository.py  # Database operations (UPSERT)
│   └── utils/
│       ├── __init__.py
│       ├── logger.py           # Color-coded logger with hospital context
│       ├── data_formatter.py   # Value normalization (dates, times, integers)
│       ├── field_mappings.py   # Centralized field name mappings
│       ├── retry.py            # Async retry with exponential backoff
│       └── http_client.py      # Shared aiohttp session management
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 20250126_000000_initial_schema.py
├── data/                       # Private - scraping target CSV files (gitignored)
├── alembic.ini
├── requirements.txt
├── .env
└── README.md
```

---

## Setup & Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/ahmaad-ansari/er-watch-scraper.git
   cd er-watch-scraper
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright Browsers** (for Power BI scraping)
   ```bash
   playwright install chromium
   ```

5. **Configure Environment Variables**
   Create a `.env` file in the project root:
   ```
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=your_db_name
   ```

---

## Database Migrations

This project uses Alembic for database schema management.

**Run migrations:**
```bash
alembic upgrade head
```

**Create a new migration:**
```bash
alembic revision --autogenerate -m "Description of changes"
```

**Check current migration status:**
```bash
alembic current
```

---

## Usage

**Run the scraper:**
```bash
python -m scraper.main
```

The script will:
1. Retrieve scraping targets from the database
2. Concurrently scrape all targets using the appropriate scraper (API, HTML, PBI)
3. Parse and format the data
4. Save results to the database via UPSERT
5. Display a run summary with success/failure statistics

---

## Run Summary & Failure Notifications

After each run, a detailed summary is displayed:

```
============================================================
                    SCRAPER RUN SUMMARY
============================================================
Total hospitals: 42
Successful: 38 (90.5%)
Failed: 4 (9.5%)

FAILED HOSPITALS:
------------------------------------------------------------
Hospital ID: OHC15
Action: pbi
URL: https://app.powerbi.com/view?r=...
Error: Selector failed for 'estimatedWaitTime'
       selectorSequence: [{"tag": "tspan", "nthOfType": 7}]
       No element found matching selector

Hospital ID: OHT14
Action: html
URL: https://www.hospital.ca/emergency
Error: HTTP 503 Service Unavailable
============================================================
```

This tells you exactly:
- Which hospital failed
- What type of scraper was used
- The URL that was scraped
- The specific error that occurred

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DB_USER` | PostgreSQL username |
| `DB_PASSWORD` | PostgreSQL password |
| `DB_HOST` | Database host address |
| `DB_PORT` | Database port (default: 5432) |
| `DB_NAME` | Database name |

---

## Extending the Project

### Add a New Scraper

1. Create a new file in `scraper/scrapers/` inheriting from `BaseScraper`
2. Implement the async `scrape()` method
3. Update `aggregator.py` to handle the new action type

### Add a New Hospital

1. Add a row to the `scraping_targets` table with:
   - `hospital_id`: Unique identifier
   - `url`: Target URL
   - `action`: Scraper type (see below)
   - `scraping_instructions`: JSON object with field extraction rules

### Action Types

| Action | Description | Use Case |
|--------|-------------|----------|
| `api` | Async HTTP request with aiohttp | Standard JSON/text APIs |
| `api_h` | Headless browser (Playwright) + JSON parsing | APIs protected by Cloudflare/bot detection |
| `html` | Async HTTP request + BeautifulSoup parsing | Static HTML pages |
| `pbi` | Headless browser + HTML parsing | Power BI dashboards |
| `pbi_h` | Headless browser with headers + HTML parsing | Protected dynamic pages |

### Scraping Instructions Format

```json
{
  "lastUpdated": {
    "unit": "EST",
    "pattern": "(regex pattern)",
    "formatCode": "%Y-%m-%d %H:%M:%S",
    "dataPath": "path.to.field",           // For API
    "selectorSequence": [{"tag": "div"}]   // For HTML
  },
  "patientsWaiting": {
    "dataPath": "patients.waiting"
  },
  "estimatedWaitTime": {
    "unit": "minutes",
    "pattern": "(\\d+)",
    "dataPath": "wait.time"
  }
}
```

---

## License

This project does not currently specify a license. For more information or if you wish to use this in a commercial or open-source context, please contact the repository owner.

---

**Thank you for using ER Watch!**
If you encounter any issues or have suggestions, please open an issue or submit a pull request.
