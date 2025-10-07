import atexit
import time

from src.Workers import WorkerManager

workers = WorkerManager(min_workers=10, max_workers=20, desired_crawls_per_sec=15)

def main():
    workers.start()


def save(workers: WorkerManager):
    print("saving")
    workers.exit_handler()

atexit.register(save, workers)

if __name__ == "__main__":
    main()
