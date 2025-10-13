from collections import deque
import csv
import threading
import time
from src.helpers.DomainExtractor import CleanUrl, extract_domain
from protego import Protego

class QueueManager:

    def __init__(self):
        target_url = "https://wikipedia.org"

        # instantiate the queues
        self.__high_priority_queue = deque()
        self.__low_priority_queue = deque()
        self.__indexing_queue = deque()

        # create priority queues
        self.__high_priority_queue.append(target_url)
        self.__low_priority_queue.append(target_url)

        # Keep track of all seens urls to avoid duplicates
        self.__seen_lock = threading.Lock()
        self.__seen_urls = set()

        # Keep track of all visited domains to determine high and low priority urls
        self.__visited_lock = threading.Lock()
        self.__visited_domains = set()

        self.__robots_lock = threading.Lock()
        self.__robots_txt = dict[str, str]()
        
        self.__cooldowns_lock = threading.Lock()
        self.__cooldowns = dict[str, float]()

    def get_high_priority_url(self) -> str | None:
        try:
            return self.__high_priority_queue.pop()
        except IndexError:
            return None
    
    def get_low_priority_url(self) -> str | None:
        try:
            return self.__low_priority_queue.pop()
        except IndexError:
            return None
        
    def get_next_to_index(self) -> dict[str, list[str]] | None:
        try:
            return self.__indexing_queue.pop()
        except IndexError:
            return None
    
    def get_next_cooldown(self, domain: str, cooldown_time: float = 0) -> float:

        if(not cooldown_time): cooldown_time = 1.0

        with self.__cooldowns_lock:
            next_cooldown = self.__cooldowns.get(domain)
            if(not next_cooldown): next_cooldown = time.time()

            self.__cooldowns[domain] = next_cooldown + cooldown_time
            return next_cooldown - time.time() if next_cooldown > time.time() else 0.0
    
    def check_robots(self, domain: str) -> bool:
        text = self.__robots_txt.get(domain)
        if(not text): return False
        return True

    def get_robots(self, domain: str):
        text = self.__robots_txt.get(domain)
        if(not text): text = ''
        rp = Protego.parse(text)
        return rp
    
    def save_robots_txt(self, domain: str, text: str):
        with self.__robots_lock:
            self.__robots_txt[domain] = text
    
    def queue(self, urls: list[str]):
        for new_url in urls:
            new_url = CleanUrl(new_url)

            with self.__seen_lock:
                if(new_url in self.__seen_urls): continue
                self.__seen_urls.add(new_url)
            
            domain = extract_domain(new_url)
            with self.__visited_lock:
                if(not domain in self.__visited_domains): 
                    self.__visited_domains.add(domain)
                    self.__high_priority_queue.append(new_url)
                else: self.__low_priority_queue.append(new_url)

    def queue_index(self, url: str, title: str, description: str, outgoing: list[str], text: str):
        self.__indexing_queue.append({
            "url": [url],
            "title": [title],
            "description": [description],
            "outgoing": outgoing,
            "text": [text]
        })
    
    def save(self):
        # ...

        # save data to CSV
        csv_filename = "visited.csv"
        with open(csv_filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["Url"])
            writer.writeheader()
            for url in self.__visited_urls:
                writer.writerow({"Url": url})

        # save data to CSV
        csv_filename = "queue.csv"
        with open(csv_filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["Url"])
            writer.writeheader()
            while (
                not self.__high_priority_queue.empty() or not self.__low_priority_queue.empty()
            ):  
                # update the priority queue
                if not self.__high_priority_queue.empty():
                    current_url = self.__high_priority_queue.get()
                elif not self.__low_priority_queue.empty():
                    current_url = self.__low_priority_queue.get()
                else:
                    break
                writer.writerow({"Url": current_url})
    