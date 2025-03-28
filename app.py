from flask import Flask, Response
import requests
import xml.etree.ElementTree as ET
import os

app = Flask(__name__)

API_KEY = os.environ.get("API_KEY")
API_TOKEN = os.environ.get("API_TOKEN")
SYNC_URL = "https://paytraq-to-pipedrive-basic-service-281111054789.us-central1.run.app/get-paytraq-orders"

def safe_text(el, path, default="—"):
    try:
        found = el.find(path)
        return found.text.strip() if found is not None and found.text else default
    except:
        return default

@app.route("/paytraq-full-report", methods=["GET"])
def paytraq_full_report():
    list_url = f"https://go.paytraq.com/api/sales?APIKey={API_KEY}&APIToken={API_TOKEN}"

    try:
        response = requests.get(list_url)
        response.raise_for_status()
    except Exception as e:
        return Response(f"❌ Kļūda saņemot dokumentu sarakstu: {e}", mimetype="text/plain")

    root = ET.fromstring(response.content)
    first_doc = root.find(".//Document/DocumentID")
    if first_doc is None:
        return Response("❌ Nav atrasts neviens dokuments.", mimetype="text/plain")

    document_id = first_doc.text
    output = [f"✅ Jaunākais dokumenta ID: {document_id}"]

    detail_url = f"https://go.paytraq.com/api/sale/{document_id}?APIKey={API_KEY}&APIToken={API_TOKEN}"
    try:
        detail_response = requests.get(detail_url)
        detail_response.raise_for_status()
    except Exception as e:
        return Response(f"❌ Kļūda iegūstot dokumenta datus: {e}", mimetype="text/plain")

    xml_string = detail_response.content
    detail_root = ET.fromstring(xml_string)

    doc_ref = safe_text(detail_root, ".//DocumentRef")
    doc_date = safe_text(detail_root, ".//DocumentDate")
    client_name = safe_text(detail_root, ".//ClientName")
    comment = safe_text(detail_root, ".//Comment")

    estimate_order = "—"
    if comment.startswith("M-860325"):
        estimate_order = comment.split(",")[0].strip()
    elif doc_ref.startswith("PAS/"):
        estimate_order = doc_ref

    output.append(f"📄 Dokumenta Nr.: {doc_ref}")
    output.append(f"📅 Dokumenta datums: {doc_date}")
    output.append(f"🧾 Komentārs: {comment}")
    output.append(f"📦 Estimate / Sales Order: {estimate_order}")
    output.append(f"🤑 Klients: {client_name}")

    output.append("\n📦 Produkti dokumentā:")
    output.append("=" * 60)
    line_items = detail_root.findall(".//LineItem")
    group_totals = {}
    if not line_items:
        output.append("❌ Produkti nav atrasti.")
    else:
        for idx, item in enumerate(line_items, 1):
            code = safe_text(item, ".//ItemCode")
            name = safe_text(item, ".//ItemName")
            qty = safe_text(item, "Qty")
            price = safe_text(item, "Price")
            total = safe_text(item, "LineTotal")
            unit = safe_text(item, ".//UnitName", default="gab.")
            item_id = safe_text(item, ".//ItemID")

            group_name = "—"
            group_id = "—"
            if item_id != "—":
                product_url = f"https://go.paytraq.com/api/product/{item_id}?APIToken={API_TOKEN}&APIKey={API_KEY}"
                try:
                    response = requests.get(product_url)
                    response.raise_for_status()
                    product_root = ET.fromstring(response.content)
                    group_name = safe_text(product_root, ".//Group/GroupName")
                    group_id = safe_text(product_root, ".//Group/GroupID")
                    group_totals[group_name] = group_totals.get(group_name, 0.0) + float(total.replace(",", "."))
                except:
                    group_name = "—"
                    group_id = "—"

            output.append(f"{idx}. {qty} x {name} ({code}) - {price} EUR [{unit}] → {total} EUR")
            output.append(f"   🔎 ItemID: {item_id}")
            output.append(f"   📂️ Grupa: {group_name} (ID: {group_id})")
            output.append("   🔍 Pilns XML par produktu:")
            for child in item.iter():
                tag = child.tag
                text = child.text.strip() if child.text else "—"
                output.append(f"      {tag}: {text}")

    client_id = safe_text(detail_root, ".//ClientID")
    output.append(f"\n🔎 ClientID: {client_id}")
    client_url = f"https://go.paytraq.com/api/client/{client_id}?APIToken={API_TOKEN}&APIKey={API_KEY}"
    try:
        client_response = requests.get(client_url)
        client_response.raise_for_status()
        client_root = ET.fromstring(client_response.text)

        email = safe_text(client_root, ".//Email")
        phone = safe_text(client_root, ".//Phone")
        reg_number = safe_text(client_root, ".//RegNumber")
        vat_number = safe_text(client_root, ".//Client/VATNumber")
        address = safe_text(client_root, ".//Address")
        city = safe_text(client_root, ".//City")
        zip_code = safe_text(client_root, ".//Zip")
        country = safe_text(client_root, ".//Country")

        output.append("\n📇 Klienta informācija:")
        output.append("=" * 60)
        output.append(f"💼 Nosaukums: {client_name}")
        output.append(f"✉️ E-pasts: {email}")
        output.append(f"📞 Telefons: {phone}")
        output.append(f"🏢 Reģistrācijas nr.: {reg_number}")
        output.append(f"🧾 PVN numurs: {vat_number}")
        output.append(f"📍 Adrese: {address}")
        output.append(f"       Pilsēta: {city}")
        output.append(f"       Pasta indekss: {zip_code}")
        output.append(f"       Valsts: {country}")

        # ✅ Šīs divas rindiņas izmanto automatizācijai:
        output.append(f"\n__REGNUM__:{reg_number}")
        output.append(f"__VATNUM__:{vat_number}")

    except Exception as e:
        output.append(f"❌ Neizdevās iegūt klienta datus: {e}")

    output.append("\n📊 Produktu grupas pasūtījumā ar kopsummām:")
    output.append("=" * 60)
    for group_name, total in group_totals.items():
        output.append(f"📂 {group_name}: {total:.2f} EUR")

    try:
        sync_response = requests.post(SYNC_URL, data=xml_string, headers={"Content-Type": "application/xml"})
        output.append("\n📤 Nosūtīts uz Pipedrive servisu:")
        output.append(sync_response.text)
    except Exception as e:
        output.append(f"❌ Kļūda sūot uz Pipedrive servisu: {e}")

    return Response("\n".join(output), mimetype="text/plain")

@app.route("/", methods=["GET"])
def index():
    return "✅ Serviss darbojas. Izmanto /paytraq-full-report, lai skatītu detalizētu atskaiti."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
