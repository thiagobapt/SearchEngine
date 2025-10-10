"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import string
from pymongo import MongoClient
import reflex as rx
import nltk
from nltk import pos_tag
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import requests
from lxml import html
from sentence_transformers import SentenceTransformer, util

from rxconfig import config

mongodb = MongoClient("mongodb://localhost:27017/")
db = mongodb["searchengine"]
collection = db['indexes']

nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('averaged_perceptron_tagger_eng', quiet=True)  # for pos_tag
nltk.download('wordnet', quiet=True)  # for lemmatizer
nltk.download('stopwords', quiet=True)  # for stopwords+

lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words())
model = SentenceTransformer('all-MiniLM-L6-v2') # Load a pre-trained model

class State(rx.State):
    """The app state."""

class FormInputState(rx.State):
    form_data: dict[str, list[str]] = {}
    results: dict[str, dict[str, str]] = {}

    @rx.event
    def handle_submit(self, form_data: dict):
        text: str = form_data.get('input')

        text = " ".join(text.split())

        text = text.translate(str.maketrans('', '', string.punctuation + '’')).lower()

        tokens = word_tokenize(text)

        filtered_tokens = [word for word in tokens if word not in stop_words]

        filtered_tokens = [word for word in filtered_tokens if not len(word) > 30]

        tagged = pos_tag(filtered_tokens)

        lemmatized_words = [lemmatizer.lemmatize(
            word, pos='v' if tag.startswith('V') else 'n') for word, tag in tagged]

        # 2. Define the aggregation pipeline
        pipeline = [
            # Stage 1: Filter the documents to include only the target words
            {
                "$match": {
                    "word": { "$in": lemmatized_words }
                }
            },
            # Stage 2: Group by URL. Collect unique matched words and sum the total word count.
            {
                "$group": {
                    "_id": "$url",
                    # Collect unique words to determine the match count (e.g., 3 out of 5)
                    "matched_words": { "$addToSet": "$word" },
                    # Sum the 'count' field for ALL matching documents on this URL
                    "total_word_count": { "$sum": "$count" }
                }
            },
            # Stage 3: Project the Match Count (the number of unique words found)
            {
                "$project": {
                    "url": "$_id",
                    # Calculate the match count (number of unique words found)
                    "match_count": { "$size": "$matched_words" },
                    "total_word_count": 1 # Keep the total word count for secondary sorting
                }
            },
            # Stage 4: Sort the results.
            # Primary sort: By 'match_count' (descending) - most matching words first.
            # Secondary sort: By 'total_word_count' (descending) - highest overall count first.
            {
                "$sort": {
                    "match_count": -1,
                    "total_word_count": -1
                }
            },
            # Stage 5 (Optional): Clean up the output
            {
                "$project": {
                    "_id": 0,
                    "url": 1,
                    "match_count": 1,
                    "total_word_count": 1
                }
            }
        ]

        # 3. Execute the aggregation
        result_cursor = collection.aggregate(pipeline)

        # 4. Extract and print the list of URLs
        urls_with_all_words = [doc['url'] for doc in result_cursor]

        self.results.clear()

        for url in urls_with_all_words:
            
            try:
                response = requests.get(url, headers={'User-Agent': 'NoAICrawler'}, timeout=5)

                response.raise_for_status()

                tree = html.fromstring(response.text)
            
                elements = tree.xpath('//p | //h1 | //h2 | //h3 | //h4 | //h5 | //h6 | //a')

                all_text = ''

                title_element = tree.xpath("//title/text()")

                for element in  elements:
                    all_text = all_text + element.text_content() + '\n'

                whitespace_except_space = string.whitespace.replace(" ", "")
                all_text = all_text.strip(whitespace_except_space)

                words = all_text.split(" ")

                for index, word in enumerate(words):
                    lemmatized = lemmatizer.lemmatize(word)
                    if (lemmatized.lower() in lemmatized_words):
                        words[index] = f"**{word}**"

                words = " ".join(words)

                sentences = nltk.sent_tokenize(words)
            
                sentence_embeddings = model.encode(sentences, convert_to_tensor=True)
                query_embedding = model.encode(form_data.get('input'), convert_to_tensor=True)

                cosine_scores = util.cos_sim(query_embedding, sentence_embeddings)[0]
                most_relevant_index = cosine_scores.argmax().item()

                self.results[url] = {
                    "all_text": all_text,
                    "title": title_element,
                    "search_paragraph": sentences[most_relevant_index]
                }
            except Exception as e:
                self.results[url] = {
                    "all_text": '',
                    "title": '',
                    "search_paragraph": ''
                }
                print(e)
                continue
        
        self.form_data = {"input": form_data.get('input').split(' ')}


def render_item(info: list):
    """Render a single item."""
    url = info[0]
    page_info: dict[str, str] = info[1]
    # Note that item here is a Var, not a str!
    return rx.container(rx.text(page_info.get('title'), size='5'), rx.link(url, href=url), rx.markdown(page_info.get("search_paragraph")))

def form_search():
    return rx.card(
        rx.vstack(
            rx.heading("Search Engine"),
            rx.form.root(
                rx.hstack(
                    rx.input(
                        name="input",
                        placeholder="What are you looking for?",
                        type="text",
                        required=True,
                        radius='full',
                        width="100%"
                    ),
                    rx.button("Search", type="submit"),
                    width="100%",
                ),
                on_submit=FormInputState.handle_submit,
                reset_on_submit=True,
            ),
            rx.divider(),
            rx.vstack(
                rx.heading("Results:"),
                rx.badge(FormInputState.form_data.get('input')),
                rx.box(
                    rx.foreach(FormInputState.results, render_item)
                )
            ),
            align_items="left",
            width="100%",
        ),
        width="100%",
    )

def index() -> rx.Component:
    return rx.flex(
        rx.container(
            form_search(),
        ),
        align='center',
        justify='center'
    )


app = rx.App()
app.add_page(index)
