import unittest
from datetime import date

import pandas as pd

from planificacion_ascensos import calcular_candidatos_ascenso


class PlanificacionAscensosTests(unittest.TestCase):
    def _datos(self):
        return pd.DataFrame(
            {
                "cedula_limpia": ["1", "1", "2", "3", "4"],
                "estado_dni": ["Con DNI"] * 5,
                "nombres": [
                    "Ana Pérez",
                    "Ana Pérez",
                    "Luis Mora",
                    "María Sol",
                    "José Ruiz",
                ],
                "provincia": ["Manabí"] * 5,
                "curso": [
                    "Marinero Pescador",
                    "Marinero Pescador",
                    "Marinero Pescador",
                    "Patrón De Pesca Costanero",
                    "Marinero De Primera De Máquinas De B/P",
                ],
                "es_graduado": [True, False, True, True, True],
                "anio": [2024, 2026, 2024, 2023, 2020],
                "mes": [11, 10, 11, 10, 1],
                "fec_fin": [
                    "2024-11-17",
                    "2026-10-01",
                    "2024-11-18",
                    "No registrada",
                    "2020-01-31",
                ],
                "fecha": ["", "", "", "", ""],
            }
        )

    def test_agrupa_por_dni_y_aplica_fecha_de_corte_inclusiva(self):
        candidatos, demanda, totales = calcular_candidatos_ascenso(
            self._datos(),
            fecha_corte=date(2026, 11, 17),
        )

        self.assertEqual(totales["personas_evaluadas"], 3)
        self.assertEqual(totales["personas_con_ruta"], 3)
        self.assertEqual(totales["personas_sin_ruta"], 0)
        self.assertEqual(totales["candidatos_potenciales"], 2)
        self.assertEqual(set(candidatos["cedula_limpia"]), {"1", "3"})
        self.assertEqual(
            candidatos.set_index("cedula_limpia").loc["1", "tiempo_espera"],
            "2 a, 0 m, 0 d",
        )
        self.assertEqual(demanda["candidatos"].sum(), 2)

    def test_marca_la_fecha_por_anio_mes_como_estimacion(self):
        datos = self._datos()
        datos.loc[3, "fec_fin"] = "No registrada"
        datos.loc[3, "anio"] = 2023
        datos.loc[3, "mes"] = 10

        candidatos, _, _ = calcular_candidatos_ascenso(
            datos,
            fecha_corte=date(2026, 11, 17),
        )

        costanero = candidatos[
            candidatos["cedula_limpia"] == "3"
        ].iloc[0]
        self.assertEqual(costanero["fuente_fecha"], "Año/mes (estimado)")
        self.assertEqual(costanero["curso_objetivo"], "Patrón / Capitán De Pesca De Altura")

    def test_excluye_identidades_invalidas_y_cursos_no_graduados(self):
        datos = self._datos()
        datos.loc[len(datos)] = [
            "5",
            "Sin DNI",
            "Persona no identificada",
            "Manabí",
            "Marinero Pescador",
            True,
            2024,
            1,
            "2024-01-01",
            "",
        ]

        candidatos, _, totales = calcular_candidatos_ascenso(
            datos,
            fecha_corte=date(2026, 11, 17),
        )

        self.assertNotIn("5", set(candidatos["cedula_limpia"]))
        self.assertEqual(totales["personas_evaluadas"], 3)


if __name__ == "__main__":
    unittest.main()
