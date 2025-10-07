import asyncio
import atexit

from src.Workers import Workers

workers = Workers()

async def main():
    await workers.start()


def save(workers: Workers):
    print("saving")
    workers.exit_handler()

atexit.register(save, workers)

if __name__ == "__main__":
    asyncio.run(main())
