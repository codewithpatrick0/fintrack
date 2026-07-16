from pathlib import Path
import sys
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

raiz = Path(__file__).resolve().parent.parent

if str(raiz) not in sys.path:
    sys.path.append(str(raiz))

from conexion import obtener_conexion

def obtener_dataset():
    with obtener_conexion() as conexion, conexion.cursor() as cursor:
        
        consulta = """
                    SELECT t.info, c.nombre_categoria
                    FROM transacciones t 
                    JOIN categorias c ON t.id_categoria = c.id
                    WHERE c.nombre_categoria != 'Sin categoria';
                    """
        cursor.execute(consulta)
        dataset = cursor.fetchall()

        if not dataset:
            return [], []
        
        lista_x = [d[0] for d in dataset]
        lista_y = [d[1] for d in dataset]
        

        return lista_x, lista_y
    
lista_x, lista_y = obtener_dataset()
    
#Descarga de lista de stop_words en español
nltk.download('stopwords')
from nltk.corpus import stopwords

stop_words_limpio = stopwords.words('spanish')
    
vectorizador = TfidfVectorizer(lowercase=True, stop_words=stop_words_limpio)

X_train, X_test, y_train, y_test = train_test_split(
    lista_x,
    lista_y,
    test_size=0.2, 
    random_state=42,
    stratify=lista_y,
    )

X_train_vectorized = vectorizador.fit_transform(X_train)
X_test_vectorized = vectorizador.transform(X_test)

modelo_ml = MultinomialNB(alpha=1.0)

modelo_ml.fit(X_train_vectorized, y_train)

predicciones = modelo_ml.predict(X_test_vectorized)

precision_global = accuracy_score(y_test, predicciones)


print("RESUMEN")
print(f"ACCURACY GLOBAL: {precision_global:.2%}")
print(classification_report(y_test, predicciones))
print(confusion_matrix(y_test, predicciones))