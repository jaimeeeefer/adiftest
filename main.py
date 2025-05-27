# main.py

from flask import Flask, request, jsonify
from flask_cors import CORS # Importa la extensión Flask-Cors
from horarios_adif import get_horarios, STATION_URL_NAMES, TRAFFIC_TYPES # Importa tus funciones y diccionarios

app = Flask(__name__)
CORS(app) # Habilita CORS para toda la aplicación Flask. ¡Esto soluciona el 403 Forbidden!

# Ruta para la URL raíz (GET request)
# Esto es útil para verificar que la API está funcionando al visitar su URL base.
@app.route('/', methods=['GET'])
def home():
    return "<h1>API de Horarios ADIF en Render</h1><p>Esta es la API de backend para consultar horarios. Por favor, accede desde la interfaz web en GitHub Pages.</p><p>El endpoint para consultas es <code>/get_train_data</code> (POST).</p>"

# Ruta API para obtener los horarios (POST request desde tu GitHub Page)
@app.route('/get_train_data', methods=['POST'])
def get_train_data():
    # Obtener datos del formulario enviados en la petición POST
    station_code = request.form.get('station_code')
    traffic_type_key = request.form.get('traffic_type')

    # Validaciones básicas de los parámetros recibidos
    if not station_code or not traffic_type_key:
        print("API - Error: Faltan station_code o traffic_type en la solicitud.")
        return jsonify({"error": "Faltan parámetros: 'station_code' o 'traffic_type'."}), 400

    if station_code not in STATION_URL_NAMES:
        print(f"API - Error: Código de estación '{station_code}' no soportado.")
        return jsonify({"error": f"Código de estación '{station_code}' no soportado."}), 400

    selected_traffic = TRAFFIC_TYPES.get(traffic_type_key)
    if not selected_traffic:
        print(f"API - Error: Tipo de tráfico '{traffic_type_key}' no válido.")
        return jsonify({"error": f"Tipo de tráfico '{traffic_type_key}' no válido."}), 400
    
    traffic_type_value = selected_traffic['value']

    print(f"API - Recibida solicitud para estación: {station_code}, tipo de tráfico: {selected_traffic['name']}")
    
    # Llama a tu función de scraping de horarios
    # Ajusta max_retries y delay según tu necesidad.
    horarios_obtenidos = get_horarios(station_code, traffic_type_value, max_retries=5, delay=3)

    # Prepara la respuesta JSON basada en los resultados de get_horarios
    if horarios_obtenidos is None:
        # Si get_horarios devuelve None después de todos los reintentos, es un fallo crítico.
        print("API - Error: No se pudieron obtener los horarios de Adif después de múltiples intentos. Puede haber un problema con la API externa o la red.")
        return jsonify({"error": "No se pudieron obtener los horarios de Adif. Inténtalo de nuevo más tarde o verifica el código de estación/tráfico."}), 500
    elif not horarios_obtenidos:
        # Si get_horarios devuelve una lista vacía, no hay horarios encontrados pero la petición fue exitosa.
        print(f"API - Aviso: No se encontraron horarios para la estación {STATION_URL_NAMES.get(station_code)} y el tipo de tráfico '{selected_traffic['name']}'.")
        return jsonify({"message": f"No se encontraron horarios para la estación {STATION_URL_NAMES.get(station_code)} y el tipo de tráfico '{selected_traffic['name']}'. Esto puede significar que no hay trenes programados para el período actual con esos criterios.", "horarios": []}), 200
    else:
        # Si se obtuvieron horarios, devolverlos.
        print(f"API - Éxito: {len(horarios_obtenidos)} horarios encontrados.")
        return jsonify({"horarios": horarios_obtenidos}), 200

# Asegúrate de que esta parte esté al final y sea la que inicie la aplicación Flask
if __name__ == '__main__':
    # Cuando se despliega con Gunicorn en Render, esta parte no se ejecuta directamente,
    # ya que Gunicorn es quien inicia la aplicación.
    app.run(host='0.0.0.0', port=8080)
