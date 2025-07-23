from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
import requests

# (el resto de imports y configuración que ya tenés)

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip()
    num_media = int(request.values.get('NumMedia', 0))

    resp = MessagingResponse()
    msg = resp.message()

    if num_media > 0:
        # Si mandaron una imagen, obtenemos la URL y la descargamos
        media_url = request.values.get('MediaUrl0')
        media_content = requests.get(media_url).content
        texto = ocr_image(media_content)
        if not texto:
            msg.body("No pude extraer texto de la imagen. Por favor, escribí el texto manualmente.")
            return str(resp)
    else:
        texto = incoming_msg
        if not texto:
            msg.body("No recibí texto ni imagen.")
            return str(resp)

    # Buscar en Google Sheets
    try:
        records = sheet.get_all_records()
        resultado = next(
            (r for r in records if str(r.get("Caravana", "")).lower() == texto.lower()),
            None
        )
    except Exception as e:
        msg.body(f"Error accediendo a Google Sheets: {str(e)}")
        return str(resp)

    if resultado:
        corral = resultado.get("Corral", "No tiene Corral asignado")
        msg.body(f"Caravana: {texto}\nCorral: {corral}")
    else:
        msg.body("No encontré la caravana en la hoja.")

    return str(resp)







