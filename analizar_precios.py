"""analizar_precios.py - RFBOT - Rock & Feller's"""
import pandas as pd, json
from pathlib import Path
from datetime import timedelta

DIR_DATA = Path("data")
DIR_DATA.mkdir(exist_ok=True)

def load():
    try:
        df = pd.read_csv("rockandfellers_precios.csv")
        df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.normalize()
        return df.dropna(subset=["Precio_ARS","Fecha"])
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()

def var(df, dias):
    hoy = df["Fecha"].max()
    h = df[df["Fecha"]==hoy]
    r = df[df["Fecha"]<=hoy-timedelta(days=dias)].sort_values("Fecha").groupby("Producto").last().reset_index()
    m = h.merge(r[["Producto","Precio_ARS"]], on="Producto", suffixes=("_h","_r"))
    if m.empty: return None
    return ((m["Precio_ARS_h"]-m["Precio_ARS_r"])/m["Precio_ARS_r"]*100).mean()

def graficos(df):
    hoy = df["Fecha"].max()
    cats = df["Categoria"].dropna().unique().tolist() if "Categoria" in df.columns else []
    res = {}
    for key,dias in {"7d":7,"30d":30,"6m":180}.items():
        dp = df[df["Fecha"]>=hoy-timedelta(days=dias)]
        st = dp.groupby("Fecha")["Precio_ARS"].mean().reset_index()
        if st.empty: res[key]={"total":[],"categorias":{}}; continue
        b=st["Precio_ARS"].iloc[0]
        total=[{"fecha":r["Fecha"].strftime("%Y-%m-%d"),"pct":round((r["Precio_ARS"]/b-1)*100,2)} for _,r in st.iterrows()]
        cats_s={}
        for c in cats:
            s=dp[dp["Categoria"]==c].groupby("Fecha")["Precio_ARS"].mean().reset_index()
            if len(s)<2: continue
            b2=s["Precio_ARS"].iloc[0]
            cats_s[c]=[{"fecha":r["Fecha"].strftime("%Y-%m-%d"),"pct":round((r["Precio_ARS"]/b2-1)*100,2)} for _,r in s.iterrows()]
        res[key]={"total":total,"categorias":cats_s}
    return res

def ranking(df, dias):
    hoy = df["Fecha"].max()
    h = df[df["Fecha"]==hoy]
    r = df[df["Fecha"]<=hoy-timedelta(days=dias)].sort_values("Fecha").groupby("Producto").last().reset_index()
    m = h.merge(r[["Producto","Precio_ARS"]], on="Producto", suffixes=("_h","_r"))
    if m.empty: return []
    m["d"]=(m["Precio_ARS_h"]-m["Precio_ARS_r"])/m["Precio_ARS_r"]*100
    m=m[m["d"].abs()>0]
    cat_map = h.set_index("Producto")["Categoria"].to_dict() if "Categoria" in h.columns else {}
    sub_map = h.set_index("Producto")["Subcategoria"].to_dict() if "Subcategoria" in h.columns else {}
    return m.sort_values("d",ascending=False).apply(lambda row:{
        "nombre":row["Producto"],"categoria":cat_map.get(row["Producto"],""),
        "subcategoria":sub_map.get(row["Producto"],""),
        "diff_pct":round(row["d"],2),"precio_hoy":round(row["Precio_ARS_h"],2)
    },axis=1).tolist()

def main():
    df = load()
    if df.empty: return
    hoy = df["Fecha"].max()
    dh = df[df["Fecha"]==hoy]
    v1=var(df,1); v30=var(df,30)
    dr=df[df["Fecha"]==hoy-timedelta(days=1)]
    sube=baja=igual=0; cats_dia=[]
    if not dr.empty:
        m=dh.merge(dr[["Producto","Precio_ARS"]], on="Producto", suffixes=("_h","_r"))
        m["d"]=(m["Precio_ARS_h"]-m["Precio_ARS_r"])/m["Precio_ARS_r"]*100
        sube=int((m["d"]>0.01).sum()); baja=int((m["d"]<-0.01).sum()); igual=int((m["d"].abs()<=0.01).sum())
        if "Categoria" in m.columns:
            for c, g in m.groupby("Categoria"):
                cats_dia.append({"categoria":c,"variacion_pct_promedio":round(g["d"].mean(),2),
                    "productos_subieron":int((g["d"]>0.01).sum()),"productos_bajaron":int((g["d"]<-0.01).sum()),"total_productos":len(g)})
    res={"variacion_dia":round(v1,2) if v1 is not None else None,"variacion_mes":round(v30,2) if v30 is not None else None,
        "total_productos":len(dh),"productos_subieron_dia":sube,"productos_bajaron_dia":baja,"productos_sin_cambio_dia":igual,"categorias_dia":cats_dia}
    (DIR_DATA/"resumen.json").write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding="utf-8")
    (DIR_DATA/"graficos.json").write_text(json.dumps(graficos(df),ensure_ascii=False,indent=2),encoding="utf-8")
    (DIR_DATA/"ranking_dia.json").write_text(json.dumps(ranking(df,1),ensure_ascii=False,indent=2),encoding="utf-8")
    (DIR_DATA/"ranking_7d.json").write_text(json.dumps(ranking(df,7),ensure_ascii=False,indent=2),encoding="utf-8")
    (DIR_DATA/"ranking_mes.json").write_text(json.dumps(ranking(df,30),ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"JSONs RFBOT ok. Hoy: {len(dh)} items")

if __name__=="__main__": main()
