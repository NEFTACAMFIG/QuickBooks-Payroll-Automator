import os
import pandas as pd
import requests
import time
from dotenv import load_dotenv
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes

# 1. CARGAR CONFIGURACIÓN
load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
ENVIRONMENT = 'production'
REDIRECT_URI = os.getenv('REDIRECT_URI')

CUENTA_BANCO_ID = os.getenv('QB_CUENTA_BANCO_ID')
CUENTA_GASTO_ID = os.getenv('QB_CUENTA_GASTO_ID')

# 2. AUTENTICACIÓN ÚNICA
auth_client = AuthClient(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    environment=ENVIRONMENT,
    redirect_uri=REDIRECT_URI,
)

print(f"--- MODO PRODUCCIÓN: GENERACIÓN DE CHEQUES MULTI-LÍNEA ---")
auth_url = auth_client.get_authorization_url([Scopes.ACCOUNTING])
print(f"1. Abre esta URL y autoriza:\n{auth_url}")

auth_code = input("\n2. Pega el 'code' aquí: ")
realm_id = input("3. Pega el 'realmId' aquí: ")

auth_client.get_bearer_token(auth_code, realm_id=realm_id)
access_token = auth_client.access_token

# ==============================================
# 3. CARGAR DATOS Y AGRUPAR POR VENDOR
# ==============================================
archivo_excel = 'PROGRAMA_UNIDO_employees&projects_id.xlsx'
df_datos = pd.read_excel(archivo_excel)

#doc_number_inicial = int(input("\n4. Ingresa el número de cheque inicial: "))

# AGRUPAMOS por la columna 'id' para juntar las líneas de un mismo empleado
grupos_empleados = df_datos.groupby('id')

# ==============================================
# 4. CONFIGURAR ENDPOINT Y BUCLE
# ==============================================
base_url = "https://quickbooks.api.intuit.com"
url = f"{base_url}/v3/company/{realm_id}/purchase"

headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

print(f"\n🚀 Procesando {len(grupos_empleados)} cheques totales...")

for vendor_id, filas in grupos_empleados:

    lineas_del_cheque = []

    # Iteramos sobre las filas del grupo para crear las líneas
    for _, fila in filas.iterrows():
        # Extraer ID de proyecto si existe
        id_proyecto = str(int(fila['id_proyecto'])) if pd.notna(fila['id_proyecto']) else ""

        nombre_proyecto = fila.get('proyecto', '')
        if str(nombre_proyecto).strip().upper() == "OVERHEAD COSTS":
            nombre_proyecto = "Office"

        # Construir descripción según tu regla
        shift_hours = float(fila.get('Shift hours', 0.0))
        if shift_hours == 0:
            descripcion = "GAS"
        else:
            descripcion = f"{fila.get('Shift hours', '')} HRS {nombre_proyecto}"

        # Crear la estructura de la línea
        linea = {
            "Description": descripcion,
            "Amount": float(fila.get('Daily Amount', 0.0)),
            "DetailType": "AccountBasedExpenseLineDetail",
            "AccountBasedExpenseLineDetail": {
                "AccountRef": {
                    "value": CUENTA_GASTO_ID
                },
                "CustomerRef": {
                    "value": id_proyecto
                }
            }
        }
        lineas_del_cheque.append(linea)

    # Creamos el objeto del Cheque (Purchase) con todas sus líneas
    payload = {
        "PaymentType": "Check",
        #"DocNumber": str(doc_number_inicial),
        "PrintStatus": "NeedToPrint",
        "AccountRef": {
            "value": CUENTA_BANCO_ID
        },
        "EntityRef": {
            "value": str(int(vendor_id)),
            "type": "Vendor"
        },
        "TxnDate": time.strftime("%Y-%m-%d"),
        "PrivateNote": "",
        "Line": lineas_del_cheque
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        tid = response.headers.get('intuit_tid', 'N/A')

        if response.status_code == 200:
            nombre = f"{filas.iloc[0]['First name']} {filas.iloc[0]['Last name']}"
            print(f"✅ Cheque | {nombre} | {len(lineas_del_cheque)} líneas creadas.")
            #doc_number_inicial += 1  # Incrementar para el siguiente empleado
        else:
            print(f"❌ Error en cheque de {vendor_id} | Status: {response.status_code}")
            print(f"Respuesta: {response.text}")

    except Exception as e:
        print(f"🛑 Error crítico en comunicación: {e}")

    # Pausa mínima para estabilidad
    time.sleep(0.2)

print("\n--- PROCESO FINALIZADO ---")
