import requests as req
from bs4 import BeautifulSoup
from helpers.ClearCmd import clear_screen
from helpers.DomainExtractor import ExtractDomain
import time
from tenacity import retry, stop_after_attempt, wait_exponential
import threading
from queue import Queue

target_url = "https://en.wikipedia.org"

headers = {'User-Agent': 'NoAICrawler/0.0 (https://example.org/coolbot/; coolbot@example.org)'}

# instantiate the queues
high_priority_queue = Queue()
low_priority_queue = Queue()

# create priority queues
high_priority_queue.put(target_url)
low_priority_queue.put(target_url)

visited_urls = set()
visited_lock = threading.Lock()

# Domains we have visited before and must apply a cooldown
domain_cooldowns = set()

req_times = []

MAX_CRAWLS = 200

def fetch_error(retry_state):
    print(f"All retries failed after {retry_state.attempt_number} attempts.")
    print(f"Last exception: {retry_state.outcome.exception()}")
    return None # Or raise a custom exception, or return a default value

@retry(
    stop=stop_after_attempt(4),  # maximum number of retries
    wait=wait_exponential(multiplier=2, min=2, max=3),  # exponential backoff
    retry_error_callback=fetch_error
)
def fetch_url(url: str, session: req.Session, id: int):
    print(f'Id: {id} | fetching: {url}')
    response = session.get(url, headers=headers,timeout= 1)
    return response

def crawl(thread_id: int, session: req.Session):
    print(f'{thread_id} starting')
    

    crawled = 0
    while crawled < MAX_CRAWLS:
        # update the priority queue
        if not high_priority_queue.empty():
            current_url = high_priority_queue.get()
        elif not low_priority_queue.empty():
            current_url = low_priority_queue.get()
        else:
           time.sleep(1)
           continue

        with visited_lock:
            if current_url in visited_urls:
                continue

        crawled += 1
        with visited_lock:
            visited_urls.add(current_url)

        sleep_time = 0.05
        print('domain: ', ExtractDomain(current_url))
        if(ExtractDomain(current_url) in domain_cooldowns): time.sleep(sleep_time)

        response = fetch_url(current_url, session, thread_id)

        if(response == None or response.status_code != 200): continue

        soup = BeautifulSoup(response.text, "html.parser")

        links = soup.select('a[href]')

        for link_element in links:
            new_url = link_element["href"]

            if(not new_url.startswith('http')): continue

            domain = ExtractDomain(new_url)

            with visited_lock:
                if(not new_url in visited_urls): 
                    if(not domain in domain_cooldowns): 
                        domain_cooldowns.add(domain)
                        high_priority_queue.put(new_url)
                    else: low_priority_queue.put(new_url)
    
    print(f'{thread_id} closing')


num_workers = 50
threads = []

# start worker threads
for i in range(num_workers):
    session = req.Session()
    thread = threading.Thread(target=crawl, daemon=True, args=[i, session])
    threads.append(thread)
    thread.start()

import csv

def save():
    # ...

    # save data to CSV
    csv_filename = "visited.csv"
    with open(csv_filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["Url"])
        writer.writeheader()
        for url in visited_urls:
            writer.writerow({"Url": url})

    # save data to CSV
    csv_filename = "queue.csv"
    with open(csv_filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["Url"])
        writer.writeheader()
        while (
            not high_priority_queue.empty() or not low_priority_queue.empty()
        ):  
            # update the priority queue
            if not high_priority_queue.empty():
                current_url = high_priority_queue.get()
            elif not low_priority_queue.empty():
                current_url = low_priority_queue.get()
            else:
                break
            writer.writerow({"Url": current_url})

import atexit

def exit_handler():
    print('Exiting...')
    save()

atexit.register(exit_handler)

while True:
    time.sleep(1)