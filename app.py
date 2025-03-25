from flask import Flask, jsonify
import requests
from datetime import datetime
import xml.etree.ElementTree as ET

app = Flask(__name__)

# API dati
API_KEY = "421045bc-a402-4223-b048-52b65340e21a-98693"
API_TOKEN = "KcPtQHuxpxGbXCr4"
SYNC_URL = "https://paytraq-to-pipedrive-basic-service-281111054789.us-central1.run.app/sync"

@app.route('/', methods=['GET'])
def index():
    return jsonify({"message": "Sveiki! Serviss darbojas. Izmanto /get-paytraq-orders lai ielādētu un sinhronizētu datus."})

@app.route('/get-paytraq-orders', methods=['GET'])
def get_orders():
    today = datetime.today().strftime('%Y-%m-%d')
    url = f"https://go.paytraq.com/api/sales?APIKey={API_KEY}&APIToken={API_TOKEN}&DateFrom={today}&DateTo={today}"

    response = requests.get(url)
    
    if response.status_code == 200:
        print("Content-Type:", response.headers.get('Content-Type'))
        print("PayTraq response:", response.text)
        
        try:
            # Parsē XML
            root = ET.fromstring(response.text)
            data = parse_xml_to_dict(root)  # Funkcija, lai pārvērstu XML uz dictionary (JSON formātā)

            # Nosūtām uz /sync endpointu
            sync_response = requests.post(SYNC_URL, json=data)
            return jsonify({
                "paytraq_status": "success",
                "sync_status": sync_response.status_code,
                "sync_response": sync_response.text
            })
        except Exception as e:
            return jsonify({"error": "Failed to parse XML", "details": str(e), "response": response.text})

    else:
        return jsonify({"status": "error", "code": response.status_code, "message": response.text})

# Funkcija XML pārveidošanai uz Python dictionary
def parse_xml_to_dict(element):
    data = {}
    for child in element:
        if len(child):
            data[child.tag] = parse_xml_to_dict(child)  # Rekursija
        else:
            data[child.tag] = child.text
    return data

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
