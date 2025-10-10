import asyncio
import csv
import threading
import time
from pymongo import MongoClient
from src.Crawler import Crawler
from src.Queue import QueueManager
from src.Indexer import Indexer

class Workers:
    def __init__(self):
        self.__manager = QueueManager()
        self.__indexer = Indexer(MongoClient("mongodb://localhost:27017/"))

    def new_worker(self, high_priority: bool):
        crawler = Crawler(self.__indexer, high_priority=high_priority, max_concurrent=30)

        asyncio.run(crawler.crawl(self.__manager))

    def start(self, max_workers: int):
        # Minimum of 2 workers is needed, one for high priority and one for low
        if(max_workers < 2): max_workers = 2

        # Start threads for each link
        threads: list[threading.Thread] = []

        for i in range(max_workers):
            # Using `args` to pass positional arguments and `kwargs` for keyword arguments
            t = threading.Thread(target=self.new_worker, args=[i + 1 < (max_workers * 0.7)], daemon=True)
            threads.append(t)
        
        # Start each thread
        for t in threads:
            t.start()

        while True:
            time.sleep(1)

    def save_index(self):
        # save data to CSV
        csv_filename = "index.csv"
        with open(csv_filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["term", "urls"])
            writer.writeheader()
            index = self.__indexer.get_index()
            for term in index.items():
                writer.writerow({"term": term[0], "urls": term[1]})

    def exit_handler(self):
        print('Exiting...')
        #self.__manager.save() # no longer needed
        # self.save_index() # no longer needed