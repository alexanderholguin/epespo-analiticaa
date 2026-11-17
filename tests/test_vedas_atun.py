import unittest

import pandas as pd

from vedas_atun import (
    calcular_cursos_en_vedas_atun,
    obtener_periodos_veda_atun,
)


class PeriodosVedaAtunTests(unittest.TestCase):
    def test_calendario_2025_tiene_dos_ventanas_de_72_dias(self):
        periodos = obtener_periodos_veda_atun().set_index("periodo")

        self.assertEqual(periodos.loc["Ventana 1", "dias"], 72)
        self.assertEqual(periodos.loc["Ventana 2", "dias"], 72)
        self.assertEqual(
            periodos.loc["Ventana 2", "inicio"].strftime("%Y-%m-%d"),
            "2025-11-09",
        )
        self.assertEqual(
            periodos.loc["Ventana 2", "fin"].strftime("%Y-%m-%d"),
            "2026-01-19",
        )

    def test_anios_previos_se_marcan_como_estimacion(self):
        periodos = obtener_periodos_veda_atun([2024, 2025, 2026])

        self.assertEqual(periodos["anio_veda"].unique().tolist(), [2024, 2025])
        referencias = periodos.groupby("anio_veda")["referencia"].first()
        self.assertEqual(referencias.loc[2024], "Estimación histórica")
        self.assertEqual(referencias.loc[2025], "Oficial (2025)")

    def test_cuenta_personas_unicas_y_estimaciones_mensuales(self):
        datos = pd.DataFrame(
            {
                "cedula_limpia": [
                    "01001",
                    "01001",
                    "02002",
                    "03003",
                    None,
                ],
                "nombres": [
                    "Ana",
                    "Ana",
                    "Luis",
                    "Marta",
                    None,
                ],
                "matricula": ["A1", "A1", "B2", "C3", None],
                "anio": [2023] * 5,
                "mes": [8, 9, 7, 9, 9],
                "fec_ini": [
                    "2023-08-01",
                    "2023-09-01",
                    "2023-07-25",
                    None,
                    None,
                ],
                "fec_fin": [
                    "2023-08-10",
                    "2023-09-10",
                    "2023-08-02",
                    None,
                    None,
                ],
            }
        )

        resumen, totales = calcular_cursos_en_vedas_atun(datos)
        ventana = resumen.set_index(["anio_veda", "periodo"]).loc[
            (2023, "Ventana 1")
        ]

        self.assertEqual(ventana["personas_unicas"], 3)
        self.assertEqual(ventana["personas_con_fecha_exacta"], 2)
        self.assertEqual(ventana["personas_estimadas_por_mes"], 1)
        self.assertEqual(ventana["registros_con_fecha_exacta"], 3)
        self.assertEqual(ventana["registros_estimados_por_mes"], 2)
        self.assertEqual(ventana["registros_sin_identidad"], 1)
        self.assertEqual(totales["personas_unicas"], 3)

    def test_fecha_de_enero_se_asocia_a_veda_iniciada_el_ano_anterior(self):
        datos = pd.DataFrame(
            {
                "cedula_limpia": [None],
                "nombres": ["José Pérez"],
                "matricula": ["M-12"],
                "anio": [2024],
                "mes": [1],
                "fec_ini": ["2024-01-10"],
                "fec_fin": ["2024-01-15"],
            }
        )

        resumen, _ = calcular_cursos_en_vedas_atun(datos)
        ventana = resumen.set_index(["anio_veda", "periodo"]).loc[
            (2023, "Ventana 2")
        ]

        self.assertEqual(ventana["personas_unicas"], 1)
        self.assertEqual(ventana["personas_con_fecha_exacta"], 1)


if __name__ == "__main__":
    unittest.main()
