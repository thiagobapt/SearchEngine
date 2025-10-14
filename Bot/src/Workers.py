import asyncio
import csv
import threading
import time
from pymongo import AsyncMongoClient, MongoClient
import pymongo
from src.Crawler import Crawler
from src.Queue import QueueManager
from src.Indexer import Indexer

class Workers:
    def __init__(self):
        self.__manager = QueueManager()
        self.__mongo_client = MongoClient("mongodb://localhost:27017/")

    def new_crawler(self, high_priority: bool):
        crawler = Crawler(high_priority=high_priority, max_concurrent=100)

        asyncio.run(crawler.crawl(self.__manager))
    
    def new_indexer(self):
        indexer = Indexer(db= AsyncMongoClient("mongodb://localhost:27017/"), max_concurrent = 1000)
        asyncio.run(indexer.index(self.__manager))

    def start(self, max_crawlers: int, max_indexers: int):
        # initialize database
        db = self.__mongo_client['searchengine']
        
        # db['indexes'].create_index([("word", pymongo.TEXT), ("url", pymongo.TEXT)])
        # db['outgoing_links'].create_index([("url", pymongo.TEXT)])
        # db['pages'].create_index([("url", pymongo.TEXT)])

        # Minimum of 2 workers is needed, one for high priority and one for low
        if(max_crawlers < 2): max_crawlers = 2

        # Start threads for each link
        threads: list[threading.Thread] = []

        for i in range(max_crawlers):
            # Using `args` to pass positional arguments and `kwargs` for keyword arguments
            t = threading.Thread(target=self.new_crawler, args=[i + 1 < (max_crawlers * 0.7)], daemon=True)
            threads.append(t)

        for i in range(max_indexers):
            # Using `args` to pass positional arguments and `kwargs` for keyword arguments
            t = threading.Thread(target=self.new_indexer, daemon=True)
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