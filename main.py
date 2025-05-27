# main.py

from flask import Flask, request, jsonify
from flask_cors import CORS # Importa la extensión Flask-Cors
from horarios_adif import get_horarios, STATION_URL_NAMES, TRAFFIC_TYPES # Importa tus funciones y diccionarios

app = Flask(__name__)
# Habilita CORS para toda la aplicación Flask.
# Esto es CRUCIAL para que tu GitHub Page pueda llamar a tu API en Render.
# Permite peticiones desde cualquier origen ('*'), lo cual es adecuado para desarrollo.
CORS(app) 

# Ruta para la URL raíz (GET request)
# Esto es útil para verificar que la API está funcionando al visitar su URL base en el navegador.
@app.route('/', methods=['GET'])
def home():
    return "<h1>API de Horarios ADIF en Render</h1><p>Esta es la API de backend para consultar horarios de trenes.</p><p>El endpoint para consultas es <code>/get_train_data</code> (POST).</p><p>Por favor, utiliza la interfaz web en tu GitHub Pages para interactuar con esta API.</p>"

# Ruta API para obtener los horarios (POST request desde tu GitHub Page)
@app.route('/get_train_data', methods=['POST'])
def get_train_data():
    # Obtener datos del formulario enviados en la petición POST
    # request.form se usa para datos enviados con 'application/x-www-form-urlencoded'
    station_code = request.form.get('station_code')
    traffic_type_key = request.form.get('traffic_type')

    # Validaciones básicas de los parámetros recibidos
    if not station_code or not traffic_type_key:
        print("API - Error: Faltan station_code o traffic_type en la solicitud.")
        return jsonify({"error": "Faltan parámetros: 'station_code' o 'traffic_type'."}), 400

    if station_code not in STATION_URL_NAMES:
        print(f"API - Error: Código de estación '{station_code}' no soportado.")
        return jsonify({"error": f"Código de estación '{station_code}' no soportado por esta API."}), 400

    selected_traffic = TRAFFIC_TYPES.get(traffic_type_key)
    if not selected_traffic:
        print(f"API - Error: Tipo de tráfico '{traffic_type_key}' no válido.")
        return jsonify({"error": f"Tipo de tráfico '{traffic_type_key}' no válido."}), 400
    
    traffic_type_value = selected_traffic['value']

    print(f"API - Recibida solicitud para estación: {STATION_URL_NAMES.get(station_code)} ({station_code}), tipo de tráfico: {selected_traffic['name']}")
    
    # Llama a tu función de scraping de horarios
    # Ajusta max_retries y delay según tu necesidad.
    horarios_obtenidos = get_horarios(station_code, traffic_type_value, max_retries=5, delay=3)

    # Prepara la respuesta JSON basada en los resultados de get_horarios
    if horarios_obtenidos is None:
        # Si get_horarios devuelve None después de todos los reintentos, es un fallo crítico.
        print("API - Error: No se pudieron obtener los horarios de Adif después de múltiples intentos. Puede haber un problema con la web externa o la red.")
        return jsonify({"error": "No se pudieron obtener los horarios de Adif. Inténtalo de nuevo más tarde o verifica el código de estación/tráfico. Consulta los logs del servidor para más detalles."}), 500
    elif not horarios_obtenidos:
        # Si get_horarios devuelve una lista vacía, no hay horarios encontrados pero la petición fue exitosa.
        print(f"API - Aviso: No se encontraron horarios para la estación {STATION_URL_NAMES.get(station_code)} y el tipo de tráfico '{selected_traffic['name']}'.")
        return jsonify({"message": f"No se encontraron horarios para la estación {STATION_URL_NAMES.get(station_code)} y el tipo de tráfico '{selected_traffic['name']}'. Esto puede significar que no hay trenes programados para el período actual con esos criterios.", "horarios": []}), 200
    else:
        # Si se obtuvieron horarios, devolverlos.
        print(f"API - Éxito: {len(horarios_obtenidos)} horarios encontrados.")
        return jsonify({"horarios": horarios_obtenidos}), 200

# Esta parte es para que Gunicorn (el servidor que usa Render) sepa qué objeto Flask servir.
# Render ejecutará 'gunicorn main:app', buscando 'app' en este archivo.
if __name__ == '__main__':
    # Esto solo se ejecuta si corres el script directamente (ej. python main.py),
    # no cuando se despliega con Gunicorn en Render.
    app.run(host='0.0.0.0', port=os.getenv('PORT', 5000)) # Usa el puerto que Render asigna, por defecto 5000
