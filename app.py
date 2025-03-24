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
    print("Paytraq API URL:", url)
    print("Paytraq API status code:", response.status_code)
    print("Paytraq API response body:", response.text)
    
    if response.status_code == 200:
        data = response.json()
        sync_response = requests.post(SYNC_URL, json=data)
        print("SYNC status code:", sync_response.status_code)
        print("SYNC response body:", sync_response.text)
        return jsonify({
            "paytraq_status": "success",
            "sync_status": sync_response.status_code,
            "sync_response": sync_response.text
        })
    else:
        return jsonify({
            "status": "error",
            "code": response.status_code,
            "message": response.text
        })

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
