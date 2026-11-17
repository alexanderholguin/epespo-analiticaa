import unittest

import pandas as pd

from duplicados_trayectoria import (
    resumir_codigos_impresion,
    resumir_trayectoria_por_jerarquia,
)


class DuplicadosTrayectoriaTests(unittest.TestCase):
    def test_resume_codigos_y_separa_valores_no_reconocidos(self):
        datos = pd.DataFrame(
            {
                "impresion": [0, 1, 2, 2, None, 3],
                "estado_dni": [
                    "Con DNI",
                    "Con DNI",
                    "Con DNI",
                    "Con DNI",
                    "Sin DNI",
                    "Con DNI",
                ],
                "cedula_limpia": [
                    "0100000001",
                    "0100000002",
                    "0100000003",
                    "0100000003",
                    "",
                    "0100000004",
                ],
                "curso": ["A", "A", "A", "B", "B", "C"],
            }
        )

        resumen, por_curso = resumir_codigos_impresion(datos)
        por_codigo = resumen.set_index("codigo")

        self.assertEqual(por_codigo.loc["0", "registros"], 1)
        self.assertEqual(por_codigo.loc["1", "registros"], 1)
        self.assertEqual(por_codigo.loc["2", "registros"], 2)
        self.assertEqual(por_codigo.loc["2", "personas_dni"], 1)
        self.assertEqual(
            por_codigo.loc["—", "clasificacion"],
            "Sin código / no reconocido",
        )
        self.assertEqual(
            por_curso.loc[
                (por_curso["curso"] == "A") & (por_curso["codigo"] == "2"),
                "registros",
            ].iloc[0],
            1,
        )

    def test_distingue_un_curso_una_jerarquia_y_avance(self):
        datos = pd.DataFrame(
            {
                "estado_dni": ["Con DNI"] * 6 + ["Sin DNI"],
                "cedula_limpia": [
                    "0100000001",
                    "0100000001",
                    "0100000002",
                    "0100000003",
                    "0100000003",
                    "0100000003",
                    "",
                ],
                "curso": [
                    "Marinero Pescador",
                    "Pescador Artesanal",
                    "Marinero Pescador",
                    "Marinero Pescador",
                    "Marinero De Primera",
                    "Patrón Costanero",
                    "Patrón Costanero",
                ],
                "escala_nautica": [
                    "1. Base",
                    "1. Base",
                    "1. Base",
                    "1. Base",
                    "2. Calificada",
                    "3. Mando medio",
                    "3. Mando medio",
                ],
            }
        )

        por_jerarquia, totales = resumir_trayectoria_por_jerarquia(datos)
        nivel_base = por_jerarquia.set_index("jerarquia").loc["1. Base"]

        self.assertEqual(totales["personas_analizadas"], 3)
        self.assertEqual(totales["una_jerarquia_un_curso"], 1)
        self.assertEqual(totales["una_jerarquia_varios_cursos"], 1)
        self.assertEqual(totales["varias_jerarquias"], 1)
        self.assertEqual(nivel_base["un_curso"], 1)
        self.assertEqual(nivel_base["varios_cursos"], 1)


if __name__ == "__main__":
    unittest.main()
