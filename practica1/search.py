"""
search.py
Author: Sergio Salesa y Rubén Martín
Last update: 2024-09-25

Program to search a free text query on a previously created inverted index.
This program is based on the whoosh library. See https://pypi.org/project/Whoosh/ .
Usage: python search.py -index <index folder>
"""

import sys
import os

from whoosh.qparser import QueryParser
from whoosh.qparser import OrGroup
from whoosh import scoring
import whoosh.index as index
from nltk.stem.snowball import SnowballStemmer
from whoosh.analysis import Filter

# Se ha creado la clase Stemming con la clase Filter, la cual aplicará el SnowballStemming en el analyzer
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
        # Se ha creado el parser con cada uno de los campos que queremos preguntar
        self.parser = {
            'creator': QueryParser("creator", ix.schema, group = OrGroup),
            'contributor': QueryParser("contributor", ix.schema, group = OrGroup),
            'publisher': QueryParser("publisher", ix.schema, group = OrGroup),
            'title': QueryParser("title", ix.schema, group = OrGroup),
            'description': QueryParser("descripcion", ix.schema, group = OrGroup),
            'subject': QueryParser("subject", ix.schema, group = OrGroup),
            'date': QueryParser("date", ix.schema, group = OrGroup)
        }

    def search(self, tag, query_text, query_number, results_file, info=False):
        # Parse the query based on the tag (field)
        query = self.parser.get(tag, self.parser['title']).parse(query_text)
        results = self.searcher.search(query, limit=100)  # Limit to top 100 results
        #print(query)
        # Save the results to the output file
        # Creamos el fichero donde se guardarán los resultados de las consultas
        with open(results_file, 'a') as f:
            f.write(f"Query {query_number} - {tag}: {query_text}\n")
            for i, result in enumerate(results, start=1):
                f.write(f"{query_number}\t{result.get('identity')}\n")
                if info:
                    f.write(f"Modified: {result.get('modif')}\n")
        print(f"Query {query_number} procesada. {len(results)} resultados escritos en {results_file}.")


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

    # Si existe el fichero donde se van a guardar los resultados lo borramos
    if os.path.exists(results_file):
        os.remove(results_file)
    # Initialize the searcher
    searcher = MySearcher(index_folder)

    # Open and process the query file
    with open(query_file, 'r') as file:
        for query_number, line in enumerate(file, start=1):
            tag, query = line.split(":", 1)
            searcher.search(tag,query,query_number,results_file, info)

    print(f"Busqueda completada, los resultados están en {results_file}.")
