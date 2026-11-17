import unittest

import pandas as pd

from estadisticas_historicas import (
    calcular_crecimiento_interanual,
    resumir_evolucion,
)


class EstadisticasHistoricasTests(unittest.TestCase):
    def test_resume_total_graduados_brecha_y_tasa_por_anio(self):
        datos = pd.DataFrame(
            {
                "anio": [2022, 2022, 2022, 2023, 2023],
                "es_graduado": [True, True, False, True, False],
            }
        )

        resumen = resumir_evolucion(datos, "anio").set_index("periodo")

        self.assertEqual(resumen.loc[2022, "registros"], 3)
        self.assertEqual(resumen.loc[2022, "graduados"], 2)
        self.assertEqual(resumen.loc[2022, "brecha"], 1)
        self.assertAlmostEqual(resumen.loc[2022, "tasa_graduacion"], 200 / 3)
        self.assertEqual(resumen.loc[2023, "tasa_graduacion"], 50)

    def test_calcula_crecimiento_interanual_y_filtra_mismo_mes(self):
        datos = pd.DataFrame(
            {
                "anio": [2023, 2023, 2024, 2024, 2024],
                "mes": [1, 2, 1, 1, 2],
            }
        )

        actuales, anteriores, crecimiento = calcular_crecimiento_interanual(
            datos,
            anio_actual=2024,
            mes=1,
        )

        self.assertEqual(actuales, 2)
        self.assertEqual(anteriores, 1)
        self.assertEqual(crecimiento, 100)

    def test_no_calcula_porcentaje_sin_base_anterior(self):
        datos = pd.DataFrame(
            {
                "anio": [2024, 2024],
                "mes": [1, 2],
            }
        )

        actuales, anteriores, crecimiento = calcular_crecimiento_interanual(
            datos,
            anio_actual=2024,
        )

        self.assertEqual(actuales, 2)
        self.assertEqual(anteriores, 0)
        self.assertIsNone(crecimiento)


if __name__ == "__main__":
    unittest.main()
