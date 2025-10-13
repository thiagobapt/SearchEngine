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


        pipeline = [
            # Filter to include documents with at least one target word
            {
                "$match": {
                    "word": { "$in": lemmatized_words }
                }
            },
            # Group by URL, calculate match count and total word count
            {
                "$group": {
                    "_id": "$url",
                    "matched_words": { "$addToSet": "$word" },
                    "total_word_count": { "$sum": "$count" }
                }
            },
            # Calculate Match Count
            {
                "$project": {
                    "url": "$_id",
                    "match_count": { "$size": "$matched_words" },
                    "total_word_count": 1
                }
            },
            # Join with the 'pages'
            {
                "$lookup": {
                    "from": "pages",
                    "localField": "url",          # Field from the input documents (from the current pipeline)
                    "foreignField": "url",        # Field from the documents of the "from" collection (pages)
                    "as": "page_details"          # The name of the new array field to add to the output documents
                }
            },
            # Deconstruct the 'page_details' array
            # Since 'url' is unique in the 'pages' collection, this array will usually have 0 or 1 element.
            # This turns the array into an object for easier access.
            {
                "$unwind": {
                    "path": "$page_details",
                    "preserveNullAndEmptyArrays": True # Important: Keep results even if no match is found in 'pages'
                }
            },
            # Sort the results
            # Primary: By 'match_count' (descending). Secondary: By 'total_word_count' (descending).
            {
                "$sort": {
                    "match_count": -1,
                    "total_word_count": -1
                }
            },
            #  Clean up the output to include the page details
            {
                "$project": {
                    "_id": 0,
                    "url": 1,
                    "match_count": 1,
                    "total_word_count": 1,
                    "title": "$page_details.title",           # Extract title from the joined document
                    "description": "$page_details.description" # Extract description from the joined document
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
