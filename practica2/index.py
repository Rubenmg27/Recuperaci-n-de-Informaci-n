"""
index.py
Author: Javier Nogueras Iso
Last update: 2024-09-07

Simple program to create an inverted index with the contents of text/xml files contained in a docs folder
This program is based on the whoosh library. See https://pypi.org/project/Whoosh/ .
Usage: python index.py -index <index folder> -docs <docs folder>
"""

from whoosh.index import create_in
from whoosh.fields import *
from datetime import datetime
from whoosh.analysis import RegexTokenizer, LowercaseFilter, StopFilter, Filter
from nltk.stem.snowball import SnowballStemmer


import os

import xml.etree.ElementTree as ET

spanish_stopwords = [
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por",
    "un", "para", "con", "no", "una", "su", "al", "lo", "como", "más", "pero", 
    "sus", "le", "ya", "o", "este", "sí", "porque", "esta", "entre", "cuando", 
    "muy", "sin", "sobre", "también", "me", "hasta", "hay", "donde", "quien", 
    "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni", "contra", 
    "otros", "ese", "eso", "ante", "ellos", "e", "esto", "mí", "antes", "algunos", 
    "qué", "unos", "yo", "otro", "otras", "otra", "él", "tanto", "esa", "estos", 
    "mucho", "quienes", "nada", "muchos", "cual", "poco", "ella", "estar", 
    "estas", "algunas", "algo", "nosotros", "mi", "mis", "tú", "te", "ti", 
    "tu", "tus", "ellas", "nosotras", "vosotros", "vosotras", "os", "mío", 
    "mía", "míos", "mías", "tuyo", "tuya", "tuyos", "tuyas", "suyo", "suya", 
    "suyos", "suyas", "nuestro", "nuestra", "nuestros", "nuestras", "vuestro", 
    "vuestra", "vuestros", "vuestras", "esos", "esas", "estoy", "estás", 
    "está", "estamos", "estáis", "están", "esté", "estés", "estemos", "estéis", 
    "estén", "estaré", "estarás", "estará", "estaremos", "estaréis", "estarán", 
    "estaría", "estarías", "estaríamos", "estaríais", "estarían", "estaba", 
    "estabas", "estábamos", "estabais", "estaban", "estuve", "estuviste", 
    "estuvo", "estuvimos", "estuvisteis", "estuvieron", "estuviera", 
    "estuvieras", "estuviéramos", "estuvierais", "estuvieran", "estuviese", 
    "estuvieses", "estuviésemos", "estuvieseis", "estuviesen", "estando", 
    "estado", "estada", "estados", "estadas", "estad"
]


def create_folder(folder_name):
    if (not os.path.exists(folder_name)):
        os.mkdir(folder_name)

class Stemming(Filter):
    def __init__(self, language="spanish"):
        self.stemmer = SnowballStemmer(language)

    def __call__(self, tokens):
        for token in tokens:
            token.text = self.stemmer.stem(token.text)  
            yield token



class MyIndex:
    def __init__(self,index_folder):
        
        schema = Schema(
            path=ID(stored=True), 
            creator=TEXT(analyzer = RegexTokenizer(expression=r"\w+") | LowercaseFilter() | StopFilter(spanish_stopwords) | Stemming()),
            contributor=TEXT(analyzer = RegexTokenizer(expression=r"\w+") | LowercaseFilter() | StopFilter(spanish_stopwords) | Stemming()),
            publisher=TEXT(analyzer = RegexTokenizer(expression=r"\w+") | LowercaseFilter() | StopFilter(spanish_stopwords) | Stemming()),
            title=TEXT(analyzer = RegexTokenizer(expression=r"\w+") | LowercaseFilter() | StopFilter(spanish_stopwords) | Stemming()),
            description=TEXT(analyzer = RegexTokenizer(expression=r"\w+") | LowercaseFilter() | StopFilter(spanish_stopwords) | Stemming()),
            subject=TEXT(analyzer = RegexTokenizer(expression=r"\w+") | LowercaseFilter() | StopFilter(spanish_stopwords) | Stemming()),
            date=TEXT(analyzer = RegexTokenizer(expression=r"\w+") | LowercaseFilter() | StopFilter(spanish_stopwords) | Stemming()),
            modif=STORED,
            identity=STORED
        )
        create_folder(index_folder)
        index = create_in(index_folder, schema)
        self.writer = index.writer()

    def index_docs(self,docs_folder):
        if (os.path.exists(docs_folder)):
            for file in sorted(os.listdir(docs_folder)):
                # print(file)
                if file.endswith('.xml'):
                    tags = {
                        'dc:creator': '{http://purl.org/dc/elements/1.1/}creator',
                        'dc:contributor': '{http://purl.org/dc/elements/1.1/}contributor',
                        'dc:publisher': '{http://purl.org/dc/elements/1.1/}publisher',
                        'dc:title': '{http://purl.org/dc/elements/1.1/}title',
                        'dc:description': '{http://purl.org/dc/elements/1.1/}description',
                        'dc:subject': '{http://purl.org/dc/elements/1.1/}subject',
                        'dc:date': '{http://purl.org/dc/elements/1.1/}date',
                        'dc:identifier': '{http://purl.org/dc/elements/1.1/}identifier',
                    }
                    self.index_xml_doc(docs_folder, file,tags)
                elif file.endswith('.txt'):
                    self.index_txt_doc(docs_folder, file)
        self.writer.commit()

    def index_txt_doc(self, foldername,filename):
        file_path = os.path.join(foldername, filename)
        # print(file_path)
        with open(file_path) as fp:
            text = ' '.join(line for line in fp if line)
            modified_date = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%a, %d %b %Y %H:%M:%S +0000')
        # print(text)
        self.writer.add_document(path=filename, content=text, modif=modified_date)

    def index_xml_doc(self, foldername, filename, tags):
        file_path = os.path.join(foldername, filename)
        # print(file_path)
        tree = ET.parse(file_path)
        root = tree.getroot()
        #raw_text = "".join(root.itertext())
        raw_text = { tag: "" for tag in tags}

        for field, full_tag in tags.items():
            for text in root.findall(full_tag):
                raw_text[field] += (text.text or "" ).strip() + " "
        # break into lines and remove leading and trailing space on each
        #text = ' '.join(line.strip() for line in raw_text.splitlines() if line)
        modified_date = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%a, %d %b %Y %H:%M:%S +0000')
        # print(text)
        self.writer.add_document(
            path=filename,
            creator=raw_text.get('dc:creator',''),
            contributor=raw_text.get('dc:contributor',''),
            publisher=raw_text.get('dc:publisher',''),
            title=raw_text.get('dc:title',''),
            description=raw_text.get('dc:description',''),
            subject=raw_text.get('dc:subject',''),
            date=raw_text.get('dc:date',''),
            modif=modified_date,
            identity=raw_text.get('dc:identifier')
        )
    

if __name__ == '__main__':

    index_folder = '../whooshindex'
    docs_folder = '../docs'
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '-index':
            index_folder = sys.argv[i + 1]
            i = i + 1
        elif sys.argv[i] == '-docs':
            docs_folder = sys.argv[i + 1]
            i = i + 1
        i = i + 1

    my_index = MyIndex(index_folder)
    my_index.index_docs(docs_folder)


