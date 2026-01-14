package IR.Practica5;

import org.apache.commons.io.FileUtils;
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.*;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.tdb2.TDB2Factory;
import org.apache.jena.query.text.EntityDefinition;
import org.apache.jena.query.text.TextDatasetFactory;
import org.apache.jena.query.text.TextIndexConfig;


import java.io.*;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.io.File;

import org.apache.lucene.analysis.es.SpanishAnalyzer;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.MMapDirectory;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.w3c.dom.Document;
import org.xml.sax.SAXException;


import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;



// Clase que carga el modelo RDF de la colección de documentos y realiza las consultas
public class SemanticSearcher {

    public static final String NP = "http://www.equipo35.com/model#";

    /** -rdf <rdfPath> ruta del fichero RDF que contiene la colección de recursos.
     * -infoNeeds <infoNeedsFile> permite indicar la ruta del fichero que
     *  contiene las necesidades de información.
     *  -output <resultsFile> permite indicar la ruta del fichero donde se
     *  generarán los resultados del sistema para las necesidades de información siguiendo
     *  el mismo formato que el utilizado para los ficheros de resultados del sistema tradicional.
     */
	public static void main (String args[]) throws Exception {
        // Definición del uso de parámetros para el programa
        String uso = "java SemanticSearcher [-rdf <rdf>] [-infoNeeds <infoNeedsFile>] [-output <resultsFile>]";
        // lo dejamos definido para correrlo en intellij
        String rdfPath = "coleccion.ttl";
        String infoNeedsFile = "necesidadesInformacionElegidas.txt";
        String resultsFile = "semanticResults35.txt";

        if (args.length != 6) {
            System.err.println("Uso: " + uso);
            System.exit(1);
        }

        // Procesamiento de los argumentos de la línea de comandos
        for (int i = 0; i < args.length; i++) {
            if (args[i].equals("-rdf")) {
                rdfPath = args[++i];
            } else if (args[i].equals("-infoNeeds")) {
                infoNeedsFile = args[++i];
            } else if (args[i].equals("-output")) {
                resultsFile = args[++i];
            }
        }
        //Llama al método que ejecuta las necesidades de información
        ejecutarNecesidadesInfo(infoNeedsFile,rdfPath,resultsFile);
    }

    // Método que procesa las necesidades de información
    public static void ejecutarNecesidadesInfo(String infoNeedsFile, String rdfPath, String resultsFile) throws ParserConfigurationException, IOException, SAXException {

        // Carga el archivo XML de necesidades de información
        File xmlFile = new File(infoNeedsFile);
        if (!xmlFile.exists()) {
            System.out.println("El fichero proporcionado no existe");
            System.exit(0);
        }

        // Parseamos el fichero XML, en UTF-8 para que no haya problemas con las tildes
        DocumentBuilderFactory dbFactory = DocumentBuilderFactory.newInstance();
        DocumentBuilder dBuilder = dbFactory.newDocumentBuilder();
        Document doc = dBuilder.parse(xmlFile);
        doc.getDocumentElement().normalize();

        // Configura el índice para la búsqueda semántica
        TextIndexConfig config = configureIndex();
        // Prepara la base de datos y carga el modelo RDF
        Dataset ds = setUpDataBase(rdfPath,config);

        PrintWriter pWriter = new PrintWriter(new FileOutputStream(resultsFile));

        // Recorre cada necesidad de información en el archivo XML
        NodeList nl = doc.getElementsByTagName("informationNeed");
        List<String> resultados;
        for (int i = 0; i < nl.getLength(); i++) { // Recorremos las necesidades de información
            Node text = ((Element)nl.item(i)).getElementsByTagName("text").item(0);
            String id = ((Element)nl.item(i)).getElementsByTagName("identifier").item(0).getTextContent();
            String queryString = limpiarQuery(text.getTextContent());
            resultados = executeQuery(ds, id, queryString);
            escribirRes(pWriter, resultados);
        }
        pWriter.close();

        // Muestra mensaje indicando que los resultados han sido generados
        System.out.println("Se han generado los resultados en el fichero " + resultsFile);
    }

    // Configura el índice para la búsqueda semántica en Jena
    public static TextIndexConfig configureIndex() throws IOException {

        // Definición de las entidades que se indexarán (campos de RDF)
        EntityDefinition entDef = new EntityDefinition("uri", "type",
                 ResourceFactory.createProperty(NP,"type"));
        entDef.set("language", ResourceFactory.createProperty(NP,"language").asNode());
        entDef.set("date", ResourceFactory.createProperty(NP,"date").asNode());
        entDef.set("title", ResourceFactory.createProperty(NP,"title").asNode());
        entDef.set("subject", ResourceFactory.createProperty(NP,"subject").asNode());
        entDef.set("description", ResourceFactory.createProperty(NP,"description").asNode());
        entDef.set("creator", ResourceFactory.createProperty(NP,"creator").asNode());
        entDef.set("contributor", ResourceFactory.createProperty(NP,"contributor").asNode());
        entDef.set("publisher", ResourceFactory.createProperty(NP,"publisher").asNode());

        // Configura el índice con un analizador en español
        TextIndexConfig config = new TextIndexConfig(entDef);
        config.setAnalyzer(new SpanishAnalyzer());
        config.setQueryAnalyzer(new SpanishAnalyzer());
        config.setMultilingualSupport(true);

        return config;
    }


    // Configura y carga la base de datos (modelo RDF y texto indexado)
    public static Dataset setUpDataBase(String rdfPath, TextIndexConfig config) throws IOException {

        // Elimina directorio previo para la base de datos
        FileUtils.deleteDirectory(new File("repositorio"));
        Dataset ds1 = TDB2Factory.connectDataset("repositorio/tdb2");

        // Crea el índice de Lucene
        Directory dir =  new MMapDirectory(Paths.get("./repositorio/lucene"));
        Dataset ds = TextDatasetFactory.createLucene(ds1, dir, config) ;

        // Inicia la transacción de escritura
        ds.begin(ReadWrite.WRITE) ;
        // Lee el modelo RDF en la base de datos
        RDFDataMgr.read(ds.getDefaultModel(), rdfPath) ;
        // Commit de la transacción
        ds.commit();
        ds.end();

        return ds;
    }

    // Limpia el string de la consulta para que no haya problemas con las tildes
    public static String limpiarQuery(String query){
        String resultado = query.trim();
        // Cambiamos las codificaciones de las tildes
        resultado = resultado.replaceAll("\u00f3", "ó");
        resultado = resultado.replaceAll("\u00fa", "ú");
        resultado = resultado.replaceAll("\u00f1", "ñ");
        resultado = resultado.replaceAll("\u00d1", "Ñ");
        resultado = resultado.replaceAll("\u00e1", "á");
        resultado = resultado.replaceAll("\u00e9", "é");
        resultado = resultado.replaceAll("\u00ed", "í");
        
        return resultado;
    }

    // Ejecuta la consulta sobre el conjunto de datos y obtiene los resultados
    public static List<String> executeQuery(Dataset conjuntoDatos, String id, String queryString){
        List<String> resultados = new ArrayList<String>();
        conjuntoDatos.begin(ReadWrite.READ);
        try {
            // Crea la consulta SPARQL
            Query query = QueryFactory.create(queryString);
            // Ejecuta la consulta sobre el conjunto de datos
            QueryExecution qexec = QueryExecutionFactory.create(query, conjuntoDatos);
            // Obtenemos los resultados
            ResultSet results = qexec.execSelect();
            // Recorremos los resultados
            while (results.hasNext()) {
                QuerySolution qSol = results.nextSolution();
                // Obtenemos el recurso del documento en el resultado
                Resource documento = qSol.getResource("x");
                // Almacenamos el documento y su ID en la lista de resultados
                resultados.add(id + "\t" + documento.getURI());
            }
            qexec.close();
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            conjuntoDatos.end();
        }
        return resultados;
    }

    // Escribe los resultados de la consulta en el archivo de salida
    public static void escribirRes(PrintWriter pWriter, List<String> res){
        for (String resultado : res) pWriter.println(resultado);
    }



}
