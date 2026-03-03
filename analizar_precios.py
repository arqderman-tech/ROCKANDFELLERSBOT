"""analizar_precios.py - RFBOT Multi-Local"""
import pandas as pd, json
from pathlib import Path
from datetime import timedelta

DIR_DATA = Path("data")
DIR_DATA.mkdir(exist_ok=True)

LOCALES = ["Orono", "Alto Rosario", "Savoy"]
CARTAS = {"restaurante":"Restaurante","cafeteria":"Cafeteria","vinos-y-espumantes":"Vinos y Espumantes","cocktails":"Cocktails"}
CARTA_COLORS = {"Restaurante":"#ef4444","Cafeteria":"#f59e0b","Vinos y Espumantes":"#8b5cf6","Cocktails":"#0ea5e9"}

def load():
    try:
        df = pd.read_csv("rf_precios.csv")
        df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.normalize()
        return df.dropna(subset=["Precio_ARS","Fecha"])
    except Exception as e:
        print(f"Error: {e}"); return pd.DataFrame()

def var_pct(df, dias, local=None, carta=None):
    d = df.copy()
    if local: d = d[d["Local"]==local]
    if carta: d = d[d["Carta"]==carta]
    if d.empty: return None
    hoy = d["Fecha"].max()
    ref = hoy - timedelta(days=dias)
    h = d[d["Fecha"]==hoy]; r = d[d["Fecha"]<=ref].sort_values("Fecha").groupby("Producto").last().reset_index()
    m = h.merge(r[["Producto","Precio_ARS"]], on="Producto", suffixes=("_h","_r"))
    if m.empty: return None
    return round(((m["Precio_ARS_h"]-m["Precio_ARS_r"])/m["Precio_ARS_r"]*100).mean(), 2)

def serie_pct(df, dias, local=None, carta=None):
    d = df.copy()
    if local: d = d[d["Local"]==local]
    if carta: d = d[d["Carta"]==carta]
    if d.empty: return []
    hoy = d["Fecha"].max()
    desde = hoy - timedelta(days=dias)
    dp = d[d["Fecha"]>=desde]
    st = dp.groupby("Fecha")["Precio_ARS"].mean().reset_index()
    if st.empty or len(st)<2: return []
    b = st["Precio_ARS"].iloc[0]
    return [{"fecha":r["Fecha"].strftime("%Y-%m-%d"),"pct":round((r["Precio_ARS"]/b-1)*100,2)} for _,r in st.iterrows()]

def ranking(df, dias, local=None):
    d = df.copy()
    if local: d = d[d["Local"]==local]
    hoy = d["Fecha"].max()
    h = d[d["Fecha"]==hoy]
    r = d[d["Fecha"]<=hoy-timedelta(days=dias)].sort_values("Fecha").groupby(["Producto","Local"]).last().reset_index()
    m = h.merge(r[["Producto","Local","Precio_ARS"]], on=["Producto","Local"], suffixes=("_h","_r"))
    if m.empty: return []
    m["d"]=(m["Precio_ARS_h"]-m["Precio_ARS_r"])/m["Precio_ARS_r"]*100
    m=m[m["d"].abs()>0]
    cat_map = h.set_index("Producto")["Carta_Label"].to_dict() if "Carta_Label" in h.columns else {}
    rub_map = h.set_index("Producto")["Rubro"].to_dict() if "Rubro" in h.columns else {}
    return m.sort_values("d",ascending=False).apply(lambda row:{
        "nombre":row["Producto"],"local":row["Local"],
        "carta":cat_map.get(row["Producto"],""),"rubro":rub_map.get(row["Producto"],""),
        "diff_pct":round(row["d"],2),"precio_hoy":round(row["Precio_ARS_h"],2)
    },axis=1).tolist()

def main():
    df = load()
    if df.empty: print("Sin datos"); return
    hoy = df["Fecha"].max()
    df_hoy = df[df["Fecha"]==hoy]

    # Resumen global
    v1=var_pct(df,1); v30=var_pct(df,30)

    # Stats por local
    locales_stats = {}
    for local in LOCALES:
        dh_l = df_hoy[df_hoy["Local"]==local]
        v1_l = var_pct(df,1,local=local)
        cartas_stats = {}
        for carta_key, carta_label in CARTAS.items():
            dh_c = dh_l[dh_l["Carta"]==carta_key]
            v1_c = var_pct(df,1,local=local,carta=carta_key)
            # Rubros del dia
            rubros = []
            if not dh_c.empty:
                dr = df[(df["Fecha"]==hoy-timedelta(days=1)) & (df["Local"]==local) & (df["Carta"]==carta_key)]
                if not dr.empty:
                    m = dh_c.merge(dr[["Producto","Precio_ARS"]],on="Producto",suffixes=("_h","_r"))
                    m["d"]=(m["Precio_ARS_h"]-m["Precio_ARS_r"])/m["Precio_ARS_r"]*100
                    for rub, g in m.groupby("Rubro"):
                        rubros.append({"rubro":rub,"variacion":round(g["d"].mean(),2),
                            "subieron":int((g["d"]>0.01).sum()),"bajaron":int((g["d"]<-0.01).sum()),"total":len(g)})
            cartas_stats[carta_key] = {
                "label": carta_label,
                "total_productos": len(dh_c),
                "variacion_dia": v1_c,
                "rubros": rubros
            }
        locales_stats[local] = {
            "total_productos": len(dh_l),
            "variacion_dia": v1_l,
            "cartas": cartas_stats
        }

    # Graficos globales y por local/carta
    periodos = {"7d":7,"30d":30,"6m":180}
    graficos = {}
    for key,dias in periodos.items():
        graficos[key] = {
            "total": serie_pct(df,dias),
            "por_local": {loc: serie_pct(df,dias,local=loc) for loc in LOCALES},
            "por_carta": {cl: serie_pct(df,dias,carta=ck) for ck,cl in CARTAS.items()}
        }

    # Rankings
    rank_global_dia = ranking(df,1)
    rank_global_7d = ranking(df,7)
    rank_global_mes = ranking(df,30)
    rank_por_local = {loc: ranking(df,1,local=loc) for loc in LOCALES}

    # Comparativo de precios entre locales (productos comunes)
    comparativo = []
    if not df_hoy.empty:
        prod_multi = df_hoy.groupby("Producto")["Local"].nunique()
        prods_comunes = prod_multi[prod_multi>1].index.tolist()
        for prod in prods_comunes[:50]:
            fila = {"producto": prod}
            for loc in LOCALES:
                row = df_hoy[(df_hoy["Producto"]==prod) & (df_hoy["Local"]==loc)]
                fila[loc] = float(row["Precio_ARS"].iloc[0]) if not row.empty else None
            fila["carta"] = df_hoy[df_hoy["Producto"]==prod]["Carta_Label"].iloc[0] if not df_hoy[df_hoy["Producto"]==prod].empty else ""
            fila["rubro"] = df_hoy[df_hoy["Producto"]==prod]["Rubro"].iloc[0] if not df_hoy[df_hoy["Producto"]==prod].empty else ""
            comparativo.append(fila)

    resumen = {
        "variacion_dia": v1, "variacion_mes": v30,
        "total_productos": len(df_hoy),
        "locales": locales_stats,
        "carta_colors": CARTA_COLORS,
        "fecha_actualizacion": hoy.strftime("%Y-%m-%d") if hasattr(hoy,"strftime") else str(hoy)
    }

    (DIR_DATA/"resumen.json").write_text(json.dumps(resumen,ensure_ascii=False,indent=2),encoding="utf-8")
    (DIR_DATA/"graficos.json").write_text(json.dumps(graficos,ensure_ascii=False,indent=2),encoding="utf-8")
    (DIR_DATA/"ranking_dia.json").write_text(json.dumps(rank_global_dia[:30],ensure_ascii=False,indent=2),encoding="utf-8")
    (DIR_DATA/"ranking_7d.json").write_text(json.dumps(rank_global_7d[:30],ensure_ascii=False,indent=2),encoding="utf-8")
    (DIR_DATA/"ranking_mes.json").write_text(json.dumps(rank_global_mes[:30],ensure_ascii=False,indent=2),encoding="utf-8")
    (DIR_DATA/"ranking_por_local.json").write_text(json.dumps(rank_por_local,ensure_ascii=False,indent=2),encoding="utf-8")
    (DIR_DATA/"comparativo_locales.json").write_text(json.dumps(comparativo,ensure_ascii=False,indent=2),encoding="utf-8")

    print(f"JSONs RFBOT ok. Hoy: {len(df_hoy)} registros totales")
    for loc in LOCALES:
        n = len(df_hoy[df_hoy["Local"]==loc])
        print(f"  {loc}: {n} items")

if __name__=="__main__": main()
