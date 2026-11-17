import unittest

import pandas as pd

from modalidades import normalizar_modalidad, resumir_modalidades


class NormalizarModalidadTests(unittest.TestCase):
    def test_unifica_acentos_espacios_y_mayusculas(self):
        self.assertEqual(normalizar_modalidad("CAPACITACION"), "Capacitación")
        self.assertEqual(normalizar_modalidad(" capacitación "), "Capacitación")

    def test_agrupa_formacion_regular_con_formacion(self):
        self.assertEqual(normalizar_modalidad("Formacion Regular"), "Formación")
        self.assertEqual(normalizar_modalidad("Formación"), "Formación")

    def test_normaliza_error_de_escritura_confirmado(self):
        self.assertEqual(
            normalizar_modalidad("Actua Cono"),
            "Actualización de Conocimientos",
        )
        self.assertEqual(
            normalizar_modalidad("Actualización de conocimientos"),
            "Actualización de Conocimientos",
        )

    def test_conserva_homologacion_as_separada(self):
        self.assertEqual(normalizar_modalidad("Homologación"), "Homologación")
        self.assertEqual(
            normalizar_modalidad("Homologacion-As"),
            "Homologación-As",
        )

    def test_unifica_aliases_que_se_normalizaban_en_la_consulta(self):
        for valor, esperado in (
            ("ELD", "Estudio Libre Dirigido"),
            ("Estudio Libre Dirigido", "Estudio Libre Dirigido"),
            ("NIVELACION", "Nivelación"),
        ):
            with self.subTest(valor=valor):
                self.assertEqual(normalizar_modalidad(valor), esperado)

    def test_unifica_valores_sin_registro(self):
        for valor in (None, float("nan"), "NaN", "Nulo", "Sin Registro"):
            with self.subTest(valor=valor):
                self.assertEqual(normalizar_modalidad(valor), "Sin Registro")

    def test_resumen_muestra_variantes_y_conteos(self):
        resumen = resumir_modalidades(
            pd.Series(["Formacion", "Formación Regular", "Formación"])
        )
        registros = resumen.set_index("Nombre original")["Registros"]
        self.assertEqual(set(resumen["Modalidad unificada"]), {"Formación"})
        self.assertEqual(registros["Formacion"], 1)
        self.assertEqual(registros["Formación Regular"], 1)
        self.assertEqual(registros["Formación"], 1)


if __name__ == "__main__":
    unittest.main()
