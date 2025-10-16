import asyncio
from pymongo import TEXT, AsyncMongoClient, UpdateOne
import networkx as nx

class Ranker:
    def __init__(self, db: AsyncMongoClient, iterations: int):
        self.db = db["searchengine"]
        self.outgoing = self.db['outgoing_links']
        self.pages = self.db['pages']
        self.iterations = iterations
        pass

    async def SaveRanks(self, operations: list):
        try:
            await self.pages.bulk_write(operations, ordered=False)
            print(f"Saved {len(operations)}")
        except Exception as e:
            print(e)

        return

    async def PageRank(self):
        outgoing = []
        pages_dict = {}

        async with self.outgoing.find() as cursor:
            async for doc in cursor:
                outgoing.append(doc)

        async with self.pages.find() as cursor:
            async for doc in cursor:
                pages_dict[str(doc['url'])] = doc['_id']
        
        edges = []

        for page in outgoing:
            for url in page['outgoing']:
                edges.append((page['url'], url))

        G = nx.DiGraph()

        G.add_edges_from(edges)

        pagerank_scores = nx.pagerank(G, alpha=0.85)

        operations = []

        for url, rank in pagerank_scores.items():
            try:
                operations.append(UpdateOne({
                    '_id': pages_dict[url]
                }, {
                    "$set": {
                        "rank": rank
                    }
                }))
            except Exception:
                continue
        
        print(f"Saving {len(operations)} page ranks...")

        chunks = []

        chunk_size = 5000

        while len(operations) > 0:
            chunk = []

            for _ in range(chunk_size):
                if(len(operations) == 0): break
                chunk.append(operations.pop())

            chunks.append(chunk)

        tasks = []

        for chunk in chunks:
            tasks.append(self.SaveRanks(chunk))

        await asyncio.gather(*tasks, return_exceptions=True)

        print("Done!")

        return