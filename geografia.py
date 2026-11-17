import pandas as pd


def estimar_zona_cantonal(cedula_limpia: object, provincia: str) -> str:
    cedula = str(cedula_limpia).strip()
    if not cedula.isdigit() or len(cedula) < 3:
        return "No Determinado"
    digito = int(cedula[2])
    if provincia == "Manabí":
        if digito in (0, 1):
            return "Manta / Montecristi / Jaramijó"
        if digito in (2, 3):
            return "Portoviejo y Cuenca Central"
        if digito in (4, 5):
            return "Sucre / San Vicente / Bahía"
        if digito in (6, 7):
            return "Pedernales / Jama / Cojimíes"
        return "Zona Sur (Jipijapa / Puerto López)"
    if provincia == "Guayas":
        if digito in (0, 1, 2):
            return "Guayaquil Metropolitano"
        if digito in (3, 4):
            return "Playas / Posorja / Golfo"
        return "Cantones Fluviales (Durán / Daule)"
    if provincia == "Esmeraldas":
        if digito in (0, 1, 2):
            return "Esmeraldas / Atacames"
        return "San Lorenzo / Eloy Alfaro"
    if provincia == "Santa Elena":
        return "La Libertad / Salinas / Santa Elena"
    return f"Cantones de {provincia}"


def estimar_zonas_cantonales(
    cedulas: pd.Series,
    provincias: pd.Series,
) -> pd.Series:
    provincias = provincias.reindex(cedulas.index).fillna("No Registrada")
    cedulas = cedulas.fillna("").astype(str).str.strip()
    digitos_validos = cedulas.str.isdigit() & cedulas.str.len().ge(3)
    tercer_digito = cedulas.str[2].where(digitos_validos, "")
    claves = pd.Series(
        list(zip(provincias.astype(str), tercer_digito)),
        index=cedulas.index,
        dtype=object,
    )
    lookup = {
        clave: estimar_zona_cantonal(
            "00" + clave[1] if clave[1] else "",
            clave[0],
        )
        for clave in claves.drop_duplicates()
    }
    return claves.map(lookup)
