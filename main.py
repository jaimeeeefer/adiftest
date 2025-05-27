# main.py
from flask import Flask, render_template, request, jsonify
from horarios_adif import get_horarios, STATION_URL_NAMES, TRAFFIC_TYPES # Importa tus funciones y diccionarios

app = Flask(__name__)

# Ruta para la página principal con el formulario
@app.route('/')
def index():
    return render_template('index.html', station_url_names=STATION_URL_NAMES, traffic_types=TRAFFIC_TYPES)

# Ruta API para obtener los horarios
@app.route('/get_train_data', methods=['POST'])
def get_train_data():
    station_code = request.form.get('station_code')
    traffic_type_key = request.form.get('traffic_type')

    if not station_code or not traffic_type_key:
        return jsonify({"error": "Faltan parámetros: station_code o traffic_type."}), 400

    # Asegúrate de que el station_code sea válido
    if station_code not in STATION_URL_NAMES:
        return jsonify({"error": f"Código de estación '{station_code}' no soportado."}), 400

    # Obtener el valor real del tipo de tráfico de nuestro diccionario
    selected_traffic = TRAFFIC_TYPES.get(traffic_type_key)
    if not selected_traffic:
        return jsonify({"error": f"Tipo de tráfico '{traffic_type_key}' no válido."}), 400

    traffic_type_value = selected_traffic['value']

    print(f"Recibida solicitud para estación: {station_code}, tipo de tráfico: {selected_traffic['name']}")
    
    # Llama a tu función existente
    horarios_obtenidos = get_horarios(station_code, traffic_type_value, max_retries=5, delay=3)

    if horarios_obtenidos is None:
        return jsonify({"error": "No se pudieron obtener los horarios de Adif después de múltiples intentos. Puede haber un problema con la API externa."}), 500
    elif not horarios_obtenidos:
        return jsonify({"message": f"No se encontraron horarios para la estación {STATION_URL_NAMES.get(station_code)} y el tipo de tráfico '{selected_traffic['name']}'. Esto puede significar que no hay trenes programados para el período actual con esos criterios.", "horarios": []}), 200
    else:
        # Devuelve los horarios como JSON
        return jsonify({"horarios": horarios_obtenidos}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080) # Replit usa 0.0.0.0 y el puerto por defecto es 8080 (o se asigna dinámicamente)
