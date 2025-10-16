from collections import deque
import csv
import json
import threading
import time
from src.helpers.DomainExtractor import CleanUrl, extract_domain
from protego import Protego
import redis

class QueueManager:

    def __init__(self):
        target_url = "https://wikipedia.org"
        self.r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

        # create priority queues
        self.r.lpush('high_priority_queue', target_url)
        self.r.lpush('low_priority_queue', target_url)

        # Keep track of all seens urls to avoid duplicates
        self.__seen_lock = threading.Lock()

        # Keep track of all visited domains to determine high and low priority urls
        self.__visited_lock = threading.Lock()
        
        self.__cooldowns_lock = threading.Lock()

        self.interrupted = False

    def get_high_priority_url(self, count: int = 1) -> str | list[str] | None:
        try:
            return self.r.rpop('high_priority_queue', count=count)
        except Exception as e:
            print(e)
            return None
    
    def get_low_priority_url(self, count: int = 1) -> str | list[str] | None:
        try:
            return self.r.rpop('low_priority_queue', count=count)
        except Exception as e:
            print(e)
            return None
        
    def get_next_to_index(self, count: int = 1) -> list[dict[str, list[str]]] | dict[str, list[str]] | None:
        try:
            results = self.r.rpop('indexing_queue', count=count)

            if(not results): return None

            if(count > 1):
                index_list: list[dict[str, list[str]]] = []
                for item in results:
                    index_list.append(json.loads(item))
                return index_list
            
            return json.loads(results)
        except Exception as e:
            print(e)
            return None
    
    def get_next_cooldown(self, domain: str, cooldown_time: float = 0) -> float:

        if(not cooldown_time): cooldown_time = 2.0

        with self.__cooldowns_lock:
            next_cooldown = self.r.get(f"domain:{domain}")
            if(not next_cooldown or float(next_cooldown) < time.time()): next_cooldown = time.time()
            else: next_cooldown = float(next_cooldown)

            self.r.set(f"domain:{domain}", json.dumps(next_cooldown + cooldown_time))
            return next_cooldown - time.time() if next_cooldown > time.time() else 0.0
    
    def check_robots(self, domain: str) -> bool:
        try:
            return not self.r.exists(f"robots:{domain}") == 0
        except Exception as e:
            print(e)

    def get_robots(self, domain: str):
        text = self.r.get(f"robots:{domain}")
        if(not text): text = ''
        rp = Protego.parse(text)
        return rp
    
    def save_robots_txt(self, domain: str, text: str):
        try:
            self.r.set(f"robots:{domain}", text)
        except Exception as e:
            print(e)
    
    def queue(self, urls: list[str]):
        for new_url in urls:
            new_url = CleanUrl(new_url)

            with self.__seen_lock:
                if(self.r.sismember("seen_urls", new_url)): continue
                self.r.sadd("seen_urls", new_url)
            
            domain = extract_domain(new_url)
            with self.__visited_lock:
                if(self.r.exists(f"domain:{domain}") == 0):
                    self.r.set(f"domain:{domain}", json.dumps(time.time()))

                    self.r.lpush('high_priority_queue', new_url)
                else: self.r.lpush('low_priority_queue', new_url)

    def queue_index(self, url: str, title: str, description: str, outgoing: list[str], text: str):
        self.r.lpush('indexing_queue', json.dumps({
            "url": [url],
            "title": [title],
            "description": [description],
            "outgoing": outgoing,
            "text": [text]
        }))
    
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
    