import requests
from bs4 import BeautifulSoup
import os
import pandas as pd
from datetime import datetime
import json
import re
import matplotlib.pyplot as plt
import seaborn as sns
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
import sys

# ==============================================================================
# ----------------------------
# CONFIGURACIÓN (editar si hace falta)
# ----------------------------

# Credenciales y destino del email
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
# REEMPLAZAR con sus credenciales de email
EMAIL_USER = 'wifienrosario@gmail.com' 
EMAIL_PASSWORD = 'zrmr mgws hjtz brsk' 
EMAIL_RECIPIENT = 'arqderman@gmail.com'

# Archivos
MASTER_CSV = "rockandfellers_precios.csv"
REPORT_XLSX = "rockandfellers_reporte.xlsx"
CHART_DIR = "charts_rockandfellers"

# URL principal del menú
URL_MENU_PRINCIPAL = 'https://rockandfellers.com.ar/cartas-qr/rock-feller-s-boulevard-orono/restaurante'

# API del Dólar
API_DOLAR_URL = "https://api.comparadolar.ar/usd"

# Crear directorio para gráficos
os.makedirs(CHART_DIR, exist_ok=True)
# ==============================================================================

# --- Funciones de Lógica de Extracción de Precios (Dólar) ---

def obtener_precio_dolar_api(url_api):
    """
    Realiza una solicitud a la API del dólar, busca la cotización de 
    Banco Nación y retorna el valor 'ask' (venta). 
    Lógica sincronizada con hacienda.py para mayor precisión.
    """
    print("🔎 Intentando obtener cotización del dólar de la API...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url_api, headers=headers, timeout=10)
        response.raise_for_status() 
        
        data = response.json() 
        
        cotizacion_nacion = next((item for item in data if item.get('slug') == 'banco-nacion'), None)
        
        if cotizacion_nacion and 'ask' in cotizacion_nacion:
            precio_dolar = float(cotizacion_nacion['ask'])
            print(f"✅ Precio del Dólar Oficial (Banco Nación, Venta - ask) extraído: ${precio_dolar:,.2f} ARS")
            return precio_dolar
        else:
            print("❌ No se pudo encontrar la cotización 'banco-nacion' o el campo 'ask'. Usando 1.0.")
            return 1.0

    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión al obtener el precio del dólar de la API: {e}. Usando 1.0.")
        return 1.0
    except Exception as e:
        print(f"❌ Error inesperado al obtener el dólar: {e}. Usando 1.0.")
        return 1.0

# --- Funciones de Data Management (CSV Maestro) ---

def cargar_o_crear_maestro():
    """Carga el DataFrame maestro desde CSV o crea uno nuevo."""
    columnas = ['Fecha', 'Producto', 'Categoria', 'Subcategoria', 'Descripcion_Corta', 'Precio_ARS', 'Precio_USD', 'Dolar_ARS'] 
    
    if os.path.exists(MASTER_CSV):
        try:
            df = pd.read_csv(MASTER_CSV)
            df['Fecha'] = pd.to_datetime(df['Fecha']).dt.normalize()
            
            # Asegurar que todas las columnas existan
            if all(col in df.columns for col in columnas):
                return df[columnas]
            else:
                # Si faltan columnas, agregar las faltantes (ej. Dolar_ARS, Precio_USD)
                for col in columnas:
                    if col not in df.columns:
                        df[col] = None 
                return df[columnas] 

        except Exception as e:
            print(f"⚠️ Error al leer el CSV: {e}. Creando un DataFrame vacío.")
            return pd.DataFrame(columns=columnas)
    else:
        print("📁 Archivo maestro no encontrado. Creando uno nuevo.")
        return pd.DataFrame(columns=columnas)

def guardar_datos(df, nombre, precio_ars, categoria, subcategoria, descripcion_corta, dolar_ars):
    """Añade los datos de hoy al maestro si no existe una entrada para la fecha y el producto."""
    now = datetime.now() 
    hoy = now.date()
    
    df_temp = df.copy()
    if not df_temp.empty:
        # Convertir la columna de Fecha (datetime) a solo la fecha (date)
        df_temp['Fecha_Dia'] = df_temp['Fecha'].dt.date
    else:
        # Si está vacío, se inicializa la columna de comparación
        df_temp['Fecha_Dia'] = pd.Series([], dtype='object')
    
    # === LÓGICA DE DUPLICACIÓN POR DÍA Y PRODUCTO ===
    ya_existe = ((df_temp['Fecha_Dia'] == hoy) & (df_temp['Producto'] == nombre)).any()

    if ya_existe:
        return df 
    
    else:
        precio_usd = precio_ars / dolar_ars
        fecha_almacenamiento = now.replace(hour=0, minute=0, second=0, microsecond=0) 
        
        nueva_fila = pd.DataFrame([{
            'Fecha': fecha_almacenamiento,
            'Producto': nombre,
            'Categoria': categoria,
            'Subcategoria': subcategoria,
            'Descripcion_Corta': descripcion_corta,
            'Precio_ARS': precio_ars,
            'Precio_USD': precio_usd,
            'Dolar_ARS': dolar_ars
        }])
        
        df_final = pd.concat([df, nueva_fila], ignore_index=True)
        df_final = df_final.sort_values(by=['Fecha', 'Producto']).reset_index(drop=True)
        
        df_final.to_csv(MASTER_CSV, index=False)
        return df_final

# ==============================================================================
# ----------------------------
# FUNCIÓN DE RASTREO ESPECÍFICA PARA LIVEWIRE
# ----------------------------

def rastrear_menu(url):
    """Rastrea el menú extrayendo el JSON del atributo 'wire:initial-data'."""
    print(f"⚙️ Rastreo iniciado en: {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Error al acceder a la URL: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    livewire_div = soup.find('div', attrs={'wire:initial-data': True})

    if not livewire_div:
        print("❌ No se encontró el contenedor Livewire.")
        return []

    initial_data_json = livewire_div['wire:initial-data']
    try:
        initial_data = json.loads(initial_data_json)
    except json.JSONDecodeError as e:
        print(f"❌ Error al decodificar JSON: {e}")
        return []

    menu_data = initial_data.get('serverMemo', {}).get('data', {}).get('menus', {})

    if not menu_data:
        return []

    productos_encontrados = []

    for rubro_index, rubro in menu_data.items():
        if not isinstance(rubro, dict): continue
        category_name = rubro.get('name', 'N/A').strip('- ').title() 

        for subrubro in rubro.get('subrubros', []):
            if not isinstance(subrubro, dict): continue
            subcategory_name = subrubro.get('name', 'N/A').strip().title()
            
            products = subrubro.get('products', {})
            products_list = list(products.values()) if isinstance(products, dict) else products
            
            for product in products_list:
                if isinstance(product, dict):
                    nombre_producto = product.get('name', 'N/A')
                    descripcion_corta = product.get('short_description', 'N/A')
                    
                    precio = None
                    product_details = product.get('product_details')
                    if product_details and isinstance(product_details, list) and product_details:
                        precio_str = product_details[0].get('default_price')
                        if precio_str:
                            try:
                                precio = float(precio_str)
                            except ValueError:
                                precio = None
                    
                    if precio is not None and precio > 0:
                        productos_encontrados.append({
                            'nombre': nombre_producto,
                            'precio_ars': precio,
                            'categoria': category_name,
                            'subcategoria': subcategory_name,
                            'descripcion_corta': descripcion_corta
                        })

    print(f"✅ Extracción de datos finalizada. Productos encontrados: {len(productos_encontrados)}")
    return productos_encontrados

# ==============================================================================
# ----------------------------
# FUNCIONES DE REPORTE, ANÁLISIS Y EMAIL
# ----------------------------

def calcular_variacion_historica(df):
    """Calcula la variación porcentual histórica."""
    now = datetime.now().date()
    df_historico = df.copy()
    df_historico['Fecha'] = df_historico['Fecha'].dt.date
    productos = df_historico['Producto'].unique()
    resultados_lista = []
    
    for producto in productos:
        df_prod = df_historico[df_historico['Producto'] == producto].sort_values(by='Fecha')
        if df_prod.empty: continue
        precio_actual = df_prod.iloc[-1]['Precio_ARS']
        categoria_producto = df_prod.iloc[-1]['Categoria']
        subcategoria_producto = df_prod.iloc[-1]['Subcategoria']
        
        precio_ayer = df_prod[df_prod['Fecha'] < now].tail(1)['Precio_ARS'].iloc[0] if not df_prod[df_prod['Fecha'] < now].empty else None
        hace_30_dias = now - pd.Timedelta(days=30)
        precio_mes = df_prod[df_prod['Fecha'] <= hace_30_dias].tail(1)['Precio_ARS'].iloc[0] if not df_prod[df_prod['Fecha'] <= hace_30_dias].empty else None
        hace_1_año = now - pd.Timedelta(days=365)
        precio_año = df_prod[df_prod['Fecha'] <= hace_1_año].tail(1)['Precio_ARS'].iloc[0] if not df_prod[df_prod['Fecha'] <= hace_1_año].empty else None

        def calcular_pct_change(precio_actual, precio_ref):
            if precio_ref is not None and precio_ref > 0:
                return ((precio_actual - precio_ref) / precio_ref) * 100
            return None

        var_dia = calcular_pct_change(precio_actual, precio_ayer)
        var_mes = calcular_pct_change(precio_actual, precio_mes)
        var_año = calcular_pct_change(precio_actual, precio_año)

        resultados_lista.append({
            'Producto': producto,
            'Categoria': categoria_producto,
            'Subcategoria': subcategoria_producto,
            'Precio Actual (ARS)': f"${precio_actual:,.2f}",
            'Variacion vs Ayer': f"{var_dia:.2f}%" if var_dia is not None else "-",
            'Variacion vs 30 Días': f"{var_mes:.2f}%" if var_mes is not None else "-",
            'Variacion vs 1 Año': f"{var_año:.2f}%" if var_año is not None else "-",
            'Variacion_Dia_Val': var_dia 
        })
        
    return pd.DataFrame(resultados_lista).sort_values(by=['Categoria', 'Subcategoria', 'Producto']).reset_index(drop=True)

def generar_reporte_y_graficos(df):
    """Genera el Excel y los gráficos por categoría."""
    if df.shape[0] < 1: return [], None, None
    df = df.sort_values(by=['Fecha', 'Categoria', 'Subcategoria', 'Producto']).reset_index(drop=True)
    productos = df['Producto'].unique()
    categorias = df['Categoria'].unique()
    
    df_list = []
    tiene_variacion = False
    for producto in productos:
        df_prod = df[df['Producto'] == producto].copy()
        if df_prod.shape[0] >= 2:
            df_prod['Variacion_ARS'] = df_prod['Precio_ARS'].pct_change() * 100
            df_prod['Variacion_USD'] = df_prod['Precio_USD'].pct_change() * 100
            tiene_variacion = True
        else:
            df_prod['Variacion_ARS'] = df_prod['Variacion_USD'] = None
        df_list.append(df_prod)
        
    df_con_variacion = pd.concat(df_list, ignore_index=True)
    writer = pd.ExcelWriter(REPORT_XLSX, engine='xlsxwriter')
    
    # Hojas de Excel
    df_maestro = df_con_variacion[['Fecha', 'Categoria', 'Subcategoria', 'Producto', 'Descripcion_Corta', 'Precio_ARS', 'Precio_USD', 'Dolar_ARS']].copy()
    df_maestro['Fecha'] = df_maestro['Fecha'].dt.strftime('%Y-%m-%d')
    df_maestro.to_excel(writer, sheet_name='1. Maestro ARS USD', index=False)
    
    df_pivot_ars = df_con_variacion.pivot_table(index='Producto', columns='Fecha', values='Precio_ARS')
    df_pivot_ars.columns = df_pivot_ars.columns.strftime('%Y-%m-%d')
    df_pivot_ars.to_excel(writer, sheet_name='2. Precios ARS')

    df_pivot_usd = df_con_variacion.pivot_table(index='Producto', columns='Fecha', values='Precio_USD')
    df_pivot_usd.columns = df_pivot_usd.columns.strftime('%Y-%m-%d')
    df_pivot_usd.to_excel(writer, sheet_name='3. Precios USD')

    df_variacion_historica = calcular_variacion_historica(df)
    df_variacion_historica.drop(columns=['Variacion_Dia_Val']).to_excel(writer, sheet_name='6. Variacion vs Histórico', index=False)
    writer.close()
    
    # Gráficos
    sns.set_theme(style="whitegrid")
    imagenes_generadas = []
    for i, categoria in enumerate(categorias):
        df_cat = df_con_variacion[df_con_variacion['Categoria'] == categoria].copy()
        nombre_limpio = categoria.replace(' ', '_').lower()
        
        plt.figure(figsize=(12, 7))
        sns.lineplot(x='Fecha', y='Precio_ARS', data=df_cat, hue='Producto', marker='o') 
        plt.title(f'Precios: {categoria} (ARS)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        chart_path = os.path.join(CHART_DIR, f"{i+1}_{nombre_limpio}_ars.png")
        plt.savefig(chart_path)
        plt.close()
        imagenes_generadas.append({'file': chart_path, 'name': f"Precios: {categoria} (ARS)"})

    return imagenes_generadas, df_variacion_historica, df_variacion_historica.dropna(subset=['Variacion_Dia_Val'])

def df_to_html_table(df, title="Tabla"):
    if df is None or df.empty: return "<p>Sin datos.</p>"
    styles = "<style>.dataframe{width:100%;border-collapse:collapse;} .dataframe td, .dataframe th{border:1px solid #ddd;padding:8px;}</style>"
    return styles + df.to_html(index=False, classes='dataframe')

def enviar_email(df, imagenes_generadas, df_var_hist, df_top):
    msg = MIMEMultipart('related')
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_RECIPIENT
    msg['Subject'] = f"Reporte Rock & Feller's ({datetime.now().strftime('%Y-%m-%d')})"

    # Resumen simplificado
    resumen_html = "<h3>Resumen de Hoy</h3><ul>"
    hoy = datetime.now().date()
    df_hoy = df[df['Fecha'].dt.date == hoy]
    for _, row in df_hoy.head(10).iterrows(): # Muestra los primeros 10
        resumen_html += f"<li>{row['Producto']}: ${row['Precio_ARS']:,.2f}</li>"
    resumen_html += "</ul>"

    html_charts = "".join([f'<p>{img["name"]}</p><img src="cid:chart_{i+1}" width="600">' for i, img in enumerate(imagenes_generadas)])
    
    body = f"<html><body>{resumen_html}<h3>Historial</h3>{df_to_html_table(df_var_hist.drop(columns=['Variacion_Dia_Val']).head(20))}{html_charts}</body></html>"
    msg.attach(MIMEText(body, 'html'))

    # Adjunto y Gráficos
    if os.path.exists(REPORT_XLSX):
        with open(REPORT_XLSX, "rb") as f:
            part = MIMEApplication(f.read(), Name=REPORT_XLSX)
            part['Content-Disposition'] = f'attachment; filename="{REPORT_XLSX}"'
            msg.attach(part)

    for i, item in enumerate(imagenes_generadas):
        with open(item['file'], 'rb') as fp:
            img = MIMEImage(fp.read())
            img.add_header('Content-ID', f'<chart_{i+1}>')
            msg.attach(img)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, EMAIL_RECIPIENT, msg.as_string())
    print("📧 Email enviado.")

# ==============================================================================
# --- Flujo Principal ---
# ==============================================================================

def main():
    print("--- INICIO R&F ---")
    dolar_ars = obtener_precio_dolar_api(API_DOLAR_URL)
    if dolar_ars == 1.0: return

    df_maestro = cargar_o_crear_maestro()
    productos = rastrear_menu(URL_MENU_PRINCIPAL)

    df_actualizado = df_maestro.copy()
    for p in productos:
        df_actualizado = guardar_datos(df_actualizado, p['nombre'], p['precio_ars'], p['categoria'], p['subcategoria'], p['descripcion_corta'], dolar_ars)

    if not df_actualizado.empty:
        imgs, df_vh, df_top = generar_reporte_y_graficos(df_actualizado)
        enviar_email(df_actualizado, imgs, df_vh, df_top)
    print("--- FIN ---")

if __name__ == "__main__":
    main()