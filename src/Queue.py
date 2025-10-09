from collections import deque
import csv
import threading
from src.helpers.DomainExtractor import CleanUrl, ExtractDomain
from protego import Protego

class QueueManager:

    def __init__(self):
        target_url = "https://github.com"

        # instantiate the queues
        self.__high_priority_queue = deque()
        self.__low_priority_queue = deque()

        # create priority queues
        self.__high_priority_queue.append(target_url)
        self.__low_priority_queue.append(target_url)

        self.__seen_urls = set()

        # Domains we have visited before and must apply a cooldown
        self.__visited_domains = set()

        self.__robots_lock = threading.Lock()
        self.__robots_txt = dict[str, str]

    def getHighPriorityUrl(self) -> str | None:
        return self.__high_priority_queue.pop()
    
    def getLowPriorityUrl(self) -> str | None:
        return self.__low_priority_queue.pop()
    
    def inCooldown(self, current_url: str) -> bool:
        return ExtractDomain(current_url) in self.__visited_domains
    
    def checkRobots(self, url: str):
        text = self.__robots_txt.get(url)
        if(not text): return
        rp = Protego.parse(text)
        return rp
    
    def saveRobotsTxt(self, url: str, text: str):
        with self.__robots_lock:
            self.__robots_txt[url] = text
    
    def queue(self, urls: list[str]):
        for new_url in urls:
            new_url = CleanUrl(new_url)
            if(not new_url in self.__seen_urls):
                domain = ExtractDomain(new_url)
                if(not domain in self.__visited_domains): 
                    self.__visited_domains.add(domain)
                    self.__high_priority_queue.append(new_url)
                else: self.__low_priority_queue.append(new_url)
    
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
    