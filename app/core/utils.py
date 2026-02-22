import pycountry
from fastapi import HTTPException

def nombre_pais_a_iso(nombre_pais: str) -> str:
    try:
        country = pycountry.countries.search_fuzzy(nombre_pais)[0]
        return country.alpha_2
    except LookupError:
        raise HTTPException(status_code=400, detail=f"Nombre de país inválido: {nombre_pais}")