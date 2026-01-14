import pandas as pd, re, numpy as np, os, unicodedata, sys

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
from keras.preprocessing.text import Tokenizer
from keras.layers import Dense, Embedding, LSTM
from keras.optimizers import Adam
from keras.models import Sequential, load_model
from keras_nlp.layers import TransformerEncoder, TokenAndPositionEmbedding
from keras.layers import Dense, GlobalAveragePooling1D
from keras.utils import to_categorical, pad_sequences, set_random_seed
import matplotlib.pyplot as plt


namespaces = {
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
    "dc": "http://purl.org/dc/elements/1.1/"
}
xpath = "/oai_dc:dc"

# Procesa una cadena de texto para eliminar simbolos de puntuación y otros caracteres no alfanumericos y acentos.
# Convierte el texto a minuscula y elimina espacios extra.
def __limpiaCadenasDeTexto(docs):
  norm_docs = []
  for doc in docs:
    doc = ''.join(c for c in unicodedata.normalize('NFD', doc) if unicodedata.category(c) != 'Mn')
    doc = re.sub(r'[^a-zA-Z0-9\s\n\t\r]', ' ', doc).lower()
    doc = re.sub(' +', ' ', doc).strip()
    norm_docs.append(doc)
  return norm_docs

# tokeniza el texto y lo conviete en vectores de longitud constante aññadiendo tokens comodin para frases cortas
# el código describe como ajustar el tamaño de los vectores generados a la cadena mas larga.
def __tokenizadorTexto(X_train, X_test):
    t = Tokenizer(oov_token='<UNK>')
    t.fit_on_texts(X_train)
    t.word_index['<PAD>'] = 0
    num_columns = int(np.max([len(row) for row in X_train]) + np.max([len(row) for row in X_test]))
    maxlen = 300
    max_num_columns = min(num_columns,maxlen)
    X_entrenT = pad_sequences(t.texts_to_sequences(X_train), maxlen=max_num_columns, padding='post')
    X_testT = pad_sequences(t.texts_to_sequences(X_test), maxlen=max_num_columns, padding='post')
    return X_entrenT, X_testT, len(t.word_index)

#Método para guardar una serie de datos con las etiquetas indicadas en los ejes
def visualizaSerieDatos(datos,etiquetaX, etiquetaY, fichero):
    plt.figure(figsize=(10, 5))
    plt.plot(datos)
    plt.xlabel(etiquetaX, fontsize=15)
    plt.ylabel(etiquetaY, fontsize=15)
    plt.savefig(fichero)

#La codificación númerica de las palabras generada por el tokenizer la transformamos al rango
#0-1 para poder pasarselo a la red
def NormalizeData(data):
    return (data - np.min(data)) / (np.max(data) - np.min(data))

# devuelve los datos de entrenamiento y test del clasificador
# lee los datos, los limpia, y tokeniza. Las categorias las convierte a one-hot.
def lecturaDatosEntrenamientoYTestClasificador(dir, numCategorias):
    dataset_entrenamiento = __leeDataFrameClasificador(dir + '/clasificacionZaguanEntrenamiento.csv')
    dataset_test = __leeDataFrameClasificador(dir + '/clasificacionZaguanTest.csv')
    X_entren = __limpiaCadenasDeTexto(dataset_entrenamiento['Text'].values)
    X_test = __limpiaCadenasDeTexto(dataset_test['Text'].values)
    X_entren, X_test, tamVoc = __tokenizadorTexto(X_entren, X_test)
    y_entren = to_categorical(dataset_entrenamiento['indice_categoria'].values -1 , num_classes=numCategorias)
    y_test = to_categorical(dataset_test['indice_categoria'].values -1 , num_classes=numCategorias )
    return (X_entren, y_entren, X_test, y_test, tamVoc)

# Método para leer los ficheros tabulares del ejercicio de clasificación de texto (clasificación, título y descripción)
# Lee un fichero en un dataframe de Pandas y junta el título con la descripción
def __leeDataFrameClasificador(file):
    df = pd.read_csv(file,sep='\t;', index_col=False, engine='python')
    df['Text'] = df['titulo'] + '. ' + df['descripcion']
    df.drop(['titulo', 'descripcion'], axis=1, inplace=True)
    return df

def procesarXML(docs_folder):
    fEntrenamiento = open('datos/clasificacionZaguanEntrenamiento.csv', 'w', encoding='utf-8')
    fEntrenamiento.write('indice_categoria\t;titulo\t;descripcion\n')
    fTest = open('datos/clasificacionZaguanTest.csv', 'w', encoding='utf-8')
    fTest.write('indice_categoria\t;titulo\t;descripcion\n')

    if (os.path.exists(docs_folder)):
            for file in sorted(os.listdir(docs_folder)):
                if file.endswith('.xml'):
                    df = pd.read_xml(docs_folder + '/' + file, xpath=xpath, namespaces=namespaces)
                    tipo = df['type'].iloc[0]
                    if tipo == "TAZ-TFG":
                        # Extraemos el título y descripción
                        titulo = df['title'].iloc[0] if 'title' in df else ''
                        descripcion = df['description'].iloc[0] if 'description' in df else ''
                        
                        # Extraemos las categorías
                        cadenas_categoria = df['subject'].dropna().tolist()

                        if len(cadenas_categoria) > 0:
                            cadenas_categoria = __limpiaCadenasDeTexto(cadenas_categoria)
                        else:
                            cadenas_categoria = ['']  
                            
                        # Buscar el índice de carrera
                        indice_carrera = -1
                        for i in range(len(string_categorias)):
                            for categoria in cadenas_categoria:
                                if any(carrera in categoria for carrera in nombre_carreras_categorias[i]):
                                    indice_carrera = i + 1
                                    break

                        # Si no se encuentra ninguna coincidencia, asignar un índice por defecto
                        if indice_carrera == -1:
                            indice_carrera = len(string_categorias)

                        # Aleatorización para decidir el archivo de salida
                        if np.random.rand() <= 0.15:
                            fTest.write(str(indice_carrera) + '\t;' + titulo + '\t;' + descripcion + '\n')
                        else:
                            fEntrenamiento.write(str(indice_carrera) + '\t;' + titulo + '\t;' + descripcion + '\n')

#Definición del modelo usado, embeddings, una red lstm, una densa para procesar el resultado del LSTM
#y una final para clasificar en las categorias deseadas
def createModelLSTM(tamVoc,tamFrase,tamEmbd,num_categorias):
    model = Sequential()
    model.add(Embedding(tamVoc, tamEmbd, input_length=tamFrase))
    model.add(LSTM(32))
    model.add(Dense(12, activation='relu'))
    model.add(Dense(num_categorias, activation='softmax'))
    model.compile(loss='CategoricalCrossentropy', optimizer=Adam(1e-4), metrics=['accuracy'])
    return model

#Definición del modelo usado, 2 capas densas y una final de clasificación en las categorias deseadas
def createModelDensa(num_categorias):
    model = Sequential()
    model.add(Dense(32, activation='relu'))
    model.add(Dense(12, activation='relu'))
    model.add(Dense(num_categorias, activation='softmax'))
    model.compile(loss='CategoricalCrossentropy', optimizer=Adam(1e-4), metrics=['accuracy'])
    return model

#Definición del modelo usado, embeddings posicionales, el encoder de un transformer,
# un pooling para aplanar la salida del transformer, una densa para procesar el resultado del LSTM
#y una final para clasificar en las categorias deseadas
def createModelTransformer(tamVoc,tamFrase,tamEmbd,num_categorias):
    model = Sequential()
    model.add(TokenAndPositionEmbedding(tamVoc, tamFrase, tamEmbd))
    model.add(TransformerEncoder(32, num_heads=3 ))
    model.add(GlobalAveragePooling1D())
    model.add(Dense(12, activation='relu'))
    model.add(Dense(num_categorias, activation='softmax'))
    model.compile(loss='CategoricalCrossentropy', optimizer=Adam(1e-4), metrics=['accuracy'])
    return model

#---------------------------------------------------------------------------------------------------------------------------------------------------------
string_categorias = ["Ciencias Sociales y Humanidades", "Ciencias de la Salud", "Ingenierías", "Ciencias y Tecnología",
                    "Arquitectura y Urbanismo", "Educación", "Ciencias Sociales y Gestión",
                    "Comunicación y Artes", "Turismo y Lenguas",
                    "Otras"]

nombre_carreras_categorias = [['arte', 'clasicos', 'filosofia', 'historia', 'filologia', 'ingleses', 'social', 'relaciones', 'laborales', 'humanos', 'periodismo', 'geografia'],
                ['terapia', 'enfermeria', 'odontologia', 'fisioterapia', 'nutricion', 'dietetica', 'veterinaria', 'psicologia', 'actividad', 'deporte', 'medicina', 'alimentos'],
                ['ingenieria', 'quimica', 'mecatronica', 'agroalimentaria', 'telecomunicacion','informatica' ,'industrial', 'electronica', 'civil', 'electrica', 'mecanica'],                
                ['biotecnologia', 'matematicas', 'fisica', 'ambientales', 'biologia', 'computacion', 'tecnologia de la informacion'],
                ['arquitectura', 'arquitectura tecnica', 'ordenacion del territorio', 'diseño de interiores','edificacion', 'urbanismo', 'paisajismo'],
                ['primaria', 'infantil', 'actividad fisica', 'psicopedagogia', 'secundaria', 'pedagogia'],
                ['empresas', 'publica', 'economia', 'finanzas', 'contabilidad', 'gestion', 'administracion', 'comercio', 'marketing', 'recursos humanos'],
                ['bellas artes', 'comunicacion', 'informacion', 'documentacion', 'diseño', 'publicidad', 'audiovisual', 'periodismo', 'moda'],
                ['lenguas', 'modernas', 'traduccion', 'interpretacion', 'turismo', 'hosteleria','cultural', 'extranjeras'],
                ['otras']]
#---------------------------------------------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    set_random_seed(0)
    zaguanDir = 'recordsdc'
    resultsDir = 'datos/resultados'
    for i in range(len(sys.argv)):
        if sys.argv[i] == '-dir':
            zaguanDir = sys.argv[i + 1]
        elif sys.argv[i] == '-output':
            resultsDir = sys.argv[i + 1]

    if not os.path.isfile('datos/clasificacionZaguanTest.csv') or not os.path.isfile('datos/clasificacionZaguanEntrenamiento.csv'):
        procesarXML(zaguanDir)

    numCategorias = len(string_categorias)
    X_entren, y_entren, X_test, y_test, tamVoc = lecturaDatosEntrenamientoYTestClasificador("datos", numCategorias)
    tamEmbd = 50
    numEpochs = 10
    pasosValidacion = 10
    batchSize = 64

    while True:
        modelo = input("Introduce el tipo de modelo (Transformer, LSTM, Densa): ")
        if modelo in ['Transformer', 'LSTM', 'Densa']:
            print(f"Has seleccionado el modelo: {modelo}")
            break  # Salir del bucle si la entrada es válida
        else:
            print("Modelo no válido. Por favor, elige entre 'Transformer', 'LSTM' o 'Densa'.")

    if modelo == 'LSTM':
        model = createModelLSTM(tamVoc,len(X_entren[0]),  tamEmbd, numCategorias)
    elif modelo == 'Transformer':
        model = createModelTransformer(tamVoc,len(X_entren[0]),  tamEmbd, numCategorias)
    else: 
        model = createModelDensa(numCategorias)
        X_entren = NormalizeData(X_entren)
        X_test = NormalizeData(X_test)

    if modelo == 'LSTM' and os.path.isfile('modelo_entrenado_clasificador_LSTM.h5'):
        model = load_model('datos/modelo_entrenado_clasificador_LSTM.h5')
    elif modelo == 'Densa' and os.path.isfile('modelo_entrenado_clasificador_densa.h5'):
        model = load_model('datos/modelo_entrenado_clasificador_Denso.h5')
    else: 
        history = model.fit(X_entren, y_entren, epochs=numEpochs, validation_steps=pasosValidacion, batch_size=batchSize , verbose=0)
        if modelo == 'LSTM':
            model.save('datos/modelo_entrenado_clasificador_LSTM.h5')
        elif modelo == 'Densa':
            model.save('datos/modelo_entrenado_clasificador_densa.h5')


            
    # Ejemplo de evaluación y clasificación
    scores = model.evaluate(X_test, y_test, verbose=0)
    print("Precisión del modelo con los test: %.2f%%" % (scores[1] * 100))
    if not os.path.exists(resultsDir):
        os.makedirs(resultsDir)  # Crea el directorio si no existe

    # Abrir el archivo en modo de escritura
    with open(resultsDir + '/precision.txt', 'w') as f:
        f.write(str(scores[1] * 100))
    f.close()

    # visualizamos la evolución del error de entrenamiento
    visualizaSerieDatos(history.history['accuracy'], 'Epoch', 'Precisión', resultsDir + '/precision.jpg')
    visualizaSerieDatos(history.history['loss'], 'Epoch', 'Error', resultsDir + '/error.jpg')

    # Obtenemos la matriz de confusion para los datos de test
    y_pred = model.predict(X_test)
    y_pred = np.argmax(y_pred, axis=1)
    y_test = np.argmax(y_test, axis=1)
    confusion = np.zeros((numCategorias, numCategorias))
    for i in range(len(y_test)):
        confusion[y_test[i]][y_pred[i]] += 1
    print('Matriz de confusión obtenida:')
    print(confusion)
    # Escribimos la matriz de confusion en un fichero
    # Abrir el archivo en modo de escritura
    with open(resultsDir + '/confusion.txt', 'w') as f:
        f.write(str(confusion))
    f.close()


