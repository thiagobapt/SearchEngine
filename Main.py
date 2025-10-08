import asyncio
import atexit
import nltk

from src.Workers import Workers

workers = Workers()

nltk.download('punkt_tab', quiet=True)
nltk.download('averaged_perceptron_tagger_eng', quiet=True)  # for pos_tag
nltk.download('wordnet', quiet=True)  # for lemmatizer
nltk.download('stopwords', quiet=True)  # for stopwords+

async def main():
    await workers.start()

def save(workers: Workers):
    print("saving")
    workers.exit_handler()

atexit.register(save, workers)

if __name__ == "__main__":
    asyncio.run(main())
