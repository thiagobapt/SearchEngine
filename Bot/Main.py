import atexit
import nltk

from src.Workers import Workers
from nltk.corpus import wordnet

print("Loading...")
nltk.download('stopwords', quiet=True)  # for stopwords+
nltk.download('punkt_tab', quiet=True)
nltk.download('averaged_perceptron_tagger_eng', quiet=True)  # for pos_tag
nltk.download('wordnet', quiet=True)  # for lemmatizer
_ = wordnet.synsets('test') # Accessing it once to force loading
print("Done!")

workers = Workers()

def main():
    print("Starting...")
    workers.start(max_crawlers=50, max_indexers=10, max_concurrent_indexer=100, max_concurrent_crawler=100)

def save(workers: Workers):
    print("saving")
    workers.exit_handler()

atexit.register(save, workers)

if __name__ == "__main__":
    main()
