"""
search.py
Author: Javier Nogueras Iso
Last update: 2024-09-07

Program to search a free text query on a previously created inverted index.
This program is based on the whoosh library. See https://pypi.org/project/Whoosh/ .
Usage: python search.py -index <index folder>
"""

import sys
import os

from whoosh.qparser import MultifieldParser
from whoosh.qparser import OrGroup
from whoosh import scoring
import whoosh.index as index
from nltk.stem.snowball import SnowballStemmer
from whoosh.analysis import Filter
from whoosh.query import Or, And
import xml.etree.ElementTree as ET
import spacy

# Load spaCy model for NER
nlp = spacy.load("es_core_news_sm")
class Stemming(Filter):
    def __init__(self, language="spanish"):
        self.stemmer = SnowballStemmer(language)

    def __call__(self, tokens):
        for token in tokens:
            token.text = self.stemmer.stem(token.text)  
            yield token

class MySearcher:
    def __init__(self, index_folder, model_type = 'tfidf'):
        ix = index.open_dir(index_folder)
        if model_type == 'tfidf':
            # Apply a vector retrieval model as default
            self.searcher = ix.searcher(weighting=scoring.TF_IDF())
        else:
            # Apply the probabilistic BM25F model, the default model in searcher method
            self.searcher = ix.searcher()
        self.parser = MultifieldParser( ["creator","contributor","publisher","title","description","subject","date"] ,ix.schema, group =OrGroup)

    def process_query_with_ner(self, query_text):
        # Process the query text with the NLP model (spaCy in this case)
        doc = nlp(query_text)

        # Initialize an empty list for the final query
        final_query = []

        # Iterate over the tokens in the processed doc
        for ent in doc.ents:
            print(f"Entity: {ent.text}, Label: {ent.label_}")
            # Add recognized named entities to the final query
            final_query.append(ent.text)

        # Join the entities to form the final query string
        final_query = query_text + ' '.join(final_query)

        print("Final Query:")
        print(final_query)

        return str(final_query)



    
    def search(self, query_text, query_number, results_file, info=False):
        # Parse the query based on the tag (field)
        refined_query = self.process_query_with_ner(query_text)
        query = self.parser.parse(refined_query)
        print(query)
        results = self.searcher.search(query, limit=100)  # Limit to top 100 results
        #print(query)
        # Save the results to the output file
        with open(results_file, 'a') as f:
            for i, result in enumerate(results, start=1):
                f.write(f"{query_number}\t{result.get('identity')}\n")
                if info:
                    f.write(f"Modified: {result.get('modif')}\n")
        print(f"Query {query_number} processed. {len(results)} results written to {results_file}.")


if __name__ == '__main__':
    # Default values
    index_folder = '../whooshindex'
    query_file = ''
    results_file = ''
    info = False

    # Parse command-line arguments
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '-index':
            index_folder = sys.argv[i + 1]
            i += 1
        elif sys.argv[i] == '-infoNeeds':
            query_file = sys.argv[i + 1]
            i += 1
        elif sys.argv[i] == '-output':
            results_file = sys.argv[i + 1]
            i += 1
        elif sys.argv[i] == '-info':
            info = True
        i += 1

    # Check if query_file is provided
    if not query_file:
        print("Error: You must specify a query file using the -infoNeeds argument.")
        sys.exit(1)

    if os.path.exists(results_file):
        os.remove(results_file)
    # Initialize the searcher
    searcher = MySearcher(index_folder)

    tree = ET.parse(query_file)
    root = tree.getroot()

    for need in root.findall("informationNeed"):
        identifier = need.findtext("identifier")
        text = need.findtext("text")
        searcher.search(text, identifier, results_file, info)

    print(f"Search completed. Results are stored in {results_file}.")
