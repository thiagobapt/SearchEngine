from collections import deque
import threading
import requests as req
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import time
from tenacity import retry, stop_after_attempt, wait_exponential

from src.Queue import QueueManager

class CrawlerThread(threading.Thread):
    headers = {'User-Agent': 'NoAICrawler/0.0 (https://example.org/coolbot/; coolbot@example.org)'}
    MAX_CRAWLS = 200

    def __init__(self,  *args, **kwargs):
        super(CrawlerThread, self).__init__(target=self.crawl, *args, **kwargs)
        self._kill_event = threading.Event()
        self.request_times = deque(maxlen=100)
        self.total_requests = 0
        # Configure session for better performance
        self.session = req.Session()
        
        # Connection pooling
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=Retry(
                total=2,
                backoff_factor=0.1,
                status_forcelist=[500, 502, 503, 504]
            )
        )
        
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Set timeouts
        self.session.timeout = (3, 10)  # (connect, read)

    def kill(self):
        self._kill_event.set()

    def fetch_url(self, url: str):
        try:
            response = self.session.get(url, headers=self.headers, timeout=5)
            return response if response.status_code == 200 else None
        except:
            return None

    def crawl(self, manager: QueueManager):

        crawled = 0
        while crawled < self.MAX_CRAWLS:

            if(self._kill_event.is_set()): break

            current_url = manager.getUrl()

            sleep_time = 0.05

            if(not current_url): 
                time.sleep(sleep_time)
                continue

            crawled += 1

            if(manager.inCooldown(current_url)): time.sleep(sleep_time)

            start_time = time.perf_counter()

            response = self.fetch_url(current_url)

            request_time_ms = time.perf_counter() - start_time

            self.request_times.append(request_time_ms)
            self.total_requests += 1

            if(response == None or response.status_code != 200): continue

            soup = BeautifulSoup(response.text, "html.parser")

            links = soup.select('a[href]')

            manager.queue(links)