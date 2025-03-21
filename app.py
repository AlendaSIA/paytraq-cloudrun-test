import requests

# PayTraq API autentifikācijas dati
API_KEY = "421045bc-a402-4223-b048-52b65340e21a-98693"
API_TOKEN = "KcPtQHuxpxGbXCr4"

# PayTraq API URL priekš orders (sales)
url = f"https://go.paytraq.com/api/sales?APIKey={API_KEY}&APIToken={API_TOKEN}"

# Nosūtām GET pieprasījumu
response = requests.get(url)

# Pārbaudām atbildi
if response.status_code == 200:
    print("API pieslēgums veiksmīgs!")
    print(response.text)  # izdrukā visus saņemtos datus
else:
    print(f"API pieslēgums neizdevās, status kods: {response.status_code}")
    print(response.text)
