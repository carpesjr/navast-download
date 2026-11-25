#!/usr/bin/env python3
"""Gera ut1.json (UT1-UTC diario) a partir do arquivo finals2000A.daily do IERS.

Formato do IERS (colunas fixas, base 1): MJD = 8-15; UT1-UTC (s) = 59-68.
Saida: {"geradoEm","fonte","dados":[{"data":"AAAA-MM-DD","ut1MenosUtc":s}, ...]}
Seguranca: se o download falhar ou vier fora do esperado, NAO sobrescreve o ut1.json existente.
"""
import json, sys, urllib.request
from datetime import date, datetime, timedelta, timezone

FONTES = [
    "https://datacenter.iers.org/data/9/finals2000A.daily",
    "https://maia.usno.navy.mil/ser7/finals2000A.daily",
]
DIAS_PASSADO = 30
SAIDA = "ut1.json"


def baixar():
    for url in FONTES:
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                texto = r.read().decode("ascii", "replace")
            if len(texto) > 10000:
                return url, texto
        except Exception as e:  # tenta a proxima fonte
            print(f"Falha em {url}: {e}", file=sys.stderr)
    return None, None


def interpretar(texto):
    base = date(1858, 11, 17)  # MJD 0
    por_dia = {}
    for linha in texto.splitlines():
        if len(linha) < 68:
            continue
        try:
            mjd = int(float(linha[7:15]))
            v = float(linha[58:68])
        except ValueError:
            continue
        por_dia[base + timedelta(days=mjd)] = v
    return por_dia


def main():
    url, texto = baixar()
    if not texto:
        print("Nenhuma fonte respondeu; ut1.json mantido.", file=sys.stderr)
        return 1
    por_dia = interpretar(texto)
    hoje = datetime.now(timezone.utc).date()
    corte = hoje - timedelta(days=DIAS_PASSADO)
    dados = [
        {"data": d.isoformat(), "ut1MenosUtc": round(v, 6)}
        for d, v in sorted(por_dia.items()) if d >= corte
    ]
    futuros = [x for x in dados if x["data"] >= hoje.isoformat()]
    if len(dados) < 60 or not futuros or any(abs(x["ut1MenosUtc"]) > 0.9 for x in dados):
        print("Dados fora do esperado; ut1.json mantido.", file=sys.stderr)
        return 1
    # So reescreve se os dados mudaram (evita commit diario vazio)
    try:
        antigo = json.load(open(SAIDA, encoding="utf-8"))["dados"]
    except Exception:
        antigo = None
    if antigo == dados:
        print("Sem mudanca.")
        return 0
    saida = {
        "geradoEm": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fonte": url,
        "descricao": "ut1MenosUtc = UT1-UTC em segundos, por dia (UTC), do IERS finals2000A.daily",
        "dados": dados,
    }
    with open(SAIDA, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)
    print(f"ut1.json gerado: {len(dados)} dias, de {dados[0]['data']} a {dados[-1]['data']}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
