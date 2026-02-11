# Auto.ria Scraper

## 🏗️ Architecture
This project uses **FastAPI** for the server layer.

### 📁 Project Structure

```text
app/
├── database/               # Data persistence & maintenance
│   └── database.py         # SQLAlchemy models, UPSERT logic, and Backup triggers
├── scraper/                # Core Scraping Engine
│   ├── scraper.py          # Async worker logic & queue management
│   └── car_card_parser.py  # BeautifulSoup logic for extracting car data
└── server/                 # API Layer (FastAPI)
    ├── server.py           # Endpoints, BackgroundTasks, and Lifespan (Scheduler)
    └── server_states.py    # Global state management (Scraper Lock)
```

## INstallation setup

1. Clone repository
```bash
git clone https://github.com/vitaleekbliz/TT_data-ox.git
```

2. Install Docker Desktop

3. Create .env file or run DCompose with -e flags for varibales

```python
POSTGRES_USER="my_user"
POSTGRES_PASSWORD="my_secure_password"
POSTGRES_DB="app_db"
DATABASE_URL="postgresql+asyncpg://my_user:my_secure_password@db:5432/app_db"
API_PORT="8000"
BASE_URL = "https://auto.ria.com/uk/search/?search_type=1&order=7&limit=100"
```

4. Install python dependencies (Optional, for code review and future development)

*Windows*
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
*Linux/Mac*
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

5. Starting docker containers

```bash
docker-compose up -d --build
```

## Usage 

You can use localhost:8000/docs for more convenient usage

![FastAPI docs](screenshots/API_docs.png)

### 📡 API Endpoints (Front-end for testing xD)

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/start_scraping` | `GET` | Starts the background scraper. Query params: `limit` (pages), `workers`. |
| `/health` | `GET` | Returns whether the server is currently running. |
| `/save_dump` | `GET` | Manually triggers a `.sql.gz` database backup to the `/dumps` folder. |

1. When you launch the server container it triggers auto- daily- database dumps in one minute(for test purposes).
Ps. Also you can trigger manual save using API method "save_dump"

![Scheduled Dumps](screenshots/daily_dumps_promt.png)

![Saved Dumps](screenshots/daily_dumps_server_files.png)

2. Start scraper using "start_scraping" method that has 2 optional parameters: amount of workers and limit serch pages to parse

![Scraper start](screenshots/scraper_start.png)

If scraper is already running, can't start another one (safety net)

![Scraper busy](screenshots/scraper_busy.png)

3. Wait till Scraper is finished (check logs or database)

Found 3156 pages to scrape.
Limiting pages for testing : 10
Queue filled with 1010 links. Starting 3 workers...
Successfully sent 50 cars to database upsert function (worker : 2).
Successfully saved 50 cars to database.
...
Successfully sent 41 cars to database upsert function (worker : 1).
Successfully saved 33 cars to database.
Successfully saved 41 cars to database.
Scraping Complete.

4. Use pgAdmin to view database:

![Database](screenshots/RESULT.PNG)

4.1 Use varibales from .env

Host name/address: Use db 
Port: 5432
Maintenance database: app_db
Username: my_user
Password: my_secure_password

4.2 Servers > Scraper DB > Databases > app_db > Schemas > public > Tables.
    Right-click on your cars table and select View/Edit Data > All Rows.