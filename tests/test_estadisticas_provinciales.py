import unittest

import pandas as pd

from estadisticas_provinciales import (
    calcular_tasas_graduacion_provinciales,
    comparar_registros_provinciales,
)


class EstadisticasProvincialesTests(unittest.TestCase):
    def test_tasa_usa_registros_y_cuenta_graduados(self):
        datos = pd.DataFrame(
            {
                "provincia": ["Manabí", "Manabí", "Guayas"],
                "es_graduado": [True, False, True],
            }
        )
        resumen = calcular_tasas_graduacion_provinciales(datos).set_index(
            "provincia"
        )
        self.assertEqual(resumen.loc["Manabí", "registros"], 2)
        self.assertEqual(resumen.loc["Manabí", "graduados"], 1)
        self.assertEqual(resumen.loc["Manabí", "tasa_graduacion"], 50)
        self.assertEqual(resumen.loc["Guayas", "tasa_graduacion"], 100)

    def test_compara_anos_y_marca_provincias_nuevas(self):
        datos = pd.DataFrame(
            {
                "provincia": ["Manabí"] * 5 + ["Guayas"],
                "anio": [2023, 2023, 2024, 2024, 2024, 2024],
            }
        )
        comparacion = comparar_registros_provinciales(
            datos,
            anio_base=2023,
            anio_comparacion=2024,
        ).set_index("provincia")
        self.assertEqual(comparacion.loc["Manabí", "cambio"], 1)
        self.assertEqual(
            comparacion.loc["Manabí", "variacion_porcentual"],
            50,
        )
        self.assertEqual(comparacion.loc["Guayas", "tendencia"], "Nuevo")
        self.assertTrue(
            pd.isna(comparacion.loc["Guayas", "variacion_porcentual"])
        )

    def test_no_permite_comparar_el_mismo_ano(self):
        with self.assertRaises(ValueError):
            comparar_registros_provinciales(
                pd.DataFrame(columns=["provincia", "anio"]),
                anio_base=2024,
                anio_comparacion=2024,
            )


if __name__ == "__main__":
    unittest.main()
