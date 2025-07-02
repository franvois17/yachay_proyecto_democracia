#Este codigo genera un reporte de los archivos encontrados en cada año
#!/usr/bin/env python3
# enemdu_matriz_local_unzip.py  –  FINAL (prefijo, PERSONAS2… y sufijos 0-1-2 fusionados)
# ======================================================================
#  • Descomprime TODOS los .zip (profundidad ilimitada) y borra cada zip.
#  • Ignora archivos ocultos (.DS_Store, ._*).
#  • Solo crea columnas para extensiones útiles (csv, sav, xls/xlsx, pdf, sps).
#  • Normaliza nombres para evitar duplicados:
#       a) Quita prefijo  YYYYMM_  |  YYYY_MM_
#       b) Quita bloque interior  _YYYY_MM  |  -YYYY-MM
#       c) Fusiona PERSONAS2 → PERSONAS,  VIV_HOG2 → VIV_HOG,  HOGAR2 → HOGAR
#       d) Elimina dígitos finales antes de la extensión (…consumidor0.csv → consumidor.csv)
#       e) Colapsa múltiples “_” y limpia bordes.
#  • Ordena columnas por número de “X” (más frecuentes primero).
#  • Genera un Excel por año en  ~/Desktop/excels enemdu/
# ======================================================================

import re, sys, queue
from pathlib import Path
import pandas as pd
from zipfile import ZipFile, is_zipfile, BadZipFile

# ─── RUTAS ───────────────────────────────────────────────────
BASE = Path.home() / "Desktop/ENEMDU-DESCARGAS"
OUT  = Path.home() / "Desktop/excels enemdu"
OUT.mkdir(parents=True, exist_ok=True)
if not BASE.is_dir():
    sys.exit(f"❌ No se encontró la carpeta {BASE}")

# ─── EXTENSIONES CONTADAS COMO COLUMNAS ─────────────────────
ALLOWED_EXT = {".csv", ".sav", ".xls", ".xlsx", ".pdf", ".sps"}

# ─── 1. CANONICALIZADOR ─────────────────────────────────────
pat_prefix   = re.compile(r"^\d{4}[_]?(0[1-9]|1[0-2])[_\-]", re.I)     # YYYYMM_
pat_ym       = re.compile(r"([_\-])\d{4}[_\-](0?[1-9]|1[0-2])", re.I)  # _YYYY_MM
pat_personas = re.compile(r"(?i)PERSONAS2(?=[_.])")
pat_vivhog   = re.compile(r"(?i)VIV_HOG2(?=[_.])")
pat_hogar    = re.compile(r"(?i)HOGAR2(?=[_.])")
pat_trailnum = re.compile(r"(?<=\D)\d+(?=\.[^.]+$)")                   # …0.csv → …
pat_dupes    = re.compile(r"_+")

def canonical(name: str) -> str:
    name = pat_prefix.sub("", name)            # a) quita prefijo fecha
    name = pat_ym.sub("", name)                # b) quita bloque interior fecha
    name = pat_personas.sub("PERSONAS", name)  # c) fusiona variantes “2”
    name = pat_vivhog.sub("VIV_HOG",   name)
    name = pat_hogar.sub("HOGAR",      name)
    name = pat_trailnum.sub("", name)          # d) borra dígitos finales antes de extensión
    name = pat_dupes.sub("_", name)            # e) colapsa ___ → _
    return name.strip("_-")

# ─── 2. DESCOMPRESIÓN ILIMITADA DE ZIPs ─────────────────────
def unzip_recursive(root: Path):
    """Extrae todos los zips dentro de root.
       • Si un zip es válido → lo extrae y luego lo borra.
       • Si está dañado (cabecera o datos) → muestra aviso y lo borra."""
    q = queue.SimpleQueue()
    for z in root.rglob("*.zip"):
        q.put(z)

    while not q.empty():
        zpath: Path = q.get()
        if not zpath.exists() or not is_zipfile(zpath):
            continue

        try:
            with ZipFile(zpath) as zf:
                try:
                    zf.extractall(zpath.parent)
                except Exception:                      # datos corruptos
                    print(f"   ⚠️  Zip dañado (datos) → {zpath.relative_to(BASE)} — eliminado")
                    zpath.unlink(missing_ok=True)
                    continue

                # encola zips anidados
                for m in zf.namelist():
                    if m.lower().endswith(".zip"):
                        inner = zpath.parent / m
                        if inner.exists():
                            q.put(inner)

            zpath.unlink(missing_ok=True)              # borrado tras extraer OK

        except BadZipFile:                             # cabecera inválida
            print(f"   ⚠️  Zip dañado (cabecera) → {zpath.relative_to(BASE)} — eliminado")
            zpath.unlink(missing_ok=True)
# ─── 3. LISTAR DOCUMENTOS ÚTILES ────────────────────────────
def list_docs(period_path: Path):
    return [
        canonical(f.name)
        for f in period_path.rglob("*")
        if f.is_file()
           and not f.name.startswith(".")
           and f.suffix.lower() in ALLOWED_EXT
    ]

# ─── 4. GENERAR MATRICES POR AÑO ────────────────────────────
for year_dir in sorted(d for d in BASE.iterdir() if d.is_dir()):
    year = year_dir.name
    print(f"📑 Año {year}")

    registros, universe = [], set()

    for per_dir in sorted(d for d in year_dir.iterdir() if d.is_dir()):
        periodo = per_dir.name
        unzip_recursive(per_dir)           # descomprime TODO

        docs = list_docs(per_dir)
        universe.update(docs)
        registros.append({"Period": periodo, **{d: "X" for d in docs}})

    if not registros:
        continue

    # DataFrame y orden de columnas por frecuencia de “X”
    df = pd.DataFrame(registros)
    hit_counts = (df == "X").sum().drop("Period")
    ordered = hit_counts.sort_values(ascending=False).index.tolist()
    df = df.reindex(columns=["Period", *ordered]).fillna("")

    out_file = OUT / f"ENEMDU_{year}_matriz.xlsx"
    df.to_excel(out_file, index=False)
    print(f"   ✔ Guardado: {out_file}")

print("\n✅ Matrices finales en:")
print(f"   {OUT}")
