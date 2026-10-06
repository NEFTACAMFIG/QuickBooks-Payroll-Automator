import pandas as pd
import os
import requests
from dotenv import load_dotenv
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes

# ==========================================
# 1. CARGAR CONFIGURACIÓN Y AUTENTICACIÓN
# ==========================================
load_dotenv()

auth_client = AuthClient(
    client_id=os.getenv('CLIENT_ID'),
    client_secret=os.getenv('CLIENT_SECRET'),
    environment='production',
    redirect_uri=os.getenv('REDIRECT_URI'),
)

print(f"--- PASO 1: AUTORIZACIÓN PARA INVOICES ---")
print(f"Entra a este link:\n{auth_client.get_authorization_url([Scopes.ACCOUNTING])}")

auth_code = input("\n--- PASO 2: PEGA EL CODE --- \n> ")
realm_id = input("\n--- PASO 3: PEGA EL REALMID --- \n> ")

auth_client.get_bearer_token(auth_code, realm_id=realm_id)

base_url = "https://quickbooks.api.intuit.com"
headers = {
    "Authorization": f"Bearer {auth_client.access_token}",
    "Accept": "application/json"
}

# ID del Cliente Principal a filtrar en Pandas
TARGET_PARENT_ID = "397"

# ==========================================
# 2. OBTENCIÓN Y MAPEO DE CUSTOMERS / PROYECTOS
# ==========================================
print("\n--- PASO 4: DESCARGANDO CATÁLOGO DE CUSTOMERS Y PROYECTOS ---")

query_customers = "SELECT Id, DisplayName, ParentRef FROM Customer MAXRESULTS 1000"
url_cust = f"{base_url}/v3/company/{realm_id}/query?query={query_customers}"

resp_cust = requests.get(url_cust, headers=headers)

mapa_parent = {}
if resp_cust.status_code == 200:
    customers = resp_cust.json().get('QueryResponse', {}).get('Customer', [])
    for c in customers:
        cust_id = str(c.get('Id')).strip()
        # Si tiene ParentRef, guardamos el ID de su padre; de lo contrario, el ID es el mismo
        parent_id = str(c.get('ParentRef', {}).get('value', cust_id)).strip()
        mapa_parent[cust_id] = parent_id
else:
    print(f"⚠️ Error al descargar catálogo de clientes: {resp_cust.status_code}")

# ==========================================
# 3. OBTENCIÓN DE TODAS LAS INVOICES
# ==========================================
print("\n--- PASO 5: DESCARGANDO TODAS LAS INVOICES DE LA EMPRESA ---")

# Descargamos las facturas ordenadas de la más reciente a la más antigua
query_invoices = "SELECT Id, DocNumber, CustomerRef, TotalAmt, Balance, TxnDate FROM Invoice ORDERBY TxnDate DESC MAXRESULTS 1000"
url_inv = f"{base_url}/v3/company/{realm_id}/query?query={query_invoices}"

resp_inv = requests.get(url_inv, headers=headers)

if resp_inv.status_code == 200:
    lista_invoices = resp_inv.json().get('QueryResponse', {}).get('Invoice', [])

    if not lista_invoices:
        print("❌ No se encontró ninguna Factura en la cuenta.")
    else:
        # ==========================================
        # 4. PROCESAMIENTO POSTERIOR CON PANDAS
        # ==========================================
        registros = []
        for inv in lista_invoices:
            cust_ref = inv.get('CustomerRef', {})
            project_id = str(cust_ref.get('value', '')).strip()
            project_name = cust_ref.get('name', 'N/A')

            # Mapeamos a qué Cliente Padre pertenece este proyecto
            parent_customer_id = mapa_parent.get(project_id, project_id)

            registros.append({
                'invoice_id': str(inv.get('Id')).strip(),
                'doc_number': str(inv.get('DocNumber', 'N/A')).strip(),
                'project_id': project_id,
                'project_name': project_name,
                'parent_customer_id': parent_customer_id,
                'date': inv.get('TxnDate', 'N/A'),
                'total_amount': float(inv.get('TotalAmt', 0.0)),
                'balance': float(inv.get('Balance', 0.0))
            })

        # Convertimos la lista completa a un DataFrame de Pandas
        df_todas = pd.DataFrame(registros)

        # REGLA DE FILTRADO LOCAL EN PANDAS:
        # Mantenemos las facturas cuyo project_id O parent_customer_id coincidan con TARGET_PARENT_ID
        df_filtrado = df_todas[
            (df_todas['project_id'] == str(TARGET_PARENT_ID)) |
            (df_todas['parent_customer_id'] == str(TARGET_PARENT_ID))
        ].copy()

        if df_filtrado.empty:
            print(f"\n⚠️ No se encontraron facturas vinculadas al Cliente o Proyectos del Parent ID {TARGET_PARENT_ID}.")
        else:
            # Seleccionamos las columnas definitivas
            df_final = df_filtrado[['invoice_id', 'doc_number', 'project_name', 'date', 'total_amount', 'balance']]

            # ==========================================
            # 5. IMPRESIÓN EN PANTALLA Y EXPORTACIÓN A TXT
            # ==========================================
            nombre_archivo = "invoices_id_SYSTEMS.txt"

            # Exportar a TXT separado por comas
            df_final.to_csv(nombre_archivo, index=False, sep=',')

            # IMPRESIÓN FORMATEADA EN CONSOLA
            print("\n" + "=" * 85)
            print(f"   INVOICES ENCONTRADAS PARA EL CLIENTE ID {TARGET_PARENT_ID} (Y SUS PROYECTOS)")
            print("=" * 85)
            print(df_final.to_string(index=False))
            print("=" * 85)

            print(f"\n✅ Archivo generado: {os.path.abspath(nombre_archivo)}")
            print(f"Total de facturas exportadas: {len(df_final)}")

else:
    print(f"Error al consultar la API de Invoices: {resp_inv.status_code}")
    print(resp_inv.text)
