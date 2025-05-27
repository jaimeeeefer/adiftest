import requests # type: ignore
import re
import time
import json
from datetime import datetime, timedelta

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0"

# Diccionario para mapear códigos de estación a nombres de URL
# Es importante mantener este diccionario actualizado con las estaciones que te interesen.
STATION_URL_NAMES = {
    "13106": "llodio",
    "70100": "vicálvaro",
    # "CODIGO_ESTACION": "nombre-en-url", # Añade más estaciones aquí si las necesitas
}

# Diccionario para mapear las opciones de tipo de tráfico a los valores de la API
# Hemos añadido "Todos" como la primera opción.
TRAFFIC_TYPES = {
    "1": {"name": "Todos", "value": "all"},
    "2": {"name": "Cercanías", "value": "cercanias"},
    "3": {"name": "AV/LD/MD", "value": "avldmd"},
    "4": {"name": "Mercancías", "value": "m"},
    "5": {"name": "Sin Parada", "value": "sp"},
    "6": {"name": "Sin Parada2", "value": "sinparada"},
}

# El assetEntryId fijo como se ha indicado
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
        response = session.get(url, headers=headers)
    except Exception as e:
        print(f"Error al hacer la petición GET a {url}: {e}")
        return None

    if response.status_code != 200:
        print(f"Error al obtener la página {url}: {response.status_code} {response.reason}")
        return None

    match = re.search(r'p_p_auth=([a-zA-Z0-9]+)', response.text)
    if match:
        return match.group(1)
    else:
        print(f"No se encontró el token p_p_auth en la página {url}.")
        return None

def parse_time_for_sort(horario_item, current_time):
    """
    Convierte la cadena de tiempo a un valor comparable, priorizando
    los trenes más próximos, incluso si son del día siguiente.
    """
    time_str = horario_item['hora']
    
    if "min" in time_str:
        try:
            minutes = int(re.search(r'(\d+)', time_str).group(1))
            # Los trenes en minutos son siempre los más próximos
            return current_time + timedelta(minutes=minutes)
        except ValueError:
            return datetime.min # Un valor muy bajo para que aparezcan primero en caso de error
    else:
        try:
            h, m = map(int, time_str.split(':'))
            scheduled_time = current_time.replace(hour=h, minute=m, second=0, microsecond=0)

            # Si la hora programada es anterior a la hora actual, asumimos que es para el día siguiente
            if scheduled_time < current_time:
                scheduled_time += timedelta(days=1)
            
            return scheduled_time
        except ValueError:
            return datetime.max # Un valor muy alto para que aparezcan al final en caso de error

def get_horarios(station_code, traffic_type_value, max_retries=5, delay=5):
    # Obtener el nombre de la estación para la URL
    station_name = STATION_URL_NAMES.get(station_code)
    if not station_name:
        print(f"Error: No se encontró el nombre de la URL para el código de estación '{station_code}'.")
        print("Por favor, asegúrate de que el código de estación esté en el diccionario STATION_URL_NAMES.")
        return None

    url_base = f"https://www.adif.es/w/{station_code}-{station_name}"

    session = requests.Session()
    
    retries = 0
    while retries < max_retries:
        print(f"Intento {retries + 1} de {max_retries} para estación {station_code} ({station_name}), tipo de tráfico '{traffic_type_value}'...")
        token = obtener_token(session, url_base)
        if not token:
            print(f"No se pudo obtener el token. Reintentando en {delay} segundos...")
            time.sleep(delay)
            retries += 1
            continue

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

        data = {
            "_servicios_estacion_ServiciosEstacionPortlet_searchType": "proximasSalidas",
            f"_servicios_estacion_ServiciosEstacionPortlet_trafficType": traffic_type_value,
            "_servicios_estacion_ServiciosEstacionPortlet_numPage": 0,
            "_servicios_estacion_ServiciosEstacionPortlet_commuterNetwork": "BILBAO", # Esto podría variar según la estación
            f"_servicios_estacion_ServiciosEstacionPortlet_stationCode": station_code
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
            "Referer": url_base,
            "Origin": "https://www.adif.es"
        }

        try:
            response = session.post(url_post, data=data, headers=headers)
            if response.status_code == 200:
                try:
                    json_data = json.loads(response.text)
                    horarios_list = json_data.get("horarios", [])
                    
                    # Si no hay horarios en la lista o la lista es vacía, reintentamos
                    if not horarios_list:
                        print("Respuesta exitosa, pero no se encontraron horarios. Reintentando...")
                        time.sleep(delay)
                        retries += 1
                        continue # Ir al siguiente intento del bucle
                    
                    current_time = datetime.now()
                    horarios_list_sorted = sorted(horarios_list, key=lambda x: parse_time_for_sort(x, current_time))
                    
                    return horarios_list_sorted # Si se obtienen horarios, retornamos
                except json.JSONDecodeError:
                    print("Error al decodificar la respuesta JSON. Reintentando...")
                    print(response.text[:500]) # Imprime los primeros 500 caracteres para depuración
                    time.sleep(delay)
                    retries += 1
                    continue # Ir al siguiente intento del bucle
            else:
                print(f"Error {response.status_code}: {response.reason}. Reintentando...")
                print(response.text[:500]) # Imprime los primeros 500 caracteres del error
                time.sleep(delay)
                retries += 1
                continue # Ir al siguiente intento del bucle
        except requests.exceptions.RequestException as e:
            print(f"Error en la petición POST: {e}. Reintentando...")
            time.sleep(delay)
            retries += 1
            continue # Ir al siguiente intento del bucle
    
    # Si después de todos los reintentos no se pudo obtener, devuelve None
    print(f"No se pudieron obtener horarios después de {max_retries} intentos para la estación {station_code} y tipo de tráfico '{traffic_type_value}'.")
    return None

# --- Función principal para ejecutar el programa ---
def main():
    print("Bienvenido al consultor de horarios de Adif.")
    
    # Solicitar al usuario el código de la estación
    station_code = input("Por favor, introduce el código de la estación (ej. 13106 para Llodio): ")
    
    if not station_code.isdigit():
        print("Código de estación inválido. Debe ser un número.")
        return
    
    if station_code not in STATION_URL_NAMES:
        print(f"El código de estación '{station_code}' no se encuentra en la lista de estaciones soportadas.")
        print("Por favor, añade el código y su nombre de URL al diccionario 'STATION_URL_NAMES' en el script.")
        return

    # Solicitar al usuario el tipo de tráfico
    print("\nSelecciona el tipo de tráfico:")
    for key, value in TRAFFIC_TYPES.items():
        print(f"  {key}: {value['name']}")
    
    traffic_choice = input("Introduce el número de tu elección: ")

    selected_traffic = TRAFFIC_TYPES.get(traffic_choice)
    if not selected_traffic:
        print("Opción de tipo de tráfico inválida. Por favor, selecciona un número de la lista.")
        return
    
    traffic_type_value = selected_traffic['value']

    print(f"\nConsultando horarios para la estación: {station_code} y tipo de tráfico: {selected_traffic['name']}...")
    # La función get_horarios ahora maneja sus propios reintentos.
    horarios_obtenidos = get_horarios(station_code, traffic_type_value, max_retries=10, delay=5) 

    # Ahora, en main, solo necesitamos verificar el resultado final de get_horarios
    if horarios_obtenidos is None:
        print("\nEl proceso falló definitivamente. No se pudieron obtener los horarios de Adif.")
    elif not horarios_obtenidos: 
        print(f"\nNo se encontraron horarios para la estación {station_code} y el tipo de tráfico '{selected_traffic['name']}' después de múltiples intentos.")
        print("Esto puede significar que no hay trenes programados para el período actual con esos criterios.")
        print("\nProceso finalizado con éxito (sin horarios encontrados).")
    else:
        print(f"\n--- Horarios para estación {station_code} ({selected_traffic['name']}) ---")
        for horario in horarios_obtenidos:
            print(f"  Hora: {horario.get('hora')}, Destino: {horario.get('estacion')}, Vía: {horario.get('via')}, Tren: {horario.get('tren')}")
        print("\nProceso finalizado con éxito.")

if __name__ == "__main__":
    main()