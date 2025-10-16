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
    form_data: dict[str, str] = {}
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

        num_target_words = len(lemmatized_words)

        pipeline = [
            # Stage 1: Filter to include documents with at least one target word (initial filter)
            {
                "$match": {
                    "word": { "$in": lemmatized_words }
                }
            },
            # Stage 2: Group by URL, collect unique matched words, and sum the total word count
            {
                "$group": {
                    "_id": "$url",
                    "matched_words": { "$addToSet": "$word" },
                    "total_word_count": { "$sum": "$count" }
                }
            },
            # Stage 3: Calculate Match Count and prepare fields for next stage
            {
                "$project": {
                    "url": "$_id",
                    "match_count": { "$size": "$matched_words" },
                    "total_word_count": 1
                }
            },
            # 🌟 Stage 4: Filter to KEEP ONLY URLs that match ALL words
            {
                "$match": {
                    "match_count": num_target_words
                }
            },
            # Stage 5: Join with the 'pages' collection
            {
                "$lookup": {
                    "from": "pages",
                    "localField": "url",
                    "foreignField": "url",
                    "as": "page_details"
                }
            },
            # 🌟 Stage 6: Deconstruct the 'page_details' array.
            # By omitting "preserveNullAndEmptyArrays", we automatically discard URLs that did not match a page entry (and thus have no 'rank').
            {
                "$unwind": "$page_details"
            },
            # 🌟 Stage 7: Sort the results
            # Primary sort: By 'rank' (ascending: 1, lower rank is better)
            # Secondary sort: By 'total_word_count' (descending: -1, higher count is better)
            {
                "$sort": {
                    "page_details.rank": -1,
                    "total_word_count": -1
                }
            },
            # Stage 8: Clean up the output to include the rank and page details
            {
                "$project": {
                    "_id": 0,
                    "url": 1,
                    "match_count": 1,
                    "total_word_count": 1,
                    "title": "$page_details.title",
                    "description": "$page_details.description",
                    "rank": "$page_details.rank" # Include the rank in the final output
                }
            }
        ]

        # 3. Execute the aggregation
        result_cursor = collection.aggregate(pipeline)

        self.results.clear()

        for doc in result_cursor:

            self.results[doc["url"]] = {
                "title": doc["title"],
                "description": doc["description"]
            }
        
        self.form_data = {"input": form_data.get('input')}


def render_item(info: list):
    """Render a single item."""
    url = info[0]
    page_info: dict[str, str] = info[1]
    # Note that item here is a Var, not a str!
    return rx.container(rx.text(page_info.get('title'), size='5'), rx.link(url, href=url), rx.markdown(page_info.get("description")))

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
