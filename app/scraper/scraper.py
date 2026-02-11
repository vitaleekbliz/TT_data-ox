import math
import os
import asyncio
import httpx
from bs4 import BeautifulSoup
from app.database.database import Car, upsert_cars
from app.scraper.car_card_parser import get_values_car_page
from app.server.server_states import Scraper_state
import asyncio
import random

BASE_URL = os.getenv("BASE_URL")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15"
]
WORKER_HEADERS = {
    #"User-Agent": random.choice(USER_AGENTS),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://auto.ria.com/"
}

class ScraperRetryWarning(UserWarning):
    pass

async def get_total_pages(client: httpx.AsyncClient):
    """Calculates how many pages we need to iterate through."""
    response = await client.get(f"{BASE_URL}&page=0")
    soup = BeautifulSoup(response.text, "html.parser")
    
    # find total count element
    count_element = soup.find("div", id="SortButtonContentCount")
    
    if not count_element:
        return 1
    
    #parse only digits
    total_cars = int(''.join(filter(str.isdigit, count_element.get_text())))
    return math.ceil(total_cars / 100)

async def scrape_page_for_links(page_num: int, client: httpx.AsyncClient, link_queue: asyncio.Queue, max_retries: int = 5, car_card_link_class:str = "link product-card horizontal"):
    """Finds all car links on a search results page."""
    url = f"{BASE_URL}&page={page_num}"
    retry_count = 0
    
    while retry_count < max_retries:
        response = await client.get(url)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.find_all("a", class_=car_card_link_class)
            
            for card in cards:
                link = card.get("href")
                if link:
                    full_link = f"https://auto.ria.com{link}"
                    await link_queue.put(full_link)
            
            # Successfully finished, exit the while loop
            return 

        # If we reach here, the status code was NOT 200
        retry_count += 1
        
        # 1. Throw the Warning
        #logger.warning(f"Retry needed for {url}. Status: {response.status_code}")
        
        # 2. Wait before trying again (Exponential Backoff)
        # Wait 1s, then 2s, then 4s...
        await asyncio.sleep(2 ** retry_count * 10)

async def process_car_page(link_queue: asyncio.Queue, worker_id:int, max_retries:int = 3, batch_size:int = 20):
    results_batch = []
    headers = WORKER_HEADERS
    headers["User-Agent"] = USER_AGENTS[worker_id % len(USER_AGENTS)]

    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        while not link_queue.empty():
            link = await link_queue.get()
            
            # --- RETRY LOGIC START ---
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    resp = await client.get(link)
                    
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        car = Car()
                        # Remember: Ensure this function uses car.url, not car.link!
                        get_values_car_page(soup, car, link) 
                        results_batch.append(car)
                        success = True
                        
                    elif resp.status_code == 429:
                        retry_count += 1
                        # Wait longer each time: 5s, 10s, 20s + a little random "jitter"
                        wait_time = (2 ** retry_count) * 2.5 + random.random()
                        print(f"Rate limited (429) on {link}. Retrying in {wait_time:.2f}s...")
                        await asyncio.sleep(wait_time)
                        
                    else:
                        print(f"Permanent Error {resp.status_code} for {link}")
                        break # Don't retry for 404s or other errors
                        
                except Exception as e:
                    retry_count += 1
                    print(f"Request failed ({e}). Retry {retry_count}/{max_retries}...")
                    await asyncio.sleep(2)
            # --- RETRY LOGIC END ---

            if len(results_batch) >= batch_size:
                await save_to_db(results_batch, worker_id)
                results_batch = []
            
            link_queue.task_done()
            
            # Anti-Ban: Small random sleep between requests to look more human
            await asyncio.sleep(random.uniform(0.5, 1.5))
        
        if results_batch:
            await save_to_db(results_batch, worker_id)

async def save_to_db(car_list:list[Car], worder_id:int):
    print(f"Successfully sent {len(car_list)} cars to database upsert function (worker : {worder_id}).")

    await upsert_cars(car_list)

    print(f"Successfully saved {len(car_list)} cars to database.")

async def start_scraping(state:Scraper_state, worker_amount:int = 3, limit_pages_to_scrap:int = 10000000):
    state.is_running = True
    link_queue = asyncio.Queue()
    headers = WORKER_HEADERS
    headers["User-Agent"] = random.choice(USER_AGENTS)

    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        # 1. Get total pages
        total_pages = await get_total_pages(client)
        print(f"Found {total_pages} pages to scrape.")

        print(f"Limiting pages for testing : {limit_pages_to_scrap}")
        total_pages = min(total_pages, limit_pages_to_scrap)

        # 2. Collect ALL links from all search pages concurrently
        search_tasks = [scrape_page_for_links(i, client, link_queue) for i in range(total_pages)]
        await asyncio.gather(*search_tasks)

    # 3. Start 5 workers to process the collected links in parallel
    print(f"Queue filled with {link_queue.qsize()} links. Starting {worker_amount} workers...")

    workers = [asyncio.create_task(process_car_page(link_queue, workerID)) for workerID in range(worker_amount)]
    
    await asyncio.gather(*workers)
    state.is_running = False
    print("Scraping Complete.")
