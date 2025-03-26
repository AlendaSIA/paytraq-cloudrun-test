from flask import Flask, jsonify, Response
import requests
from datetime import datetime
import xml.etree.ElementTree as ET
import os  # <--- svarīgi!

app = Flask(__name__)

# API dati no vides mainīgajiem
API_KEY = os.environ.get("API_KEY")
API_TOKEN = os.environ.get("API_TOKEN")
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
        try:
            root = ET.fromstring(response.text)
            data = parse_xml_to_dict(root)
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

# === PILNA ATSKAITE: Dokuments + Produkti + Grupas ===
@app.route('/paytraq-full-report', methods=['GET'])
def paytraq_full_report():
    today = datetime.today().strftime('%Y-%m-%d')
    url = f"https://go.paytraq.com/api/sales?APIKey={API_KEY}&APIToken={API_TOKEN}&DateFrom={today}&DateTo={today}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        orders = root.findall(".//Document")
        if not orders:
            return "❌ Nav atrasts neviens dokuments."

        doc = orders[0]
        doc_id = doc.findtext("DocumentID")
        doc_number = doc.findtext("DocumentNumber")
        client_name = doc.findtext(".//Company/Name")
        line_items = doc.findall(".//LineItem")

        output = []
        output.append(f"✅ Jaunākais dokumenta ID: {doc_id}")
        output.append(f"📄 Dokumenta Nr.: {doc_number}")
        output.append(f"👤 Klients: {client_name}\n")
        output.append("📦 Produkti dokumentā:")
        output.append("=" * 60)

        item_groups = {}

        for idx, item in enumerate(line_items, 1):
            qty = item.findtext("Qty")
            name = item.findtext("ItemName")
            code = item.findtext("ItemCode")
            price = item.findtext("Price")
            unit = item.findtext(".//UnitName", default="gab.")
            total = item.findtext("LineTotal")
            item_id = item.findtext("ItemID")

            output.append(f"{idx}. {qty} x {name} ({code}) - {price} EUR [{unit}] → {total} EUR")
            output.append(f"      🔎 ItemID: {item_id}")

            # Grupas iegūšana
            product_url = f"https://go.paytraq.com/api/product/{item_id}?APIToken={API_TOKEN}&APIKey={API_KEY}"
            try:
                product_response = requests.get(product_url)
                product_response.raise_for_status()
                product_root = ET.fromstring(product_response.content)
                group_name = product_root.findtext(".//Group/GroupName", default="—").strip()
                line_total = float(total.replace(",", "."))

                if group_name not in item_groups:
                    item_groups[group_name] = 0.0
                item_groups[group_name] += line_total
            except Exception as e:
                output.append(f"      ⚠️ Neizdevās iegūt grupu: {e}")

        # Grupas apkopošana
        output.append("\n📚 Produktu grupas dokumentā:")
        output.append("=" * 60)
        for group, total in item_groups.items():
            output.append(f"🗂️ {group}: {total:.2f} EUR")

        return Response("\n".join(output), mimetype='text/plain')

    except Exception as e:
        return Response(f"❌ Kļūda: {str(e)}", mimetype='text/plain')

def parse_xml_to_dict(element):
    data = {}
    for child in element:
        if len(child):
            data[child.tag] = parse_xml_to_dict(child)
        else:
            data[child.tag] = child.text
    return data

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
