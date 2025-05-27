# horarios_adif.py
# (Contenido de tu script de scraping, asegurándote de que get_horarios
# es una función que acepta station_code y traffic_type_value,
# y que los diccionarios STATION_URL_NAMES y TRAFFIC_TYPES están definidos
# y exportados/accesibles para main.py)

import requests
from bs4 import BeautifulSoup
import time
import random

# Definiciones de estaciones y tipos de tráfico (deben coincidir con el frontend)
STATION_URL_NAMES = {
    "13106": "llodio",
    "70100": "vicálvaro",
    # Añade aquí todas las estaciones que quieras soportar con su código ADIF y su nombre para la URL
    "05001": "madrid-atocha", # Ejemplo
    "05002": "madrid-chamartin", # Ejemplo
}

TRAFFIC_TYPES = {
    "1": {"name": "Todos", "value": "all"},
    "2": {"name": "Cercanías", "value": "cercanias"},
    "3": {"name": "AV/LD/MD", "value": "avldmd"},
    "4": {"name": "Mercancías", "value": "m"},
    "5": {"name": "Sin Parada", "value": "sp"},
    "6": {"name": "Sin Parada2", "value": "sinparada"}, # Corregido de 'sinparada' a 'sp' si tu web lo usa así
}

def get_horarios(station_code, traffic_type_value, max_retries=3, delay=1):
    """
    Obtiene los horarios de trenes de una estación específica y tipo de tráfico.

    Args:
        station_code (str): Código ADIF de la estación.
        traffic_type_value (str): Valor del tipo de tráfico (ej. 'all', 'cercanias').
        max_retries (int): Número máximo de intentos si la petición falla.
        delay (int): Retraso en segundos entre reintentos.

    Returns:
        list: Una lista de diccionarios con los horarios, o None si falla.
    """
    station_name = STATION_URL_NAMES.get(station_code)
    if not station_name:
        print(f"Error: Código de estación '{station_code}' no encontrado.")
        return None

    base_url = "https://www.adif.es/w/trafico-y-estaciones/horarios-estaciones"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'es-ES,es;q=0.9',
        'Referer': 'https://www.adif.es/w/trafico-y-estaciones/horarios-estaciones',
        'X-Requested-With': 'XMLHttpRequest', # A veces es necesario para APIs que esperan AJAX
    }

    retries = 0
    while retries < max_retries:
        try:
            # Construcción de la URL de la estación específica
            full_url = f"{base_url}?station={station_name}&traffic={traffic_type_value}"
            print(f"Intentando obtener horarios de: {full_url}")

            response = requests.get(full_url, headers=headers, timeout=10)
            response.raise_for_status() # Lanza una excepción si la respuesta no es 200 OK

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar la tabla de horarios
            # Asegúrate de que el selector CSS para la tabla sea correcto para la web de ADIF
            horarios_div = soup.find('div', class_='train-schedules-data') # Puede que necesites ajustar esto
            if not horarios_div:
                print(f"Advertencia: No se encontró el div de horarios para {station_name} {traffic_type_value}.")
                return [] # Retorna lista vacía si no encuentra el contenedor

            horarios_list = []
            # Buscar filas de la tabla (ajusta el selector si es necesario)
            # Esto es un ejemplo, deberás ajustarlo a la estructura HTML real de la tabla de ADIF
            rows = horarios_div.find_all('div', class_='train-schedule-item') # O 'tr' si es una tabla HTML
            
            if not rows:
                print(f"No se encontraron filas de horarios dentro del div para {station_name} {traffic_type_value}.")
                return []

            for row in rows:
                # Extrae los datos de cada columna (ajusta los selectores CSS/clases según la web real)
                # Estos son ejemplos. DEBES verificar los nombres de las clases o IDs de los elementos
                # que contienen la hora, estación, vía y tren en la página de ADIF.
                try:
                    hora = row.find(class_='schedule-time').get_text(strip=True) if row.find(class_='schedule-time') else 'N/A'
                    estacion = row.find(class_='schedule-station').get_text(strip=True) if row.find(class_='schedule-station') else 'N/A'
                    via = row.find(class_='schedule-track').get_text(strip=True) if row.find(class_='schedule-track') else 'N/A'
                    tren = row.find(class_='schedule-train-id').get_text(strip=True) if row.find(class_='schedule-train-id') else 'N/A'
                    
                    horarios_list.append({
                        'hora': hora,
                        'estacion': estacion,
                        'via': via,
                        'tren': tren
                    })
                except Exception as e:
                    print(f"Error al parsear una fila de horario: {e}. Fila: {row.prettify()}")
                    continue # Continúa con la siguiente fila si hay un error en una

            return horarios_list

        except requests.exceptions.RequestException as e:
            print(f"Error de red o HTTP al intentar obtener horarios para {station_name}: {e}")
            retries += 1
            if retries < max_retries:
                print(f"Reintentando en {delay} segundos... (Intento {retries}/{max_retries})")
                time.sleep(delay + random.uniform(0, 1)) # Retraso con un poco de aleatoriedad
        except Exception as e:
            print(f"Ocurrió un error inesperado al procesar la respuesta para {station_name}: {e}")
            retries += 1
            if retries < max_retries:
                print(f"Reintentando en {delay} segundos... (Intento {retries}/{max_retries})")
                time.sleep(delay + random.uniform(0, 1))
    
    print(f"Fallo al obtener horarios para {station_name} después de {max_retries} intentos.")
    return None # Retorna None si todos los reintentos fallan

# Nota: Elimina cualquier 'if __name__ == "__main__":' que pudiera haber aquí
# para que no se ejecute directamente cuando se importa en Flask.
