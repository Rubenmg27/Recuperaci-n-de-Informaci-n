package IR.Practica5;

import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.vocabulary.RDF;
import org.w3c.dom.*;
import org.xml.sax.SAXException;

import java.io.*;
import java.util.ArrayList;
import java.util.List;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import java.io.FileOutputStream;
import java.io.IOException;


public class SemanticGenerator {

    // Definimos el espacio de nombres para las propiedades del modelo RDF
    private static final String namespace = "http://www.equipo35.com/model#";
    private static final String DC_NAMESPACE = "http://purl.org/dc/elements/1.1/";

    /** -rdf <rdf> indica la ruta del fichero RDF donde se genera
     * el grafo de la colección.
     * -docs <docsPath> indica la ruta del directorio que contiene
     * la colección de documentos a transformar.
     */
    public static void main(String args[])throws ParserConfigurationException, IOException, SAXException{
        // Valores por defecto para las rutas
        String uso = "java SemanticGenerator [-rdf <rdf>] [-docs <docsPath>]";
        //  Lo dejamos definido para correrlo en intellij
        String rdf = "coleccion.ttl";
        String docsPath = "recordsdc";

        if (args.length != 4) {
            System.err.println("Uso: " + uso);
            System.exit(1);
        }

        // Procesamos los argumentos de la línea de comandos
        for (int i = 0; i < args.length; i++) {
            if (args[i].equals("-rdf")) {
                rdf = args[++i];
            } else if (args[i].equals("-docs")) {
                docsPath = args[++i];
            }
        }
        // Mostrar las rutas procesadas
        //System.out.println("Ruta del fichero RDF: " + rdf);
        //System.out.println("Ruta del directorio de documentos: " + docsPath);

        // Generamos el modelo RDF basado en los documentos
        Model modelo = generarModelo(docsPath);

        // Escribimos el modelo en el fichero rdf
        try (FileOutputStream out = new FileOutputStream(rdf)) {
            modelo.write(out, "TURTLE");
            System.out.println("Modelo RDF generado correctamente en " + rdf);
        } catch (IOException e) {
            e.printStackTrace();
        }

    }
    // Función que nos genera el modelo que luego escribiremos en formato RDF
    public static Model generarModelo(String docsPath)throws ParserConfigurationException, IOException, SAXException{

        // Crea un modelo vacio
        Model model = ModelFactory.createDefaultModel();

        // Añadimos el espacio de nombres para que las propiedades se relacionen correctamente
        model.setNsPrefix("model", namespace);

        // Creamos las propiedades para el modelo
        model.createProperty(namespace + "language");
        model.createProperty(namespace + "date");
        model.createProperty(namespace + "title");
        model.createProperty(namespace + "subject");
        model.createProperty(namespace + "description");
        model.createProperty(namespace + "creator");
        model.createProperty(namespace + "contributor");
        model.createProperty(namespace + "publisher");
        model.createProperty(namespace + "relation");
        model.createProperty(namespace + "rights");
        model.createProperty(namespace + "Nombre");
        model.createProperty(namespace + "URL");

        // Verificamos si el directorio existe y si es válido
        File carpeta = new File(docsPath);
        if (!carpeta.isDirectory()) {
            throw new IllegalArgumentException("Path is not a directory: " + docsPath);
        }
        if (!carpeta.exists()) {
            throw new IllegalArgumentException("Directory does not exist: " + docsPath);
        }
        // Lista de archivos en el directorio
        String[] rutas = carpeta.list();
        for (String ruta : rutas) { // Recorremos los ficheros del directorio
            if (ruta.endsWith(".xml")) {
                String path = docsPath + "/" + ruta;
                xml_to_rdf(model, path);
            }
        }
        return model;
    }

    // Función que lee cada uno de los ficheros xml y lo almacena en el modelo
    public static void xml_to_rdf(Model model, String filename) throws ParserConfigurationException, IOException, SAXException {

        // Abrimos el archivo XML y lo procesamos
        FileInputStream fis = null;
        try {
            fis = new FileInputStream(filename);
        } catch (IOException e) {
            e.printStackTrace();
        }
        DocumentBuilderFactory dbFactory = DocumentBuilderFactory.newInstance();
        dbFactory.setNamespaceAware(true); // Ensure namespace awareness
        DocumentBuilder dBuilder = dbFactory.newDocumentBuilder();
        Document doc = dBuilder.parse(fis);

        doc.getDocumentElement().normalize();

        // Obtenemos el elemento raíz del XML
        Element root = doc.getDocumentElement();

        // Extraemos los campos del XML utilizando métodos auxiliares
        String documentoID = cargarCampo(root, "identifier");
        String type = cargarCampo(root,"type");
        List<String> language = cargarCampoLista(root,"language");
        String date = cargarCampo(root,"date");
        String title = cargarCampo(root,"title");
        List<String> subject = cargarCampoLista(root,"subject");
        String description = cargarCampo(root,"description");
        List<String> creator = cargarCampoLista(root,"creator");
        List<String> contributor = cargarCampoLista(root,"contributor");
        String publisher = cargarCampo(root,"publisher");
        List<String> relation = cargarCampoLista(root,"relation");
        List<String> rights = cargarCampoLista(root,"rights");

        // Creamos el recurso RDF para este documento
        Resource documento = model.createResource(documentoID);

        // Asignamos los valores:

        // Type
        if (type.equals("TAZ-TFG")) {
            documento.addProperty(RDF.type, model.createResource(namespace + "TAZ-TFG"));
        } else if (type.equals("TAZ-TFM")) {
            documento.addProperty(RDF.type,model.createResource(namespace + "TAZ-TFM"));
        } else if (type.equals("TAZ-PFC")) {
            documento.addProperty(RDF.type,model.createResource(namespace + "TAZ-PFC"));
        } else if (type.equals("TESIS")) {
            documento.addProperty(RDF.type,  model.createResource(namespace + "TESIS"));
        }

        // Language
        for (String i : language) {
            propiedadLiteral(model, documento, "language", i);
        }
        // Date
        if (date != null) {
            documento.addProperty(model.getProperty(namespace + "date"), model.createTypedLiteral(date, "http://www.w3.org/2001/XMLSchema#integer"));
        }
        // Title
        propiedadLiteral(model, documento, "title", title);
        // Subject
        for (String i : subject) {
            propiedadLiteral(model, documento, "subject", i);
        }
        // Description
        propiedadLiteral(model, documento, "description", description);
        // Creator
        for (String i : creator) {
            propiedadCompleja(model, documento, "creator", i, namespace + "personClass", model.getProperty(namespace + "Nombre"));
        }
        // Contributor
        for (String i : contributor) {
            propiedadCompleja(model, documento, "contributor", i, namespace + "personClass", model.getProperty(namespace + "Nombre"));
        }
        // Publisher
        propiedadLiteral(model, documento, "publisher", publisher);
        // Relation
        for (String i : relation) {
            propiedadCompleja(model, documento, "relation", i, namespace + "urlClass", model.getProperty(namespace + "URL"));
        }
        // Rights
        for (String i : rights) {
            propiedadCompleja(model, documento, "rights", i, namespace + "urlClass", model.getProperty(namespace + "URL"));
        }
    }

    // Carga un campo del documento XML que tiene un solo valor
    private static String cargarCampo(Element root, String campo) {
        String valor = null;
        NodeList nl = root.getElementsByTagNameNS(DC_NAMESPACE,campo);
        if (nl.getLength() > 0) {
            valor = nl.item(0).getTextContent();
        }
        return valor;
    }

    // Carga un campo del documento XML que puede tener varios valores
    private static List<String> cargarCampoLista(Element root, String campo) {
        List<String> valores = new ArrayList<>();
        NodeList nl = root.getElementsByTagNameNS(DC_NAMESPACE,campo);
        for (int i = 0; i < nl.getLength(); i++) {
            valores.add(nl.item(i).getTextContent());
        }
        return valores;
    }

    // Añade una propiedad compleja al documento, es decir, que no tomará el valor de un literal
    public static void propiedadCompleja(Model model, Resource documento, String propiedad, String valor, String claseRecurso, Property propiedadRecurso) {
        if (valor != null) {
            Resource recurso = model.createResource(claseRecurso);
            Resource valorRecurso = model.createResource(namespace + limpiarURI(valor));
            valorRecurso.addProperty(RDF.type, recurso);
            valorRecurso.addProperty(propiedadRecurso, model.createLiteral(valor));
            documento.addProperty(model.getProperty(namespace + propiedad), valorRecurso);
        }
    }

    // Añade una propiedad literal al documento
    public static void propiedadLiteral(Model model, Resource documento, String propiedad, String valor) {
        if (valor != null) {
            documento.addProperty(model.getProperty(namespace + propiedad), model.createLiteral(valor));
        }
    }

    // Limpia la uri para que no contenga caracteres no permitidos
    private static String limpiarURI(String uri) {
        uri = uri.replace(" ", "-").replace("\u00E1", "a").replace("\u00C1", "a")
                .replace("\u00E9", "e").replace("\u00C9", "e")
                .replace("\u00ED", "i").replace("\u00CD", "i")
                .replace("\u00F3", "o").replace("\u00D3", "o")
                .replace("\u00FA", "u").replace("\u00DA", "u")
                .replace("\u00F1", "gn").replace("\u00D1", "gn")
                .replace("\u00E7", "c").replace("\u00C7", "c")
                .replace(",", "").replace(".", "");
        uri = uri.toLowerCase();
        for (int i = 0; i < uri.length(); i++) {
            int ascii = (int) uri.charAt(i);
            if (uri.charAt(i) != '-' && (ascii < 48 || (ascii > 57 && ascii < 97) || ascii > 122)) {
                uri = uri.replace(uri.charAt(i)+"", "");
            }
        }
        return uri;
    }

}