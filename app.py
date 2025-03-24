from flask import Flask, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

# API dati
API_KEY = "421045bc-a402-4223-b048-52b65340e21a-98693"
API_TOKEN = "KcPtQHuxpxGbXCr4"
SYNC_URL = "https://aytraq-to-pipedrive-basic-service-281111054789.us-central1.run.app/sync"

@app.route('/', methods=['GET'])
def index():
    return jsonify({"message": "Sveiki! Serviss darbojas. Izmanto /get-paytraq-orders lai ielādētu un sinhronizētu datus."})

@app.route('/get-paytraq-orders', methods=['GET'])
def get_orders():
    today = datetime.today().strftime('%Y-%m-%d')
    url = f"https://go.paytraq.com/api/sales?APIKey={API_KEY}&APIToken={API_TOKEN}&DateFrom={today}&DateTo={today}"

    response = requests.get(url)
    
    if response.status_code == 200:
        # Print headers and raw response for debugging
        print("Content-Type:", response.headers.get('Content-Type'))
        print("PayTraq response body:", response.text)

        try:
            data = response.json()  # Try parsing as JSON
        except Exception as e:
            return jsonify({
                "error": "Failed to parse JSON",
                "details": str(e),
                "response": response.text
            })

        # Nosūtām uz /sync endpointu, ja dati ir pareizi
        sync_response = requests.post(SYNC_URL, json=data)

        return jsonify({
            "paytraq_status": "success",
            "sync_status": sync_response.status_code,
            "sync_response": sync_response.text
        })
    else:
        return jsonify({"status": "error", "code": response.status_code, "message": response.text})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
