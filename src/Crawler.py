import asyncio
from collections import deque
import aiohttp
import time
from lxml import html
from protego import Protego
from src.Indexer import Indexer
from src.Queue import QueueManager
from src.helpers.ClearCmd import clear_screen
from src.helpers.DomainExtractor import FindRobotsTxt
from src.Indexer import Indexer

class Crawler:
    user_agent = 'NoAICrawler'
    headers = {'User-Agent': user_agent}

    def __init__(self, indexer: Indexer, max_concurrent=8):
        self.indexer = indexer
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.request_times = deque(maxlen=100)
        self.total_requests = 0

    async def fetch_url(self, session: aiohttp.ClientSession, url: str, queue: QueueManager) -> str | None:
        try:
            robots_url = FindRobotsTxt(url)

            

            async with session.get(robots_url, timeout=aiohttp.ClientTimeout(total=5), headers=self.headers) as robots_response:
                rp = Protego.parse(await robots_response.text())
                
                delay = rp.crawl_delay(self.user_agent)

                if(delay): 
                    await asyncio.sleep(delay)

            if(rp.can_fetch(url, self.user_agent)):
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5), headers=self.headers) as response:
                        if response.status == 200:
                            return await response.text()
                        return None
                except asyncio.TimeoutError:
                    return None
                except Exception as e:
                    return None
                
        except Exception as e:
            return None

    async def crawl(self, manager: QueueManager):
        resolver = aiohttp.AsyncResolver()

        connector = aiohttp.TCPConnector(
            resolver=resolver,
            limit=10000,
            limit_per_host=100,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
            force_close=False
        )
        last_total_requests = 0
        last_stats_time = time.time()
        stats_interval = 10.0
        
        timeout = aiohttp.ClientTimeout(total=2, connect=1)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            while True:
                urls_batch = []
                for _ in range(self.max_concurrent):
                    url = manager.getHighPriorityUrl()
                    if url:
                        urls_batch.append(url)
                    elif not url:
                        break
                
                if not urls_batch:
                    await asyncio.sleep(0.001)
                    continue
                
                tasks = [self.process_url(session, url, manager) for url in urls_batch]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                current_time = time.time()
                if current_time - last_stats_time > stats_interval:
                    self.show_stats(last_total_requests, stats_interval)
                    last_total_requests = self.total_requests
                    last_stats_time = current_time
        pass

    def show_stats(self, last_total_requests, stats_interval):
        if self.request_times:
            avg_req_time = sum(self.request_times) / len(self.request_times)
            clear_screen()
            crawls_per_second = round((self.total_requests - last_total_requests) / stats_interval, 2)
            print(f"Avg request time: {round(avg_req_time, 2)}s | Crawls per second: {crawls_per_second}")
            print(f"Crawled: {self.total_requests} websites!")

    async def process_url(self, session: aiohttp.ClientSession, url: str, manager: QueueManager):
        start_time = time.perf_counter()
    
        response = await self.fetch_url(session, url, manager)
        
        request_time_ms = (time.perf_counter() - start_time)
        self.request_times.append(request_time_ms)
        self.total_requests += 1

        if response is None: 
            return

        tree = html.fromstring(response)

        links = tree.xpath('//a/@href')

        elements = tree.xpath('//p | //h1 | //h2 | //h3 | //h4 | //h5 | //h6 | //a')

        all_text = ''

        for element in  elements:
            all_text = all_text + element.text_content()
        
        hrefs = []
        for link in links:
            if str(link).startswith('http'):
                hrefs.append(link)

        try:
            self.indexer.index_html(url=url, text=all_text)
        except Exception as e:
            print(e)

        manager.queue(hrefs)