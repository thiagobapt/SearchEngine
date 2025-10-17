import asyncio
import atexit
import time
import nltk
from pymongo import AsyncMongoClient

from src.Ranker import Ranker
from src.helpers.ClearCmd import clear_screen
from src.Workers import Workers
from nltk.corpus import wordnet

workers = Workers()
ranker = Ranker(db=AsyncMongoClient("mongodb://localhost:27017/"), iterations=100)

def main():
    print("Starting...")

    while True:
        clear_screen()
        selection = input("Enter one: \n1. Crawl and index \n2. Page Rank \n3. Load nltk\n4. Exit \n")
        if selection == '1': return workers.start(low_priority_crawlers=100, high_priority_crawlers=10, max_indexers=4, max_concurrent_indexer=100, max_concurrent_crawler=100)
        elif selection == '2': return asyncio.run(ranker.PageRank())
        elif selection == '3':
            print("Loading...")
            nltk.download('stopwords', quiet=True)  # for stopwords+
            nltk.download('punkt_tab', quiet=True)
            nltk.download('averaged_perceptron_tagger_eng', quiet=True)  # for pos_tag
            nltk.download('wordnet', quiet=True)  # for lemmatizer
            _ = wordnet.synsets('test') # Accessing it once to force loading
            print("Done!")
            time.sleep(1)
            continue
        elif selection == '4': return print('Exiting...')
        else: 
            print('Please enter 1, 2, 3 or 4')
            time.sleep(1)
            continue

if __name__ == "__main__":
    main()
