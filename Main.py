import asyncio
import atexit

from src.AsyncWorkers import AsyncWorkerManager
from src.Workers import WorkerManager

# workers = WorkerManager(min_workers=10, max_workers=20, desired_crawls_per_sec=15)
workers = AsyncWorkerManager()

async def main():
    await workers.start()


def save(workers: WorkerManager):
    print("saving")
    workers.exit_handler()

atexit.register(save, workers)

if __name__ == "__main__":
    asyncio.run(main())
