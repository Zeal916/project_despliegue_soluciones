"""Genera una muestra pequeña de los datos crudos para adjuntar a la entrega (los CSV completos van por DVC).

Uso: python src/make_sample.py [--n 20000]
Muestra aleatoria reproducible (seed=42) de contratos 2017-2025 y sus adiciones en valor.
"""
import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data/raw", ROOT / "data/sample"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20_000)
    n = ap.parse_args().n
    OUT.mkdir(parents=True, exist_ok=True)
    c = pd.read_csv(RAW / "contratos_salud.csv", low_memory=False)
    c = c[pd.to_datetime(c.fecha_de_firma, errors="coerce").dt.year.between(2017, 2025)]
    m = c.sample(n=n, random_state=42)
    a = pd.read_csv(RAW / "adiciones_valor.csv")
    a = a[a.id_contrato.isin(m.id_contrato)]
    m.to_csv(OUT / "contratos_salud_muestra.csv", index=False)
    a.to_csv(OUT / "adiciones_valor_muestra.csv", index=False)
    print(f"contratos: {len(m):,} | adiciones asociadas: {len(a):,}")
