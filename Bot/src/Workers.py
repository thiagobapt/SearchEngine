import asyncio
import csv
import threading
import time
from pymongo import AsyncMongoClient, MongoClient
from src.Crawler import Crawler
from src.Queue import QueueManager
from src.Indexer import Indexer

class Workers:
    def __init__(self):
        self.__manager = QueueManager()

    def new_crawler(self, high_priority: bool, max_concurrent: int):
        crawler = Crawler(high_priority=high_priority, max_concurrent=max_concurrent)

        asyncio.run(crawler.crawl(self.__manager))
    
    def new_indexer(self, max_concurrent: int):
        indexer = Indexer(db= AsyncMongoClient("mongodb://localhost:27017/"), max_concurrent = max_concurrent)
        asyncio.run(indexer.index(self.__manager))

    def start(self, low_priority_crawlers: int, high_priority_crawlers: int, max_indexers: int, max_concurrent_crawler: int, max_concurrent_indexer: int):

        try:
            # Start threads for each link
            threads: list[threading.Thread] = []

            for i in range(low_priority_crawlers):
                # Using `args` to pass positional arguments and `kwargs` for keyword arguments
                t = threading.Thread(target=self.new_crawler, args=[False, max_concurrent_crawler], daemon=False)
                threads.append(t)
            
            for i in range(high_priority_crawlers):
                # Using `args` to pass positional arguments and `kwargs` for keyword arguments
                t = threading.Thread(target=self.new_crawler, args=[True, max_concurrent_crawler], daemon=False)
                threads.append(t)

            for i in range(max_indexers):
                # Using `args` to pass positional arguments and `kwargs` for keyword arguments
                t = threading.Thread(target=self.new_indexer, args=[max_concurrent_indexer], daemon=False)
                threads.append(t)
            
            # Start each thread
            for t in threads:
                t.start()

            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.__manager.interrupted = True

    # def save_index(self):
    #     # save data to CSV
    #     csv_filename = "index.csv"
    #     with open(csv_filename, mode="w", newline="", encoding="utf-8") as file:
    #         writer = csv.DictWriter(file, fieldnames=["term", "urls"])
    #         writer.writeheader()
    #         index = self.__indexer.get_index()
    #         for term in index.items():
    #             writer.writerow({"term": term[0], "urls": term[1]})

    def exit_handler(self):
        print('Exiting...')
        #self.__manager.save() # no longer needed
        # self.save_index() # no longer needed