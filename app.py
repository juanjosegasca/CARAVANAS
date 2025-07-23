import os
import json
from flask import Flask, request, jsonify
from google.oauth2 import service_account
from google.cloud import vision
import gspread

app = Flask(__name__)

# Cargar credenciales de Google desde variable de entorno
creds_dict = json.loads(os.environ['GOOGLE_CREDENTIALS'])
creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
credentials = service_account.Credentials.from_service_account_info(creds_dict)

# Cliente Google Vision
vision_client = vision.ImageAnnotatorClient(credentials=credentials)

# Cliente Google Sheets
gspread_creds = credentials.with_scopes([
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
])
gc = gspread.Client(auth=gspread_creds)
gc.session = gspread.httpsession.HTTPSession()  # inicializa sesión
gc.login()
sheet = gc.open("caravanas").sheet1  # Cambia "caravanas" por el nombre real de tu hoja

def ocr_image(content):
    image = vision.Image(content=content)
    response = vision_client.text_detection(image=image)
    texts = response.text_annotations
    if texts:
        return texts[0].description.strip()
    return ""

@app.route("/", methods=["GET"])
def home():
    return "Servidor Flask con OCR y Google Sheets funcionando!", 200

@app.route("/procesar", methods=["POST"])
def procesar():
    # Puede recibir JSON con "texto" o archivo imagen en multipart/form-data
    if "file" in request.files:
        file = request.files["file"]
        content = file.read()
        texto = ocr_image(content)
        if not texto:
            return jsonify({"error": "No se pudo extraer texto, ingrese manualmente"}), 400
    else:
        texto = request.json.get("texto", "")
        if not texto:
            return jsonify({"error": "No se recibió texto ni archivo"}), 400

    # Buscá el texto en la hoja de cálculo en la columna "Caravana"
    try:
        records = sheet.get_all_records()
        # Buscar fila donde "Caravana" coincida con texto OCR (case insensitive)
        resultado = next(
            (r for r in records if str(r.get("Caravana", "")).lower() == texto.lower()),
            None
        )
    except Exception as e:
        return jsonify({"error": f"Error accediendo a Google Sheets: {str(e)}"}), 500

    if resultado:
        corral = resultado.get("Corral", None)
        return jsonify({"Caravana": texto, "Corral": corral})
    else:
        return jsonify({"mensaje": "No se encontró la caravana en la hoja"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)





