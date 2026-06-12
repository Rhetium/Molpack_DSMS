import pycountry
from fastapi import HTTPException

def nombre_pais_a_iso(nombre_pais: str) -> str:
    valor = (nombre_pais or "").strip()
    # Acepta códigos ISO-2 directamente (es lo que envía el frontend);
    # el fallback por nombre cubre datos legados y scripts de carga.
    if len(valor) == 2 and valor.isalpha():
        pais = pycountry.countries.get(alpha_2=valor.upper())
        if pais:
            return pais.alpha_2
    try:
        country = pycountry.countries.search_fuzzy(valor)[0]
        return country.alpha_2
    except LookupError:
        raise HTTPException(status_code=400, detail=f"Nombre de país inválido: {nombre_pais}")