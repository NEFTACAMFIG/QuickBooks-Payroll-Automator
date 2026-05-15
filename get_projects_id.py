import os
import requests
import pandas as pd
from dotenv import load_dotenv
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes

# 1. Cargar las llaves del archivo .env
load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')
ENVIRONMENT = 'production'

# 2. Iniciar sesión para obtener permiso
auth_client = AuthClient(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    environment=ENVIRONMENT,
    redirect_uri=REDIRECT_URI,
)

auth_url = auth_client.get_authorization_url([Scopes.ACCOUNTING])
print(f"--- PASO 1: AUTORIZACIÓN ---")
print(f"Entra a este link:\n{auth_url}")

auth_code = input("\n--- PASO 2: PEGA EL CODE --- \n> ")
realm_id = input("\n--- PASO 3: PEGA EL REALMID --- \n> ")

auth_client.get_bearer_token(auth_code, realm_id=realm_id)

# 3. CONSULTA A LA API
base_url = "https://quickbooks.api.intuit.com"
# Traemos Id y el nombre completo (jerárquico)
query = "SELECT Id, FullyQualifiedName, DisplayName FROM Customer MAXRESULTS 1000"
url = f"{base_url}/v3/company/{realm_id}/query?query={query}"

headers = {
    "Authorization": f"Bearer {auth_client.access_token}",
    "Accept": "application/json"
}

print("\n--- PASO 4: PROCESANDO PROYECTOS ---")
response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    entidades = data.get('QueryResponse', {}).get('Customer', [])

    if not entidades:
        print("No se encontraron clientes.")
    else:
        # Convertimos a DataFrame para procesar fácilmente
        df = pd.DataFrame(entidades)

        # Seleccionamos columnas y renombramos
        # Usamos FullyQualifiedName porque suele ser el que contiene la ruta del proyecto
        df = df[['Id', 'DisplayName']].rename(columns={'Id': 'id', 'DisplayName': 'proyecto'})

        # --- LISTA DE IDs A ELIMINAR (Tu lista negra) ---
        ids_a_eliminar = [
            '416', '411', '524', '376', '369', '419', '511', '477', '371', '529',
            '394', '373', '386', '435', '556', '513', '611', '489', '409', '414',
            '398', '377', '366', '613', '372', '367', '620', '604', '385', '418',
            '474', '484', '517', '365', '733', '397', '406', '460', '609', '415',
            '487', '766', '393', '396', '368'
        ]

        # Aplicamos el filtro: Mantener solo los IDs que NO están en la lista negra
        df_final = df[~df['id'].isin(ids_a_eliminar)].copy()

        # 4. EXPORTAR A .TXT E IMPRIMIR
        nombre_archivo = "projects.txt"

        # Guardamos como TXT separado por comas
        df_final.to_csv(nombre_archivo, index=False, sep=',')

        print("\n" + "=" * 50)
        print("         LISTA DE PROYECTOS FILTRADA")
        print("=" * 50)
        print(df_final.to_string(index=False))
        print("=" * 50)

        print(f"\n✅ Proceso terminado.")
        print(f"Registros originales: {len(df)}")
        print(f"Registros eliminados: {len(df) - len(df_final)}")
        print(f"Archivo guardado como: {os.path.abspath(nombre_archivo)}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
