from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google.cloud import vision
from google.oauth2 import service_account
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import os
import io
import json

app = Flask(__name__)

# ✅ Convertir GOOGLE_CREDENTIALS (string plano) a dict
creds_dict = json.loads(os.environ['GOOGLE_CREDENTIALS'])

# ✅ Arreglar el campo private_key (para saltos de línea reales)
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

# ✅ Inicializar cliente de Vision
credentials = service_account.Credentials.from_service_account_info(creds_dict)
vision_client = vision.ImageAnnotatorClient(credentials=credentials)

# ✅ Inicializar cliente de Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
sheet = gspread.authorize(creds).open("MiHoja").sheet1  # <- Cambiar "MiHoja" por el nombre real

@app.route("/", methods=["POST"])
def whatsapp_bot():
    resp = MessagingResponse()
    msg = resp.message()

    num_media = int(request.values.get("NumMedia", 0))

    if num_media > 0:
        media_url = request.values.get("MediaUrl0")
        img_data = requests.get(media_url).content

        image = vision.Image(content=img_data)
        response = vision_client.text_detection(image=image)
        texts = response.text_annotations

        if texts:
            texto = texts[0].description.strip().split('\n')[0]
            try:
                cell = sheet.find(texto)
                fila = sheet.row_values(cell.row)
                msg.body(f"Encontrado: {fila}")
            except:
                msg.body(f"No se encontró '{texto}' en la hoja.")
        else:
            msg.body("No pude leer texto en la imagen. Escribí el dato manualmente.")
    else:
        texto = request.values.get("Body", "").strip()
        if texto:
            try:
                cell = sheet.find(texto)
                fila = sheet.row_values(cell.row)
                msg.body(f"Encontrado: {fila}")
            except:
                msg.body(f"No se encontró '{texto}' en la hoja.")
        else:
            msg.body("Mandame una imagen o escribí un dato para buscar.")

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)


