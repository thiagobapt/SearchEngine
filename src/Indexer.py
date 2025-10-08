from collections import defaultdict
import string
from nltk import pos_tag
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

class Indexer: 
    
    lemmatizer = WordNetLemmatizer()
    stop_words = set(stopwords.words())
    index: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def __init__(self):
        pass

    def __clean_and_tokenize(self, text: str):
        text = " ".join(text.split())

        text = text.translate(str.maketrans('', '', string.punctuation + '’'))

        tokens = word_tokenize(text)

        filtered_tokens = [word for word in tokens if word not in self.stop_words]

        filtered_tokens = [word for word in filtered_tokens if not len(word) > 30]

        tagged = pos_tag(filtered_tokens)

        lemmatized_words = [self.lemmatizer.lemmatize(
            word, pos='v' if tag.startswith('V') else 'n') for word, tag in tagged]
        
        return lemmatized_words

    def index_html(self, url: str, text: str):
        tokens = self.__clean_and_tokenize(text)
        
        for token in tokens:
            self.index[token][url] += 1
        

    def get_index(self):
        return self.index

