import csv

from pymongo import MongoClient
from src.Crawler import Crawler
from src.Queue import QueueManager
from src.Indexer import Indexer

class Workers:
    def __init__(self):
        self.__manager = QueueManager()
        self.__indexer = Indexer(MongoClient("mongodb://localhost:27017/"))

    async def start(self):
        crawler = Crawler(self.__indexer, 100)
        await crawler.crawl(self.__manager)

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