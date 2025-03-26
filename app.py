from flask import Flask, jsonify, Response
import requests
from datetime import datetime
import xml.etree.ElementTree as ET
import os

app = Flask(__name__)

API_KEY = os.environ.get("API_KEY")
API_TOKEN = os.environ.get("API_TOKEN")
SYNC_URL = "https://paytraq-to-pipedrive-basic-service-281111054789.us-central1.run.app/sync"

@app.route('/', methods=['GET'])
def index():
    return jsonify({"message": "Sveiki! Serviss darbojas. Izmanto /get-paytraq-orders lai ielādētu un sinhronizētu datus."})

def safe_text(el, path, default="—"):
    try:
        found = el.find(path)
        return found.text if found is not None and found.text else default
    except:
        return default

@app.route('/paytraq-full-report', methods=['GET'])
def paytraq_full_report():
    today = datetime.today().strftime('%Y-%m-%d')
    url = f"https://go.paytraq.com/api/sales?APIKey={API_KEY}&APIToken={API_TOKEN}&DateFrom={today}&DateTo={today}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        sales = root.findall(".//Sale")
        if not sales:
            return "❌ Nav atrasts neviens dokuments."

        header = sales[0].find("Header")
        if header is None:
            return "❌ Dokumenta struktūra nav korekta (nav Header)."

        doc = header.find("Document")
        if doc is None:
            return "❌ Dokumenta struktūra nav korekta (nav Document)."

        doc_id = safe_text(doc, "DocumentID")
        doc_number = safe_text(doc, "DocumentNumber")
        client_name = safe_text(doc.find("Client"), "ClientName")

        output = []
        output.append(f"✅ Jaunākais dokumenta ID: {doc_id}")
        output.append(f"📄 Dokumenta Nr.: {doc_number}")
        output.append(f"🧑 Klients: {client_name}\n")

        output.append("📦 Produkti dokumentā:")
        output.append("=" * 60)

        item_groups = {}
        line_items = doc.findall(".//LineItem")
        for idx, item in enumerate(line_items, 1):
            qty = safe_text(item, "Qty")
            name = safe_text(item, "ItemName")
            code = safe_text(item, "ItemCode")
            price = safe_text(item, "Price")
            unit = safe_text(item, "UnitName")
            total = safe_text(item, "LineTotal")
            item_id = safe_text(item, "ItemID")

            output.append(f"{idx}. {qty} x {name} ({code}) - {price} EUR [{unit}] → {total} EUR")
            output.append(f"   🔎 ItemID: {item_id}")

            product_url = f"https://go.paytraq.com/api/product/{item_id}?APIToken={API_TOKEN}&APIKey={API_KEY}"
            try:
                product_response = requests.get(product_url)
                product_response.raise_for_status()
                product_root = ET.fromstring(product_response.content)
                group_name = safe_text(product_root, ".//Group/GroupName")
                line_total = float(total.replace(",", ".")) if total not in ("", "—") else 0.0

                if group_name not in item_groups:
                    item_groups[group_name] = 0.0
                item_groups[group_name] += line_total
            except Exception as e:
                output.append(f"   ⚠️ Neizdevās iegūt grupu: {e}")

        output.append("\n📚 Produktu grupas dokumentā:")
        output.append("=" * 60)
        for group, total in item_groups.items():
            output.append(f"🗂️ {group}: {total:.2f} EUR")

        # Klienta papildu informācija
        output.append("\n📋 Klienta informācija:")
        output.append("=" * 60)
        company = doc.find("Company")
        output.append(f"🏢 Nosaukums: {safe_text(company, 'Name')}")
        output.append(f"📧 E-pasts: {safe_text(company, 'Email')}")
        output.append(f"📞 Telefons: {safe_text(company, 'Phone')}")
        output.append(f"🆔 Reģistrācijas nr.: {safe_text(company, 'RegistrationNo')}")

        address_parts = []
        for tag in ['Street', 'City', 'State', 'Postcode', 'CountryCode']:
            part = safe_text(company.find("Address") if company is not None else None, tag)
            address_parts.append(part)
        full_address = ", ".join(address_parts)
        output.append(f"📍 Adrese: {full_address}")

        return Response("\n".join(output), mimetype='text/plain')

    except Exception as e:
        return Response(f"❌ Kļūda: {str(e)}", mimetype='text/plain')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
