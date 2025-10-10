import asyncio
from collections import deque
import aiohttp
from lxml import html
from src.Indexer import Indexer
from src.Queue import QueueManager
from src.helpers.ClearCmd import clear_screen
from src.helpers.DomainExtractor import extract_domain, find_robots_txt
from src.Indexer import Indexer
import threading

class Crawler:
    user_agent = '*'
    headers = {'User-Agent': 'NoAICrawler'}

    def __init__(self, indexer: Indexer, high_priority: bool, max_concurrent=8):
        self.indexer = indexer
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.total_requests = 0
        self.high_priority = high_priority

    async def fetch_url(self, session: aiohttp.ClientSession, url: str, queue: QueueManager) -> str | None:
        try:
            robots_url = find_robots_txt(url)
            domain = extract_domain(url)

            if(queue.check_robots(domain)):
                async with session.get(robots_url, timeout=aiohttp.ClientTimeout(total=5), headers=self.headers) as robots_response:
                    queue.save_robots_txt(domain, await robots_response.text())

            rp = queue.get_robots(domain)

            if(rp.crawl_delay(self.user_agent)): print(f"delay for {url}: {rp.crawl_delay(self.user_agent)}")

            cooldown = queue.get_next_cooldown(domain, rp.crawl_delay(self.user_agent))
            if(rp.can_fetch(url, self.user_agent)):
                if(cooldown > 0): 
                    print(f"Sleeping for: {cooldown} seconds")
                    await asyncio.sleep(cooldown)
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5), headers=self.headers) as response:
                        if response.status == 200:
                            print(f"{threading.current_thread().name} Crawled: {url}")
                            return await response.text()
                        return None
                except asyncio.TimeoutError as e:
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
        
        timeout = aiohttp.ClientTimeout(total=2, connect=1)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            while True:
                urls_batch = []
                for _ in range(self.max_concurrent):
                    url = manager.get_high_priority_url() if self.high_priority else manager.get_low_priority_url()
                    if url:
                        urls_batch.append(url)
                    elif not url:
                        break
                
                if not urls_batch:
                    await asyncio.sleep(0.001)
                    continue
                
                tasks = [self.process_url(session, url, manager) for url in urls_batch]
                await asyncio.gather(*tasks, return_exceptions=True)
        pass

    def index(self, url: str, all_text: str):
        try:
            self.indexer.index_html(url=url, text=all_text)
        except Exception as e:
            print(e)

    async def process_url(self, session: aiohttp.ClientSession, url: str, manager: QueueManager):
    
        response = await self.fetch_url(session, url, manager)

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

        asyncio.gather(asyncio.to_thread(self.index, url, all_text))

        manager.queue(hrefs)