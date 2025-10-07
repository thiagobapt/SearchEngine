import time
from src.Queue import QueueManager
import requests as req

from src.Crawler import CrawlerThread
from src.helpers.ClearCmd import clear_screen

class WorkerManager:
    def __init__(self, max_workers: int, min_workers: int, desired_crawls_per_sec: float):
        self.__manager = QueueManager()
        self.__threads: list[CrawlerThread] = []
        self.__MAX_WORKERS = max_workers
        self.__MIN_WORKERS = min_workers
        self.__DESIRED_CRAWLS_PER_SEC = desired_crawls_per_sec
        self.__req_count_history: list[int] = []
        self.__crawl_count = 0

    def spawn(self, count: int = 1):
        print(f'Starting {count} new crawlers...')
        for _ in range(count):
            
            thread = CrawlerThread(daemon=True, args=[self.__manager])
            self.__threads.append(thread)
            thread.start()

    def kill(self, count: int):
        print(f'Killing {count} crawlers...')
        for _ in range(count):
            thread = self.__threads.pop()
            thread.kill()

    def start(self):
        # start worker threads
        self.spawn(self.__MIN_WORKERS)

        monitoring_time = 5 #seconds

        while True:
            start = time.perf_counter()

            all_request_times = []
            total_requests_this_period = 0
            
            for thread in self.__threads:
                if thread.request_times:
                    # Get recent request times
                    recent_times = list(thread.request_times)
                    all_request_times.extend(recent_times)  # Last 10 requests per thread
                    
                    # Count new requests since last check
                    new_requests = thread.total_requests - getattr(thread, '_last_count', 0)
                    total_requests_this_period += new_requests
                    thread._last_count = thread.total_requests

            self.__req_count_history.insert(0, total_requests_this_period)
            self.__crawl_count += total_requests_this_period

            if(len(self.__req_count_history) == 0 or len(all_request_times) == 0): 
                time.sleep(max(monitoring_time - (time.perf_counter() - start), 0))
                continue

            avg_req_time = sum(all_request_times) / len(all_request_times)
            avg_req_count = (sum(self.__req_count_history) / len(self.__req_count_history)) / monitoring_time

            self.__req_count_history = self.__req_count_history[:60]

            clear_screen()

            self.balance_load(avg_req_count)

            print(f"Avg request time: {round(avg_req_time,2)}s | Crawls per second: {round(avg_req_count,2)}")
            # print(f"Crawled: {self.__crawl_count} websites! Queue: {self.__manager.getQueueSize()}")
            print(f"Crawled: {self.__crawl_count} websites!")
            print(f"Crawlers active: {len(self.__threads)}")

            time.sleep(max(monitoring_time - (time.perf_counter() - start), 0))

    def balance_load(self, avg_req_count: float):
        if(avg_req_count < (self.__DESIRED_CRAWLS_PER_SEC * 1.2) and avg_req_count > (self.__DESIRED_CRAWLS_PER_SEC * 0.8)):
            return
        elif(avg_req_count < self.__DESIRED_CRAWLS_PER_SEC and len(self.__threads) < self.__MAX_WORKERS):
            if(avg_req_count == 0): return
            max_to_spawn = min(round((self.__MAX_WORKERS - len(self.__threads))), 2)

            to_spawn = round((avg_req_count * len(self.__threads)) / self.__DESIRED_CRAWLS_PER_SEC)

            self.spawn(min(max_to_spawn, to_spawn))
            
        elif(len(self.__threads) > self.__MIN_WORKERS):
            self.kill(1)


    def exit_handler(self):
        print('Exiting...')
        self.__manager.save()