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
import tempfile

app = Flask(__name__)

# ✅ Recuperar GOOGLE_CREDENTIALS y parsear correctamente
google_creds = os.environ['GOOGLE_CREDENTIALS']
creds_dict = json.loads(google_creds)
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

# ✅ Crear archivo temporal para Google APIs
with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
    json.dump(creds_dict, tmp)
    tmp.flush()
    credentials = service_account.Credentials.from_service_account_file(tmp.name)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    gspread_creds = ServiceAccountCredentials.from_json_keyfile_name(tmp.name, scope)

# ✅ Cliente de Google Vision
vision_client = vision.ImageAnnotatorClient(credentials=credentials)

# ✅ Cliente de Google Sheets
sheet = gspread.authorize(gspread_creds).open("MiHoja").sheet1  # <-- Cambiá "MiHoja" por el nombre real

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
                msg.body(f"📄 Encontrado: {fila}")
            except:
                msg.body(f"❌ No se encontró '{texto}' en la hoja.")
        else:
            msg.body("⚠️ No pude leer texto en la imagen. Por favor, escribilo manualmente.")
    else:
        texto = request.values.get("Body", "").strip()
        if texto:
            try:
                cell = sheet.find(texto)
                fila = sheet.row_values(cell.row)
                msg.body(f"📄 Encontrado: {fila}")
            except:
                msg.body(f"❌ No se encontró '{texto}' en la hoja.")
        else:
            msg.body("📩 Mandame una imagen o escribí un dato para buscar.")

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)



