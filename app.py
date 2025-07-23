import os
import json
import requests
from flask import Flask, request
from google.cloud import vision
from google.oauth2 import service_account
import gspread
import cv2
import numpy as np

app = Flask(__name__)

# Cargar credenciales de Google desde variables de entorno
google_creds_dict = json.loads(os.environ['GOOGLE_CREDENTIALS'])
credentials = service_account.Credentials.from_service_account_info(google_creds_dict)

# Inicializar clientes
vision_client = vision.ImageAnnotatorClient(credentials=credentials)
gc = gspread.authorize(credentials)
sheet = gc.open("caravanas").sheet1  # Asegurate de compartir la hoja con el mail del service account

def preprocesar_imagen(path_img):
    img = cv2.imread(path_img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    thresh = cv2.adaptiveThreshold(enhanced, 255,
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 11, 2)
    salida = "preprocesada.jpg"
    cv2.imwrite(salida, thresh)
    return salida

def extraer_texto(path):
    path_proc = preprocesar_imagen(path)
    with open(path_proc, "rb") as img_file:
        content = img_file.read()
    image = vision.Image(content=content)
    response = vision_client.text_detection(image=image)
    texts = response.text_annotations
    if texts:
        return texts[0].description.strip().replace('\n', '')
    return None

def buscar_corral_por_caravana(valor_caravana):
    datos = sheet.get_all_records()
    for fila in datos:
        if str(fila["Caravana"]) == str(valor_caravana):
            return fila.get("Corral", "No encontrado")
    return "Caravana no encontrada"

@app.route("/", methods=["GET"])
def index():
    return "Bot OCR activo ✅"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        mensaje = request.form.get("Body")
        media_url = request.form.get("MediaUrl0")

        if media_url:
            extension = media_url.split(".")[-1]
            img_path = f"imagen_recibida.{extension}"
            img_data = requests.get(media_url).content
            with open(img_path, "wb") as f:
                f.write(img_data)

            texto_detectado = extraer_texto(img_path)

            if texto_detectado:
                corral = buscar_corral_por_caravana(texto_detectado)
                respuesta = f"Caravana detectada: {texto_detectado}\nCorral: {corral}"
            else:
                respuesta = "No se pudo leer la caravana. Por favor, ingrésala manualmente."

        elif mensaje:
            corral = buscar_corral_por_caravana(mensaje.strip())
            respuesta = f"Corral para caravana {mensaje.strip()}: {corral}"
        else:
            respuesta = "Envía una foto o número de caravana."

        return respuesta
    except Exception as e:
        return f"❌ Error: {str(e)}"

if __name__ == "__main__":
    app.run(debug=True)








