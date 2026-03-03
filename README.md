# 🎸 RFBOT - Rock & Feller's Price Tracker

Tracker automático de precios de **Rock & Feller's** para los 3 locales de Rosario.

## Locales cubiertos
| Local | URL |
|-------|-----|
| Boulevard Orono | rock-feller-s-boulevard-orono |
| Alto Rosario | rock-feller-s-alto-rosario |
| Savoy | rock-feller-s-savoy |

## Cartas relevadas
- 🍽️ **Restaurante** — Entradas, Ensaladas, Pastas, Carnes, Sándwiches, Postres, etc.
- ☕ **Cafetería** — Desayunos, Meriendas, Tortas
- 🍷 **Vinos y Espumantes** — Champagnes, Bodegas, Vinos por copa
- 🍸 **Cocktails** — Clásicos, Martini Bar, Aperitivos, Cervezas

## Funcionalidades del sitio
- Vista global con comparativo entre locales
- Pestaña por local con sub-tabs por carta
- Gráfico de evolución de precios por local y por carta
- Tabla comparativa de precios entre locales (productos comunes)
- Rankings de subidas/bajadas filtrable por período

## Estructura
```
RFBOT/
├── rf.py                   # Scraper multi-local
├── analizar_precios.py     # Genera JSONs de análisis
├── generar_web.py          # Genera HTML para GitHub Pages
├── data/                   # JSONs generados
├── docs/                   # Web GitHub Pages
└── .github/workflows/      # GitHub Actions
```

## Setup
1. Fork → Settings → Pages → Source: `docs/`
2. El workflow corre automáticamente cada día a las 12:00 ART
