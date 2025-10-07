from queue import Queue
import threading
import csv
from bs4 import ResultSet, Tag

from src.helpers.DomainExtractor import ExtractDomain


class QueueManager:

    def __init__(self):
        target_url = "https://en.wikipedia.com"

        # instantiate the queues
        self.__high_priority_queue = Queue()
        self.__low_priority_queue = Queue()

        # create priority queues
        self.__high_priority_queue.put(target_url)
        self.__low_priority_queue.put(target_url)

        self.__visited_urls = set()
        self.__visited_lock = threading.Lock()

        # Domains we have visited before and must apply a cooldown
        self.__domain_cooldowns = set()


    def getUrl(self) -> str | None:
        # update the priority queue
        if not self.__high_priority_queue.empty():
            current_url = self.__high_priority_queue.get_nowait()
        elif not self.__low_priority_queue.empty():
            current_url = self.__low_priority_queue.get_nowait()
        else:
           return

        if current_url in self.__visited_urls:
            return
        self.__visited_urls.add(current_url)

        return current_url
    
    def inCooldown(self, current_url: str) -> bool:
        return ExtractDomain(current_url) in self.__domain_cooldowns
    
    def getQueueSize(self):
        return self.__high_priority_queue.qsize() + self.__low_priority_queue.qsize()
    
    def queue(self, links: ResultSet[Tag]):
        ulrs: list[str] = []

        for link_element in links:
            new_url = link_element["href"]

            if(not new_url.startswith('http')): continue

            ulrs.append(new_url)

        
        for new_url in ulrs:
            if(not new_url in self.__visited_urls): 
                domain = ExtractDomain(new_url)
                if(not domain in self.__domain_cooldowns): 
                    self.__domain_cooldowns.add(domain)
                    self.__high_priority_queue.put(new_url)
                else: self.__low_priority_queue.put(new_url)

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
    