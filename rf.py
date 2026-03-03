"""
rf.py - RFBOT Multi-Local Multi-Carta
Rock & Fellers: Orono, Alto Rosario, Savoy
Cartas: Restaurante, Cafeteria, Vinos y Espumantes, Cocktails
"""
import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
from datetime import datetime
import os

LOCALES = {
    "Orono": {"slug": "rock-feller-s-boulevard-orono", "nombre": "Boulevard Orono"},
    "Alto Rosario": {"slug": "rock-feller-s-alto-rosario", "nombre": "Alto Rosario"},
    "Savoy": {"slug": "rock-feller-s-savoy", "nombre": "Savoy"}
}

CARTAS = ["restaurante", "cafeteria", "vinos-y-espumantes", "cocktails"]
CARTA_LABELS = {
    "restaurante": "Restaurante",
    "cafeteria": "Cafeteria",
    "vinos-y-espumantes": "Vinos y Espumantes",
    "cocktails": "Cocktails"
}

BASE_URL = "https://rockandfellers.com.ar/cartas-qr"
API_DOLAR_URL = "https://api.comparadolar.ar/usd"
MASTER_CSV = "rf_precios.csv"

def obtener_dolar():
    try:
        r = requests.get(API_DOLAR_URL, timeout=10)
        data = r.json()
        bn = next((x for x in data if x.get('slug') == 'banco-nacion'), None)
        return float(bn['ask']) if bn else 1.0
    except:
        return 1.0

def extraer_menu(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(r.content, 'html.parser')
        div = soup.find('div', attrs={'wire:initial-data': True})
        if not div:
            return []
        data = json.loads(div['wire:initial-data'])
        menus_raw = data.get('serverMemo', {}).get('data', {}).get('menus', {})
        menus_list = list(menus_raw.values()) if isinstance(menus_raw, dict) else (menus_raw if isinstance(menus_raw, list) else [])
        productos = []
        for rubro in menus_list:
            if not isinstance(rubro, dict): continue
            rubro_name = rubro.get('name', '').strip(' -')
            for sub in rubro.get('subrubros', []):
                if not isinstance(sub, dict): continue
                sub_name = sub.get('name', '').strip()
                prods_raw = sub.get('products', {})
                prods = list(prods_raw.values()) if isinstance(prods_raw, dict) else (prods_raw if isinstance(prods_raw, list) else [])
                for p in prods:
                    if not isinstance(p, dict): continue
                    nombre = p.get('name', '').strip()
                    desc = (p.get('short_description', '') or '')[:80]
                    precio = None
                    details = p.get('product_details', [])
                    if details and isinstance(details, list):
                        try: precio = float(details[0].get('default_price', 0) or 0)
                        except: pass
                    if nombre and precio and precio > 0:
                        productos.append({'nombre': nombre, 'descripcion': desc, 'rubro': rubro_name, 'subrubro': sub_name, 'precio_ars': precio})
        return productos
    except Exception as e:
        print(f"  Error {url}: {e}")
        return []

def main():
    print("Rock & Feller's RFBOT iniciando...")
    dolar = obtener_dolar()
    print(f"Dolar BN: ${dolar:,.2f}")
    hoy = datetime.now().strftime("%Y-%m-%d")
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nuevos = []
    for local_key, local_info in LOCALES.items():
        slug = local_info['slug']
        print(f"Local: {local_info['nombre']}")
        for carta in CARTAS:
            url = f"{BASE_URL}/{slug}/{carta}"
            productos = extraer_menu(url)
            print(f"  {CARTA_LABELS[carta]}: {len(productos)} productos")
            for p in productos:
                nuevos.append({
                    'Fecha': hoy, 'Fecha_Hora': fecha_hora,
                    'Local': local_key, 'Local_Nombre': local_info['nombre'],
                    'Carta': carta, 'Carta_Label': CARTA_LABELS[carta],
                    'Rubro': p['rubro'], 'Subrubro': p['subrubro'],
                    'Producto': p['nombre'], 'Descripcion': p['descripcion'],
                    'Precio_ARS': p['precio_ars'],
                    'Precio_USD': round(p['precio_ars'] / dolar, 2),
                    'Dolar_ARS': dolar
                })
    if not nuevos:
        print("Sin datos.")
        return
    df_nuevo = pd.DataFrame(nuevos)
    if os.path.exists(MASTER_CSV):
        df_hist = pd.read_csv(MASTER_CSV)
        df_hist['Fecha'] = pd.to_datetime(df_hist['Fecha']).dt.strftime('%Y-%m-%d')
        df_hist = df_hist[df_hist['Fecha'] != hoy]
        df_final = pd.concat([df_hist, df_nuevo], ignore_index=True)
    else:
        df_final = df_nuevo
    df_final.to_csv(MASTER_CSV, index=False)
    print(f"OK: {len(df_nuevo)} registros guardados para {hoy}")

if __name__ == "__main__":
    main()
