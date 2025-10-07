from src.Crawler import Crawler
from src.Queue import QueueManager

class Workers:
    def __init__(self):
        self.__manager = QueueManager()

    async def start(self):
        crawler = Crawler(10)
        await crawler.crawl(self.__manager)


    def exit_handler(self):
        print('Exiting...')
        self.__manager.save()