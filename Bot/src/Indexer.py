import asyncio
from collections import defaultdict
import string
import threading
import time
from nltk import pos_tag
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from pymongo import AsyncMongoClient, InsertOne
from collections import Counter

from src.Queue import QueueManager

class Indexer: 
    
    lemmatizer = WordNetLemmatizer()
    stop_words = set(stopwords.words())

    def __init__(self, db: AsyncMongoClient, max_concurrent: 8):
        self.db = db["searchengine"]
        self.indexes = self.db['indexes']
        self.outgoing = self.db['outgoing_links']
        self.pages = self.db['pages']
        self.max_concurrent = max_concurrent
        pass

    async def index(self, manager: QueueManager):
        while True:
            indexing_batch: list[dict[str, list[str]]] = manager.get_next_to_index(self.max_concurrent)
            
            if not indexing_batch:
                await asyncio.sleep(1)
                continue
            
            tasks = []

            for to_index in indexing_batch:
                tasks.append(self.index_html(to_index.get('url')[0], to_index.get('text')[0], to_index.get('title')[0], to_index.get('description')[0], to_index.get('outgoing')))
            
            try:
                await asyncio.gather(*tasks, return_exceptions=False)
            except Exception as e:
                print(f"{threading.current_thread().name} error: {e}")
        

    def __clean_and_tokenize(self, text: str):
        text = " ".join(text.split())

        text = text.translate(str.maketrans('', '', string.punctuation + '’')).lower()

        tokens = word_tokenize(text)

        filtered_tokens = [word for word in tokens if word not in self.stop_words]

        filtered_tokens = [word for word in filtered_tokens if not len(word) > 30]

        tagged = pos_tag(filtered_tokens)

        lemmatized_words = [self.lemmatizer.lemmatize(
            word, pos='v' if tag.startswith('V') else 'n') for word, tag in tagged]
        
        return lemmatized_words

    async def index_html(self, url: str, text: str, title: str, description: str, outgoing_links: list[str]):
        start = time.perf_counter()

        tokens = self.__clean_and_tokenize(text)

        end_tokenization = time.perf_counter() - start

        start_mongo = time.perf_counter()

        await self.pages.update_one(
                {"url": url, "title": title, "description": description, "rank": 1},
                {
                    "$set": {"url": url, "title": title, "description": description, "rank": 1},
                },
                upsert=True
            )
        
        await self.outgoing.update_one(
                {"url": url, "outgoing": outgoing_links},
                {
                    "$set":  {"url": url, "outgoing": outgoing_links},
                },
                upsert=True
            )
        
        token_count = Counter(tokens)
        
        operations = []
        
        for word, count in token_count.items():
            operations.append(
                InsertOne(
                    {"word": word, "url": url},
                    {
                        # 3. Use $setOnInsert for static fields during an upsert
                        "$setOnInsert": {"word": word, "url": url},
                        "$inc": {"count": count}
                    },
                )
            )

        if operations:
            await self.indexes.bulk_write(operations, ordered=False)

        end = time.perf_counter()

        print(f"{threading.current_thread().name} Indexed: {url} in {end - start}s | DB operations: {end - start_mongo}s | Tokenization: {end_tokenization}s")

