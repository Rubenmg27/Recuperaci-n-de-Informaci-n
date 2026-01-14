import sys
import matplotlib.pyplot as plt
from collections import defaultdict
import numpy as np

# Función que lee el archivo de relevancia (qrels)
# Carga un diccionario con las necesidades de información como claves y otro diccionario 
# como valor que almacena las ID de documentos junto con su relevancia (1 si es relevante, 0 si no).
def load_qrels(qrels_file):
    qrels = defaultdict(lambda: defaultdict(int))
    with open(qrels_file, 'r') as f:
        for line in f:
            info_need, doc_id, relevance = line.strip().split('\t')
            qrels[info_need][doc_id] = int(relevance)
    return qrels

# Función que carga los resultados obtenidos
# Se lee un archivo donde se listan las ID de documentos recuperados para cada necesidad de información.
# Limita a 45 el número de documentos leídos por necesidad de información.
def load_results(results_file):
    results = defaultdict(list)
    counts = defaultdict(int)  # Lleva el conteo de cada necesidad de información

    with open(results_file, 'r') as f:
        for line in f:
            info_need, doc_id = line.strip().split('\t')
            
            # Verifica que se hayan leído menos de 45 documentos para la necesidad de información
            if counts[info_need] < 45:
                results[info_need].append(doc_id)
                counts[info_need] += 1  # Incrementa el conteo para esa necesidad

    return results

# Calcula la precisión en los primeros 10 documentos recuperados
def compute_prec_at_10(relevant_docs, retrieved_docs):
    top_10_retrieved = retrieved_docs[:10]
    relevant_in_top_10 = sum(1 for doc_id in top_10_retrieved if relevant_docs.get(doc_id, 0) == 1)
    return relevant_in_top_10 / 10.0

# Calcula la precisión promedio para una consulta dada
# Promedia las precisiones en cada posición de documentos relevantes.
def compute_avg_precision(relevant_docs, retrieved_docs):
    cum_relevant, total_precisions = 0, 0.0
    for idx, doc_id in enumerate(retrieved_docs, start=1):
        if relevant_docs.get(doc_id, 0) == 1:  # Si el documento es relevante
            cum_relevant += 1
            precision_at_k = cum_relevant / idx  # Precisión en la posición `idx`
            total_precisions += precision_at_k  # Suma la precisión en cada posición de doc relevante
    return total_precisions / cum_relevant if cum_relevant > 0 else 0.0

# Calcula la curva de precisión-recall
def compute_recall_precision_curve(relevant_docs, retrieved_docs):
    recall_precision_points = []
    cum_relevant, total_relevant = 0, sum(relevant_docs.values())
    for idx, doc_id in enumerate(retrieved_docs, start=1):
        if relevant_docs.get(doc_id, 0) == 1:
            cum_relevant += 1
            recall = cum_relevant / total_relevant
            precision = cum_relevant / idx
            recall_precision_points.append((recall, precision))
    return recall_precision_points

# Interpolación de la curva de precisión-recall
# Genera precisión interpolada en 11 niveles de recall de 0.0 a 1.0
def interpolate_recall_precision(recall_precision_points):
    recall_levels = np.linspace(0.0, 1.0, 11)
    interpolated_precision = []
    for recall_level in recall_levels:
        precisions_at_recall = [p for r, p in recall_precision_points if r >= recall_level]
        max_precision = max(precisions_at_recall) if precisions_at_recall else 0
        interpolated_precision.append((recall_level, max_precision))
    return interpolated_precision

# Calcula varias métricas de evaluación para cada necesidad de información y el total
def compute_metrics(qrels, results):
    metrics = defaultdict(dict)
    global_precision_sum, global_recall_sum, global_prec_at_10, global_avg_precision = 0, 0, 0, 0
    interpolated_precision_points = np.zeros(11)

    for info_need, retrieved_docs in results.items():
        relevant_docs = qrels[info_need]
        retrieved_relevant = sum(1 for doc_id in retrieved_docs if relevant_docs.get(doc_id, 0) == 1)
        relevant_count = sum(relevant_docs.values())
        
        precision = retrieved_relevant / len(retrieved_docs) if retrieved_docs else 0
        recall = retrieved_relevant / relevant_count if relevant_count else 0
        f1 = (2 * precision * recall) / (precision + recall) if precision + recall > 0 else 0
        prec_at_10 = compute_prec_at_10(relevant_docs, retrieved_docs)
        avg_precision = compute_avg_precision(relevant_docs, retrieved_docs)
        
        recall_precision_points = compute_recall_precision_curve(relevant_docs, retrieved_docs)
        interpolated_points = interpolate_recall_precision(recall_precision_points)
        interpolated_precision_points += np.array([p for _, p in interpolated_points])

        metrics[info_need] = {
            'precision': precision,
            'recall': recall,
            'F1': f1,
            'prec@10': prec_at_10,
            'average_precision': avg_precision,
            'recall_precision': recall_precision_points,
            'interpolated_recall_precision': interpolated_points
        }

        global_precision_sum += precision
        global_recall_sum += recall
        global_prec_at_10 += prec_at_10
        global_avg_precision += avg_precision

    global_precision = global_precision_sum / len(results) if len(results) > 0 else 0
    global_recall = global_recall_sum / len(results) if len(results) > 0 else 0
    global_f1 = (2 * global_precision * global_recall) / (global_precision + global_recall) if global_precision + global_recall > 0 else 0
    global_interpolated_precision = interpolated_precision_points / len(results)
    
    metrics['TOTAL'] = {
        'precision': global_precision,
        'recall': global_recall,
        'F1': global_f1,
        'prec@10': global_prec_at_10 / len(results) if len(results) > 0 else 0,
        'MAP': global_avg_precision / len(results) if len(results) > 0 else 0,
        'interpolated_recall_precision': [(r, p) for r, p in zip(np.linspace(0.0, 1.0, 11), global_interpolated_precision)]
    }
    return metrics

# Genera el archivo de salida con las métricas de evaluación calculadas
def generate_output(metrics, output_file):
    with open(output_file, 'w') as f:
        for info_need, metric_values in metrics.items():
            if info_need=='TOTAL':
                f.write(f"{info_need}\n")
            else:
                f.write(f"INFORMATION_NEED {info_need}\n")
            
            for metric, value in metric_values.items():
                if isinstance(value, list):
                    f.write(f"{metric}\n")
                    for r, p in value:
                        f.write(f"{r:.3f}\t{p:.3f}\n")
                else:
                    f.write(f"{metric}\t{value:.3f}\n")
            f.write("\n")

# Grafica la curva interpolada de precisión-recall
def plot_precision_recall(metrics,nombre):
    for info_need, metric_values in metrics.items():
        if info_need != 'TOTAL':
            recall_precision = metric_values['interpolated_recall_precision']
            recall_vals, precision_vals = zip(*recall_precision)
            plt.plot(recall_vals, precision_vals, label=f'Information Need {info_need}')
    
    global_recall_precision = metrics['TOTAL']['interpolated_recall_precision']
    recall_vals, precision_vals = zip(*global_recall_precision)
    plt.plot(recall_vals, precision_vals, 'k--', label='TOTAL', linewidth=2)

    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Interpolated Precision-Recall Curve")
    plt.legend()

    # Guarda la gráfica en un archivo llamado 'grafica.png'
    plt.savefig(nombre)
    plt.close()  # Cierra la gráfica para evitar mostrarla

# Grafica la curva interpolada de precisión-recall para comparar las totales
def plot_precision_recall_total_comparar(metricsA,metricsB,metricsNuestro,nombre):

    global_recall_precisionA = metricsA['TOTAL']['interpolated_recall_precision']
    recall_valsA, precision_valsA = zip(*global_recall_precisionA)
    plt.plot(recall_valsA, precision_valsA, 'gray', label='A', linewidth=2)

    global_recall_precisionB = metricsB['TOTAL']['interpolated_recall_precision']
    recall_valsB, precision_valsB = zip(*global_recall_precisionB)
    plt.plot(recall_valsB, precision_valsB, 'blue', label='B', linewidth=2)

    global_recall_precisionN = metricsNuestro['TOTAL']['interpolated_recall_precision']
    recall_valsN, precision_valsN = zip(*global_recall_precisionN)
    plt.plot(recall_valsN, precision_valsN, 'red', label='Nuestro', linewidth=2)

    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Interpolated Precision-Recall Curve")
    plt.legend()

    # Guarda la gráfica en un archivo llamado 'grafica.png'
    plt.savefig(nombre)
    plt.close()  # Cierra la gráfica para evitar mostrarla


if __name__ == "__main__":
    qrels_file, results_file, output_file = None, None, None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '-qrels':
            qrels_file = sys.argv[i + 1]
            i += 1
        elif sys.argv[i] == '-results':
            results_file = sys.argv[i + 1]
            i += 1
        elif sys.argv[i] == '-output':
            output_file = sys.argv[i + 1]
            i += 1
        i += 1

    qrels = load_qrels(qrels_file)
    results = load_results(results_file)
    metrics = compute_metrics(qrels, results)
    resultsA = load_results("resultados_sistema_a.txt")
    resultsB = load_results("resultados_sistema_b.txt")
    resultsN = load_results("equipo35.txt")
    metricsA = compute_metrics(qrels, resultsA)
    metricsB = compute_metrics(qrels, resultsB)
    metricsN = compute_metrics(qrels, resultsN)
    generate_output(metrics, output_file)
    plot_precision_recall(metrics,"grafica.png")
    plot_precision_recall_total_comparar(metricsA,metricsB,metricsN,"comparar.png")
