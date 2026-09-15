# =========================================================================
# PARTE 1: CÁLCULOS DE HORAS, BREAKS, NOTAS Y LÍNEAS DE REEMBOLSO/EXTRA
# =========================================================================
lista_archivos = ['timeclock-timesheet_overview_2026-09-07_2026-09-13.xlsx']

for excel_file in lista_archivos:
    try:
        print(f"🔄 Procesando: {excel_file}...")
        df_original = pd.read_excel(excel_file)

        # --- 1. MAPEADOR DE NOTAS CON FECHAS PARA HORAS REGULARES ---
        df_notas = df_original[["Employee ID", "Type", "Start Date", "Employee notes", "Manager notes"]].copy()
        df_notas[["Employee ID", "Type", "Start Date"]] = df_notas[["Employee ID", "Type", "Start Date"]].ffill()

        for col in ["Employee notes", "Manager notes"]:
            df_notas[col] = df_notas[col].astype(str).replace(['nan', 'None', 'NaN'], '').str.strip()

        df_notas['Employee notes_with_date'] = df_notas.apply(
            lambda r: f"{r['Start Date'].strftime('%m/%d')}: {r['Employee notes']}" if r['Employee notes'] else "",
            axis=1
        )
        df_notas['Manager notes_with_date'] = df_notas.apply(
            lambda r: f"{r['Start Date'].strftime('%m/%d')}: {r['Manager notes']}" if r['Manager notes'] else "", axis=1
        )


        def juntar_todo(series):
            lista = [s for s in series if s != ""]
            return " | ".join(lista)


        mapping_notas = df_notas.groupby(['Employee ID', 'Type']).agg({
            'Employee notes_with_date': juntar_todo,
            'Manager notes_with_date': juntar_todo
        }).reset_index().rename(columns={
            'Employee notes_with_date': 'Employee notes',
            'Manager notes_with_date': 'Manager notes'
        })

        # --- 2. CÁLCULOS DE HORAS Y BREAK ---
        # Aseguramos incluir las nuevas columnas "Food" y "Extra Labor"
        cols_base = ["Employee ID", "First name", "Last name", "Type", "Start Date",
                     "Shift hours", "Hourly rate (USD)", "Gas amount", "Food", "Extra Labor", "Manager notes"]

        working_hours = df_original[cols_base].copy()
        working_hours[["Employee ID", "First name", "Last name", "Type", "Start Date"]] = working_hours[
            ["Employee ID", "First name", "Last name", "Type", "Start Date"]].ffill()

        # Convertir montos numéricos
        for col_monto in ["Gas amount", "Food", "Extra Labor"]:
            working_hours[col_monto] = pd.to_numeric(working_hours[col_monto], errors='coerce').fillna(0)

        working_hours['Employee ID'] = working_hours['Employee ID'].astype(int).astype(str).str.zfill(5)
        working_hours['Shift hours'] = pd.to_numeric(working_hours['Shift hours'], errors='coerce').fillna(0)
        working_hours['Hourly rate (USD)'] = pd.to_numeric(working_hours['Hourly rate (USD)'], errors='coerce').fillna(
            0)

        # Descuento de break (solo en horas trabajadas)
        working_hours['Total_Dia'] = working_hours.groupby(['Employee ID', 'Start Date'])['Shift hours'].transform(
            'sum')
        es_primera_vez = ~working_hours.duplicated(subset=['Employee ID', 'Start Date'], keep='first')

        working_hours['break_discount'] = 0.0
        working_hours.loc[(es_primera_vez) & (working_hours['Total_Dia'] >= 5.5), 'break_discount'] = 0.5
        working_hours['Shift hours'] = working_hours['Shift hours'] - working_hours['break_discount']
        working_hours['Daily Amount'] = working_hours['Shift hours'] * working_hours['Hourly rate (USD)']

        # --- 3. EXTRACCIÓN DINÁMICA DE REEMBOLSOS (GAS, FOOD, EXTRA LABOR) ---
        # Definimos los tipos de línea adicionales: (Nombre Columna, Etiqueta Line_Type, Prioridad de Orden)
        reembolsos_config = [
            ('Gas amount', 'GAS', 2),
            ('Food', 'FOOD', 3),
            ('Extra Labor', 'EXTRA_LABOR', 4)
        ]

        lista_dfs_adicionales = []

        for col_nombre, line_type, prioridad in reembolsos_config:
            filas_monto = working_hours[working_hours[col_nombre] > 0].copy()
            if not filas_monto.empty:
                filas_monto['Manager notes_clean'] = filas_monto['Manager notes'].astype(str).replace(
                    ['nan', 'None', 'NaN'], '').str.strip()
                filas_monto['Manager notes_fmt'] = filas_monto.apply(
                    lambda r: f"{r['Start Date'].strftime('%m/%d')}: {r['Manager notes_clean']}" if r[
                        'Manager notes_clean'] else "",
                    axis=1
                )

                df_temp = pd.DataFrame({
                    'Employee ID': filas_monto['Employee ID'],
                    'First name': filas_monto['First name'],
                    'Last name': filas_monto['Last name'],
                    'Type': filas_monto['Type'],
                    'Line_Type': line_type,  # <--- IDENTIFICADOR DE TIPO
                    'Shift hours': 0.0,
                    'Hourly rate (USD)': 0.0,
                    'Daily Amount': filas_monto[col_nombre],  # El monto va a Daily Amount
                    'Employee notes': '',
                    'Manager notes': filas_monto['Manager notes_fmt'],
                    'Order_Priority': prioridad  # Mantiene el orden por empleado
                })
                lista_dfs_adicionales.append(df_temp)

        # --- 4. AGRUPACIÓN DE HORAS REGULARES (PRIORIDAD 1) ---
        df_final_p1 = working_hours.groupby(['Employee ID', 'Type']).agg({
            'Shift hours': 'sum',
            'Daily Amount': 'sum',
            'First name': 'first',
            'Last name': 'first',
            'Hourly rate (USD)': 'first'
        }).reset_index()

        df_final_p1['Line_Type'] = 'REGULAR'  # <--- IDENTIFICADOR
        df_final_p1['Order_Priority'] = 1

        # Unir notas acumuladas a las horas normales
        mapping_notas['Employee ID'] = mapping_notas['Employee ID'].astype(int).astype(str).str.zfill(5)
        df_final_p1 = pd.merge(df_final_p1, mapping_notas, on=['Employee ID', 'Type'], how='left').fillna("")

        columnas_orden = ['Employee ID', 'First name', 'Last name', 'Type', 'Line_Type', 'Shift hours',
                          'Hourly rate (USD)', 'Daily Amount', 'Employee notes', 'Manager notes',
                          'Order_Priority']

        df_final_p1 = df_final_p1[columnas_orden]

        # --- 5. CONCATENAR TODO Y ORDENAR ---
        todos_los_dfs = [df_final_p1] + lista_dfs_adicionales
        df_excel = pd.concat(todos_los_dfs, ignore_index=True)

        # Ordenar por Empleado y Prioridad (Horas -> Gas -> Food -> Extra Labor)
        df_excel = df_excel.sort_values(by=['Employee ID', 'Order_Priority']).drop(columns=['Order_Priority'])

        # =========================================================================
        # PARTE 2: MAPEADOR DE VENDORS Y PROYECTOS (PROGRAMA 2)
        # =========================================================================

        # Cargar TXT de Vendedores (IDs de empleados)
        df_txt_vendors = pd.read_csv('vendors_id.txt')
        df_txt_vendors['codigo_comparar'] = df_txt_vendors['name'].str.split('-').str[0].str.strip()

        # Cargar TXT de Proyectos
        df_projects = pd.read_csv('projects.txt')


        # DICCIONARIOS Y FUNCIONES DE LIMPIEZA
        def normalizar_y_limpiar(texto):
            if pd.isna(texto): return ""
            texto = str(texto).upper().replace(",", "").replace(".", "")
            return " ".join(texto.split())


        mapeo_manual_raw = {
            "OYH TPO BLDG PH1": "OYH Phase 1  TPO Building",
            "BG PRODUCTS RENOVATION PHASE 1": "BG PRODUCTS EXTERIOR PAINTING",
            "GULFBELT LOGISTICS PARK": "GULF BELT LOGISTICS",
            "RAUS OFFICE EXTERIOR - 5027, 1181 BRITTMOORE RD STE 100": "RAUS CONSTRUCTION OFFICES EXTERIOR REPAINT",
            "CITADEL OFFICE PARK (21 UNITS)": "CITADEL OFFICE PARK",
            "Office": "OVERHEAD COSTS"
        }

        mapeo_limpio = {normalizar_y_limpiar(k): normalizar_y_limpiar(v) for k, v in mapeo_manual_raw.items()}


        def buscar_proyecto(valor_excel, lista_proyectos_txt):
            if not valor_excel: return None
            if valor_excel in mapeo_limpio:
                return mapeo_limpio[valor_excel]
            if "OFFICE" in valor_excel:
                return None
            resultado = process.extractOne(valor_excel, lista_proyectos_txt, scorer=fuzz.token_set_ratio)
            if resultado and resultado[1] >= 80:
                return resultado[0]
            return None


        # --- PASO 1: Unir por Employee ID ---
        print("Procesando unión por Employee ID...")
        df_final = pd.merge(
            df_excel,
            df_txt_vendors,
            left_on='Employee ID',
            right_on='codigo_comparar',
            how='left',
            sort=False  # Mantiene el orden de agrupación que definimos
        )

        df_final = df_final.drop(columns=['codigo_comparar', 'name'])
        df_final.to_excel('resultado_unido_employees_id.xlsx', index=False)

        # --- PASO 2: Procesar Proyectos ---
        print("Procesando proyectos y casos especiales...")
        df_projects['Proyecto_Clean'] = df_projects['proyecto'].apply(normalizar_y_limpiar)
        lista_proyectos_txt = df_projects['Proyecto_Clean'].tolist()

        df_final['Type_Normalizado'] = df_final['Type'].apply(normalizar_y_limpiar)

        df_final['Proyecto_Final'] = df_final['Type_Normalizado'].apply(
            lambda x: buscar_proyecto(x, lista_proyectos_txt)
        )

        df_final_projects = pd.merge(
            df_final,
            df_projects,
            left_on='Proyecto_Final',
            right_on='Proyecto_Clean',
            how='left',
            sort=False  # Mantiene el orden de agrupación que definimos
        )

        # LIMPIEZA FINAL Y EXPORTACIÓN
        df_final_projects = df_final_projects.drop(columns=['Type_Normalizado', 'Proyecto_Final', 'Proyecto_Clean'])
        df_final_projects = df_final_projects.rename(columns={'id_x': 'id', 'id_y': 'id_proyecto'})

        df_final_projects.to_excel('PROGRAMA_UNIDO_employees&projects_id.xlsx', index=False)

        print("\n✅ ¡Hecho! Proceso completado exitosamente con registros agrupados por empleado.")
        print("1. resultado_unido_employees_id.xlsx")
        print("2. PROGRAMA_UNIDO_employees&projects_id.xlsx")

    except Exception as e:
        print(f"❌ Error: {e}")
