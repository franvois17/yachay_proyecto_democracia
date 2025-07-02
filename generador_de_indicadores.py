# Este Archivo genera todos los indicadores mostrados por enemdu
# ============================================================
# ENEMDU 2007-2025 · Indicadores laborales por período
#   • TPG, Desempleo, Adecuado, Subempleo,
#     No remunerado, Otro no pleno, Empleo total
# Jenner Baquero
# ============================================================
import re
from pathlib import Path
import pandas as pd

# ----------------------------------------------------------------------
# 1) Carpeta raíz con TODOS tus .csv  (⇩ ajústalo a tu ruta)
ROOT = Path("/Users/fran/Desktop/ENEMDU-DESCARGAS")
assert ROOT.exists(), f"Directorio no encontrado: {ROOT}"

# ----------------------------------------------------------------------
# 2) Diccionarios y utilidades
MONTH_MAP = {
    "01": "Enero", "02": "Febrero",  "03": "Marzo",     "04": "Abril",
    "05": "Mayo",  "06": "Junio",    "07": "Julio",     "08": "Agosto",
    "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre",
}

# Posibles nombres de columnas según año/ronda
AGE_CANDS    = ["p03", "edad"]
STATUS_CANDS = ["condact", "condact3"]
WEIGHT_CANDS = ["fexp", "facexp", "factor_expansion", "peso", "peso_2020", "fexp_r"]

def choose(candidates, df):
    """Devuelve la primera columna que exista (insensible a mayús./minús.)."""
    cols = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in cols:
            return cols[c]
    raise KeyError(f"No se encontró ninguna de: {candidates}")

def clean_weights(series):
    """Convierte pesos con coma decimal a float puro."""
    return (
        series.astype(str)
              .str.replace(",", ".", regex=False)
              .str.extract(r"([\d\.]+)")[0]
              .astype(float)
    )

def compute_indicators(df):
    """Devuelve un dict con TPG y los seis indicadores solicitados."""
    df.columns = df.columns.str.strip().str.lower()
    age   = choose(AGE_CANDS,    df)
    stat  = choose(STATUS_CANDS, df)
    wcol  = choose(WEIGHT_CANDS, df)

    # coerción numérica segura
    df[age]  = pd.to_numeric(df[age],  errors="coerce")
    df[stat] = pd.to_numeric(df[stat], errors="coerce")
    df[wcol] = clean_weights(df[wcol])

    pet = df.loc[(df[age] >= 15) & (df[wcol] > 0)]           # población en edad de trabajar
    pea = pet.loc[pet[stat].between(1, 8)]                   # económicamente activa
    W   = pea[wcol]                                          # atajo
    s   = pea[stat]

    total_pet = pet[wcol].sum()
    total_pea = W.sum()

    return {
        "TPG (%)":           100 * total_pea / total_pet,
        "TD (%)":            100 * W[s.isin([7, 8])].sum()           / total_pea,
        "Adecuado (%)":      100 * W[s == 1].sum()                   / total_pea,
        "Subempleo (%)":     100 * W[s.isin([2, 3])].sum()           / total_pea,
        "No Remun. (%)":     100 * W[s == 5].sum()                   / total_pea,
        "Otro No Pleno (%)": 100 * W[s == 4].sum()                   / total_pea,
        "Empleo Total (%)":  100 * W[s.isin([1, 2, 3, 4, 5, 6])].sum() / total_pea,
    }

# ----------------------------------------------------------------------
# 3) Recorrido de todos los .csv
pattern  = re.compile(r"enemdu_?p(?:ersona|ersonas)?_?(\d{4})_?(\d{2})", re.I)
records  = []

for csv_path in ROOT.rglob("*.csv"):
    m = pattern.search(csv_path.name)
    if not m:
        continue                                   # no coincide con patrón PERSONAS

    year, period = m.groups()

    try:
        df  = pd.read_csv(csv_path, sep=";", encoding="latin1", low_memory=False)
        ind = compute_indicators(df)
    except Exception as e:
        print(f"⚠️  {csv_path.name}: {e}")
        continue

    records.append({
        "Año": int(year),
        "Periodo": int(period),
        "Mes": MONTH_MAP.get(period.zfill(2), "Desconocido"),
        "Archivo": csv_path.relative_to(ROOT).as_posix(),
        **{k: round(v, 2) for k, v in ind.items()},
    })

# ----------------------------------------------------------------------
# 4) Tabla final y exportación
tabla = (
    pd.DataFrame(records)
      .sort_values(["Año", "Periodo"])
      .reset_index(drop=True)
)

print("\n=== Indicadores laborales ENEMDU (2007-2025) ===\n")
print(tabla.to_string(index=False))

csv_out = ROOT / "indicadores_laborales_por_periodo.csv"
tabla.to_csv(csv_out, index=False, encoding="utf-8-sig")
print(f"\nArchivo guardado en: {csv_out}")
