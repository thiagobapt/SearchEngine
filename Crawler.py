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

session = req.Session()

MAX_CRAWLS = 200

def my_failure_callback(retry_state):
    """
    This callback is executed when all retries are exhausted and the function
    still fails.
    """
    print(f"All retries failed after {retry_state.attempt_number} attempts.")
    print(f"Last exception: {retry_state.outcome.exception()}")
    # You can log the error, send notifications, or perform other actions here.
    return None # Or raise a custom exception, or return a default value

@retry(
    stop=stop_after_attempt(4),  # maximum number of retries
    wait=wait_exponential(multiplier=2, min=2, max=3),  # exponential backoff
    retry_error_callback=my_failure_callback
)
def fetch_url(url):
    response = session.get(url, headers=headers)
    return response

def crawl():
    
    crawled = 0
    while (
        not high_priority_queue.empty() or not low_priority_queue.empty()
    ) and crawled < MAX_CRAWLS:

        # update the priority queue
        if not high_priority_queue.empty():
            current_url = high_priority_queue.get()
        elif not low_priority_queue.empty():
            current_url = low_priority_queue.get()
        else:
           break

        with visited_lock:
            if current_url in visited_urls:
                continue

        crawled += 1
        with visited_lock:
            visited_urls.add(current_url)

        sleep_time = 0.05

        if(ExtractDomain(current_url) in domain_cooldowns): time.sleep(sleep_time)

        response = fetch_url(current_url)

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


num_workers = 5
threads = []

def tracker():
    while True:
        clear_screen()
        print(f"Visited: {len(visited_urls)} || In queue: {high_priority_queue.qsize() + low_priority_queue.qsize()}")
        time.sleep(0.5)

# start worker threads
for _ in range(num_workers):
    thread = threading.Thread(target=crawl, daemon=True)
    threads.append(thread)
    thread.start()

thread = threading.Thread(target=tracker, daemon=True)
thread.start()

# wait for all threads to finish
for thread in threads:
    thread.join()

import csv

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