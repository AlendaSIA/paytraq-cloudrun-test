
from flask import Flask, jsonify, Response
import requests
from datetime import datetime
import xml.etree.ElementTree as ET
import os

app = Flask(__name__)

API_KEY = os.environ.get("API_KEY")
API_TOKEN = os.environ.get("API_TOKEN")

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
        doc_id = doc.findtext("DocumentID", default="—")
        doc_number = doc.findtext("DocumentNumber", default="—")
        client = doc.find(".//Company")
        line_items = doc.findall(".//LineItem")

        output = []
        output.append(f"✅ Jaunākais dokumenta ID: {doc_id}")
        output.append(f"📄 Dokumenta Nr.: {doc_number}")
        output.append(f"👤 Klients: {client.findtext('Name', default='—')}")
        output.append("\n📦 Produkti dokumentā:")
        output.append("=" * 60)

        item_groups = {}

        for idx, item in enumerate(line_items, 1):
            qty = item.findtext("Qty", default="—")
            name = item.findtext("ItemName", default="—")
            code = item.findtext("ItemCode", default="—")
            price = item.findtext("Price", default="—")
            unit = item.findtext(".//UnitName", default="—")
            total = item.findtext("LineTotal", default="—")
            item_id = item.findtext("ItemID", default="—")

            output.append(f"{idx}. {qty} x {name} ({code}) - {price} EUR [{unit}] → {total} EUR")
            output.append(f"   🔎 ItemID: {item_id}")

            # Grupas iegūšana
            product_url = f"https://go.paytraq.com/api/product/{item_id}?APIToken={API_TOKEN}&APIKey={API_KEY}"
            try:
                product_response = requests.get(product_url)
                product_response.raise_for_status()
                product_root = ET.fromstring(product_response.content)
                group_name = product_root.findtext(".//Group/GroupName", default="—").strip()
                line_total = float(total.replace(",", ".")) if total != "—" else 0.0

                if group_name not in item_groups:
                    item_groups[group_name] = 0.0
                item_groups[group_name] += line_total
            except Exception:
                output.append(f"   ⚠️ Neizdevās iegūt grupu")

        output.append("\n📚 Produktu grupas dokumentā:")
        output.append("=" * 60)
        for group, total in item_groups.items():
            output.append(f"🗂️ {group}: {total:.2f} EUR")

        # Klienta informācija (visas iespējamās vērtības ar def. “—”)
        output.append("\n📋 Klienta informācija:")
        output.append("=" * 60)
        output.append(f"🏢 Nosaukums: {client.findtext('CompanyName', default='—')}")
        output.append(f"📧 E-pasts: {client.findtext('Email', default='—')}")
        output.append(f"📞 Telefons: {client.findtext('Phone', default='—')}")
        output.append(f"🧾 Reģistrācijas nr.: {client.findtext('RegNumber', default='—')}")

        address_parts = [
            client.findtext("Address/Street", default="—"),
            client.findtext("Address/City", default="—"),
            client.findtext("Address/State", default="—"),
            client.findtext("Address/Zip", default="—"),
            client.findtext("Address/Country", default="—")
        ]
        output.append(f"📍 Adrese: {', '.join(address_parts)}")

        return Response("\n".join(output), mimetype='text/plain')

    except Exception as e:
        return Response(f"❌ Kļūda: {str(e)}", mimetype='text/plain')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
