import unittest

import pandas as pd

from preparacion_datos import mapear_valores_unicos


class PreparacionDatosTests(unittest.TestCase):
    def test_transforma_una_vez_por_valor_y_preserva_nulos_e_indice(self):
        serie = pd.Series(
            ["a", "b", "a", None, pd.NA],
            index=[10, 11, 12, 13, 14],
            dtype="object",
        )
        llamadas = []

        def transformar(valor):
            llamadas.append(valor)
            return "VACÍO" if pd.isna(valor) else str(valor).upper()

        resultado = mapear_valores_unicos(serie, transformar)

        self.assertEqual(
            resultado.tolist(),
            ["A", "B", "A", "VACÍO", "VACÍO"],
        )
        self.assertEqual(resultado.index.tolist(), [10, 11, 12, 13, 14])
        self.assertEqual(len(llamadas), 3)

    def test_funciona_con_serie_vacia(self):
        resultado = mapear_valores_unicos(
            pd.Series(dtype="object"),
            str,
        )

        self.assertTrue(resultado.empty)


if __name__ == "__main__":
    unittest.main()
