# Search Engine

A web search engine built with Python that crawls, indexes, and ranks web pages using the PageRank algorithm. The front end is built with Reflex and isn't the focus of this project, is used only to demonstrate the results of the engine.

## Architecture

The project consists of two main components:

### 1. Bot (Backend Crawler/Indexer/Page Ranking)
- **Web Crawler**: Multi-threaded and asynchronous crawling
- **Indexer**: Scrapes the webpage with LXML, removes stop words and lemmatizes the words before indexing
- **PageRank**: Ranks pages with the PageRank algorithm, using NetworkX
- **Queue Management**: Queues for pages to crawl and pages to index made with Redis

### 2. FrontEnd (Search Interface)
- **Web Interface**: Search UI built with Reflex framework

## Features

- **Respectful Crawling**: Honors robots.txt, implements crawl delays and allowed pages
- **Text Processing**: Tokenization, lemmatization and stop word removal
- **Ranking**: Implements the PageRank algorithm for ranking pages
- **High Performance**: Asynchronous processing with multi-threading
- **Storage**: MongoDB for document storage and Redis for queue management

## Prerequisites

- MongoDB (running on localhost:27017)
- Redis (running on localhost:6379)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/thiagobapt/SearchEngine.git
   cd SearchEngine
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Starting the Crawler/Indexer Bot

Navigate to the Bot directory and run:

```bash
cd Bot
python Main.py
```

The main menu offers four options:

1. **Crawl and index**: Start the crawling and indexing process
   
2. **Page Rank**: Calculate PageRank scores for indexed pages
   
3. **Load NLTK**: Download required NLTK datasets **THIS MUST BE DONE FIRST**
   
4. **Exit**

### Starting the Search Interface

Navigate to the FrontEnd directory and run:

```bash
cd FrontEnd
reflex run
```

The web interface will be available at `http://localhost:3000`

## Configuration

### Crawler Settings
Modify the parameters in `Bot/Main.py` when selecting option 1:

- `low_priority_crawlers`: Number of threads for discovered domains (default: 100)
- `high_priority_crawlers`: Number of threads for new domains (default: 10)
- `max_indexers`: Number of indexing worker threads (default: 4)
- `max_concurrent_indexer`: Concurrent documents per indexer (default: 100)
- `max_concurrent_crawler`: Concurrent requests per crawler (default: 100)

In my experience, the indexing is done very fast and the resources are better allocated with more crawlers. Keep a balance with more low priority crawlers than high priority ones, as the high priority queue tends to empty out fast.

### Database Configuration
- **MongoDB**: `mongodb://localhost:27017/`
  - Database: `searchengine`
  - Collections: `indexes`, `pages`, `outgoing_links`
- **Redis**: `localhost:6379`
  - Queues: `high_priority_queue`, `low_priority_queue`, `indexing_queue`
 
**All the database configuration is done automatically!**

### PageRank Settings
Adjust iterations in `Bot/src/Ranker.py`:
```python
ranker = Ranker(db=AsyncMongoClient("mongodb://localhost:27017/"), iterations=100)
```

## Technical Details

### Text Processing Pipeline
1. **Normalization**: Remove extra whitespace and punctuation
2. **Tokenization**: Split text into individual words using NLTK
3. **Stop word removal**: Remove stop words and overly long tokens
4. **Lemmatization**: Reduce words to root forms

### Search Algorithm
The search uses MongoDB aggregation pipeline:
1. Match documents containing all query terms
2. Count term frequency per document
3. Join with page metadata (title, description, rank)
4. Sort by PageRank score first and then term frequency
5. Return formatted results

### Crawling Strategy
- **Priority Queue System**: New domains get high priority and known domains get low priority to ensure the crawler doesn't get stuck in a single website and visits a lot of new pages
- **Robots.txt Compliant**: Respects the rules under robots.txt for crawlable pages and cooldowns
- **Duplicate Detection**: Keeps track of the urls it has seen before to avoid crawling the same page twice

## Dependencies

### Core Dependencies
- `aiohttp`: Async HTTP client for web crawling
- `lxml`: Fast XML/HTML parsing
- `nltk`: Natural language processing toolkit
- `pymongo`: MongoDB driver
- `networkx`: Graph algorithms for PageRank
- `redis`: Queue management and caching
- `reflex`: Web framework for the frontend
- `sentence-transformers`: Semantic search capabilities
