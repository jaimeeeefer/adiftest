# horarios_adif.py
# (El contenido de tu script de scraping que me proporcionaste anteriormente)

import requests
import re
import time
import json
from datetime import datetime, timedelta

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0"

# Diccionario para mapear códigos de estación a nombres de URL
STATION_URL_NAMES = {
    "13106": "llodio",
    "70100": "vicálvaro",
    # "CODIGO_ESTACION": "nombre-en-url", # Añade más estaciones aquí si las necesitas
    "05001": "madrid-atocha", # Ejemplo, asegúrate que ADIF tiene esta estación así
    "05002": "madrid-chamartin", # Ejemplo
    "05003": "valencia-joaquin-sorolla", # Ejemplo
    "05004": "barcelona-sants", # Ejemplo
}

# Diccionario para mapear las opciones de tipo de tráfico a los valores de la API
TRAFFIC_TYPES = {
    "1": {"name": "Todos", "value": "all"},
    "2": {"name": "Cercanías", "value": "cercanias"},
    "3": {"name": "AV/LD/MD", "value": "avldmd"},
    "4": {"name": "Mercancías", "value": "m"},
    "5": {"name": "Sin Parada", "value": "sp"},
    "6": {"name": "Sin Parada2", "value": "sinparada"}, # Asumo que 'sinparada' es el valor correcto para la URL
}

# El assetEntryId fijo
FIXED_ASSET_ENTRY_ID = "3127062"

def obtener_token(session, url):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "TE": "trailers"
    }
    try:
        response = session.get(url, headers=headers, timeout=15) # Aumentar timeout por si acaso
    except requests.exceptions.RequestException as e:
        print(f"Error de red al obtener token de {url}: {e}")
        return None
    except Exception as e:
        print(f"Error inesperado al hacer GET a {url}: {e}")
        return None

    if response.status_code != 200:
        print(f"Error al obtener la página {url}: {response.status_code} {response.reason}. Contenido: {response.text[:200]}")
        return None

    match = re.search(r'p_p_auth=([a-zA-Z0-9]+)', response.text)
    if match:
        return match.group(1)
    else:
        print(f"No se encontró el token p_p_auth en la página {url}. Contenido de la página: {response.text[:500]}")
        return None

def parse_time_for_sort(horario_item, current_time):
    time_str = horario_item['hora']
    if "min" in time_str:
        try:
            minutes = int(re.search(r'(\d+)', time_str).group(1))
            return current_time + timedelta(minutes=minutes)
        except ValueError:
            return datetime.min
    else:
        try:
            h, m = map(int, time_str.split(':'))
            scheduled_time = current_time.replace(hour=h, minute=m, second=0, microsecond=0)
            if scheduled_time < current_time:
                scheduled_time += timedelta(days=1)
            return scheduled_time
        except ValueError:
            return datetime.max

def get_horarios(station_code, traffic_type_value, max_retries=5, delay=5):
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
        print(f"Error: Código de estación '{station_code}' no encontrado en STATION_URL_NAMES.")
        return None

    # Base URL del portal de la estación en ADIF, no la URL de los horarios directamente
    url_base = f"https://www.adif.es/w/{station_code}-{station_name}"

    session = requests.Session()
    
    retries = 0
    while retries < max_retries:
        print(f"Intento {retries + 1} de {max_retries} para {station_name} ({station_code}), tráfico '{traffic_type_value}'...")
        
        # 1. Obtener el token p_p_auth de la página base
        token = obtener_token(session, url_base)
        if not token:
            print(f"Fallo al obtener el token. Reintentando en {delay}s...")
            time.sleep(delay)
            retries += 1
            continue

        # 2. Construir la URL POST para la consulta de horarios
        url_post = (
            url_base +
            "?p_p_id=servicios_estacion_ServiciosEstacionPortlet"
            "&p_p_lifecycle=2"
            "&p_p_state=normal"
            "&p_p_mode=view"
            "&p_p_resource_id=/consultarHorario"
            "&p_p_cacheability=cacheLevelPage"
            f"&assetEntryId={FIXED_ASSET_ENTRY_ID}"
            f"&p_p_auth={token}"
        )

        # 3. Datos a enviar en la petición POST
        data = {
            "_servicios_estacion_ServiciosEstacionPortlet_searchType": "proximasSalidas",
            "_servicios_estacion_ServiciosEstacionPortlet_trafficType": traffic_type_value,
            "_servicios_estacion_ServiciosEstacionPortlet_numPage": 0,
            "_servicios_estacion_ServiciosEstacionPortlet_commuterNetwork": "BILBAO", # Esto puede variar
            "_servicios_estacion_ServiciosEstacionPortlet_stationCode": station_code
        }

        # 4. Cabeceras para la petición POST
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
            "Referer": url_base, # Importante: el Referer debe ser la página de donde obtuvimos el token
            "Origin": "https://www.adif.es"
        }

        try:
            response = session.post(url_post, data=data, headers=headers, timeout=30) # Aumentar timeout
            
            if response.status_code == 200:
                try:
                    json_data = json.loads(response.text)
                    horarios_list = json_data.get("horarios", [])
                    
                    if not horarios_list:
                        print("Respuesta exitosa de ADIF, pero no se encontraron horarios. Puede que no haya trenes en este momento.")
                        return [] # Retorna lista vacía en lugar de None para indicar que todo fue bien pero no hay datos
                    
                    current_time = datetime.now()
                    # Ordenar por hora, manejando "minutos" y cambio de día
                    horarios_list_sorted = sorted(horarios_list, key=lambda x: parse_time_for_sort(x, current_time))
                    
                    print(f"Éxito: Se encontraron {len(horarios_list_sorted)} horarios.")
                    return horarios_list_sorted # Si se obtienen horarios, retornamos
                except json.JSONDecodeError:
                    print(f"Error al decodificar la respuesta JSON. Contenido: {response.text[:500]}")
                    # No reintentar si el JSON está mal, es un problema de formato de respuesta
                    return None
            else:
                print(f"Error HTTP {response.status_code}: {response.reason}. Contenido: {response.text[:500]}")
                time.sleep(delay)
                retries += 1
                continue
        except requests.exceptions.RequestException as e:
            print(f"Error de red o conexión en la petición POST: {e}.")
            time.sleep(delay)
            retries += 1
            continue
        except Exception as e:
            print(f"Ocurrió un error inesperado durante la consulta de horarios: {e}")
            time.sleep(delay)
            retries += 1
            continue
    
    print(f"Fallo definitivo al obtener horarios después de {max_retries} intentos para la estación {station_name} y tipo de tráfico '{traffic_type_value}'.")
    return None # Retorna None si todos los reintentos fallan
