import os
import json
import requests
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from google.oauth2 import service_account
from google.cloud import vision
import gspread

# Inicializa Flask
app = Flask(__name__)

# Cargar credenciales desde variable de entorno
creds_dict = json.loads(os.environ['GOOGLE_CREDENTIALS'])
creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
credentials = service_account.Credentials.from_service_account_info(creds_dict)

# Google Vision client
vision_client = vision.ImageAnnotatorClient(credentials=credentials)

# Google Sheets client
gspread_creds = credentials.with_scopes([
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
])
gc = gspread.authorize(gspread_creds)
sheet = gc.open("caravanas").sheet1  # <- Asegurate que sea el nombre exacto

# Función OCR
def ocr_image(content):
    image = vision.Image(content=content)
    response = vision_client.text_detection(image=image)
    texts = response.text_annotations
    return texts[0].description.strip() if texts else ""

# Ruta simple para verificar
@app.route("/", methods=["GET"])
def home():
    return "Servidor OCR activo ✅", 200

# Ruta para procesar desde WhatsApp
@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip()
    num_media = int(request.values.get('NumMedia', 0))

    resp = MessagingResponse()
    msg = resp.message()

    # Si viene imagen
    if num_media > 0:
        media_url = request.values.get('MediaUrl0')
        try:
            media_content = requests.get(media_url).content
            texto = ocr_image(media_content)
        except Exception as e:
            msg.body("❌ Error al procesar la imagen.")
            return str(resp)
        if not texto:
            msg.body("⚠️ No se detectó texto. Escribilo manualmente.")
            return str(resp)
    else:
        texto = incoming_msg
        if not texto:
            msg.body("⚠️ No recibí imagen ni texto.")
            return str(resp)

    try:
        records = sheet.get_all_records()
        resultado = next(
            (r for r in records if str(r.get("Caravana", "")).lower() == texto.lower()),
            None
        )
    except Exception as e:
        msg.body("❌ Error al acceder a la hoja.")
        return str(resp)

    if resultado:
        corral = resultado.get("Corral", "Sin asignar")
        msg.body(f"✅ Caravana: {texto}\nCorral: {corral}")
    else:
        msg.body("❌ No encontré esa caravana en la hoja.")

    return str(resp)

# Ruta para pruebas manuales o Postman
@app.route("/procesar", methods=["POST"])
def procesar():
    if "file" in request.files:
        file = request.files["file"]
        content = file.read()
        texto = ocr_image(content)
        if not texto:
            return jsonify({"error": "No se pudo extraer texto de la imagen"}), 400
    else:
        texto = request.json.get("texto", "")
        if not texto:
            return jsonify({"error": "No se recibió texto ni archivo"}), 400

    try:
        records = sheet.get_all_records()
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








