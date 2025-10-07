from nltk import pos_tag
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

class Indexer: 
    
    lemmatizer = WordNetLemmatizer()
    stop_words = set(stopwords.words('english'))

    def __init__(self):
        pass

    async def index_html(self, url: str, text: str):
        
        tokens = word_tokenize(text.lower())
        tagged = pos_tag(tokens)

        filtered_tokens = [word for word in tagged if word not in self.stop_words]

        lemmatized_words = [self.lemmatizer.lemmatize(
            word, pos='v' if tag.startswith('V') else 'n') for word, tag in filtered_tokens]
        
        print(lemmatized_words)