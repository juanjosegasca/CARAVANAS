from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from PIL import Image
import requests
import pytesseract
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

app = Flask(__name__)

# Ruta opcional para Tesseract si estás en Windows o querés definirla manualmente
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

# Configuración Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
client = gspread.authorize(creds)
sheet = client.open("MiHoja").sheet1  # Nombre exacto del archivo

@app.route("/", methods=["POST"])
def whatsapp_bot():
    resp = MessagingResponse()
    msg = resp.message()

    # Chequear si se envió una imagen
    num_media = int(request.values.get("NumMedia", 0))

    if num_media > 0:
        media_url = request.values.get("MediaUrl0")
        img_data = requests.get(media_url).content

        with open("temp.jpg", "wb") as f:
            f.write(img_data)

        texto_extraido = pytesseract.image_to_string(Image.open("temp.jpg")).strip()
        os.remove("temp.jpg")

        if texto_extraido:
            primera_linea = texto_extraido.split('\n')[0].strip()
            if primera_linea:
                # Buscar en Google Sheets
                try:
                    cell = sheet.find(primera_linea)
                    fila = sheet.row_values(cell.row)
                    msg.body(f"Encontrado: {fila}")
                except:
                    msg.body(f"No se encontró '{primera_linea}' en la hoja.")
            else:
                msg.body("No pude leer ningún dato. Por favor escribí el número o texto manualmente.")
        else:
            msg.body("No pude leer la imagen. Por favor escribí el dato manualmente.")
    else:
        # Se procesó como texto
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
    ap
