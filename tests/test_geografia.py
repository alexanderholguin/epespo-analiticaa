import unittest

import pandas as pd

from geografia import estimar_zona_cantonal, estimar_zonas_cantonales


class GeografiaTests(unittest.TestCase):
    def test_calculo_vectorizado_conserva_resultados_de_la_funcion_original(self):
        provincias = [
            "Manabí",
            "Guayas",
            "Esmeraldas",
            "Santa Elena",
            "Pichincha",
        ]
        pares = [
            (f"00{digito}1234567", provincia)
            for provincia in provincias
            for digito in range(10)
        ]
        pares.extend(
            [
                ("", "Manabí"),
                ("12", "Guayas"),
                ("12A345", "Esmeraldas"),
            ]
        )
        cedulas = pd.Series([par[0] for par in pares])
        provincias_serie = pd.Series([par[1] for par in pares])

        resultado = estimar_zonas_cantonales(cedulas, provincias_serie)
        esperado = [
            estimar_zona_cantonal(cedula, provincia)
            for cedula, provincia in pares
        ]

        self.assertEqual(resultado.tolist(), esperado)


if __name__ == "__main__":
    unittest.main()
