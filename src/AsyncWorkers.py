import time
from src.AsyncCrawler import AsyncCrawler
from src.Queue import QueueManager
import requests as req

from src.helpers.ClearCmd import clear_screen

class AsyncWorkerManager:
    def __init__(self):
        self.__manager = QueueManager()

    async def start(self):
        # start worker threads
        crawler = AsyncCrawler(3000)
        await crawler.crawl(self.__manager)


    def exit_handler(self):
        print('Exiting...')
        self.__manager.save()