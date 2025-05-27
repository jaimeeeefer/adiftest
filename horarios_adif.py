# horarios_adif.py (tu script existente)
import requests
import re
import time
import json
from datetime import datetime, timedelta

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0"

STATION_URL_NAMES = {
    "13106": "llodio",
    "70100": "vicálvaro",
}

TRAFFIC_TYPES = {
    "1": {"name": "Todos", "value": "all"},
    "2": {"name": "Cercanías", "value": "cercanias"},
    "3": {"name": "AV/LD/MD", "value": "avldmd"},
    "4": {"name": "Mercancías", "value": "m"},
    "5": {"name": "Sin Parada", "value": "sp"},
    "6": {"name": "Sin Parada2", "value": "sinparada"},
}

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
    station_name = STATION_URL_NAMES.get(station_code)
    if not station_name:
        # En una API, podríamos devolver un error JSON en lugar de None
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
            "_servicios_estacion_ServiciosEstacionPortlet_commuterNetwork": "BILBAO",
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
                    
                    if not horarios_list:
                        print("Respuesta exitosa, pero no se encontraron horarios. Reintentando...")
                        time.sleep(delay)
                        retries += 1
                        continue
                    
                    current_time = datetime.now()
                    horarios_list_sorted = sorted(horarios_list, key=lambda x: parse_time_for_sort(x, current_time))
                    
                    return horarios_list_sorted
                except json.JSONDecodeError:
                    print("Error al decodificar la respuesta JSON. Reintentando...")
                    print(response.text[:500])
                    time.sleep(delay)
                    retries += 1
                    continue
            else:
                print(f"Error {response.status_code}: {response.reason}. Reintentando...")
                print(response.text[:500])
                time.sleep(delay)
                retries += 1
                continue
        except requests.exceptions.RequestException as e:
            print(f"Error en la petición POST: {e}. Reintentando...")
            time.sleep(delay)
            retries += 1
            continue
    
    print(f"No se pudieron obtener horarios después de {max_retries} intentos para la estación {station_code} y tipo de tráfico '{traffic_type_value}'.")
    return None

# Ya no necesitamos la función main() interactiva aquí.
# Si quieres mantenerla para pruebas locales, puedes hacerlo,
# pero asegúrate de que no se ejecute cuando Flask se inicie.
# if __name__ == "__main__":
#     main()
