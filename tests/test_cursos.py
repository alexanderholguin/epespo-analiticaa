import unittest

import pandas as pd

from cursos import normalizar_curso, resumir_cursos


class NormalizarCursoTests(unittest.TestCase):
    def test_unifica_variantes_de_maquinas(self):
        variantes = (
            "Marinero Primera De Maquinas De B/P",
            "Marinero De Primera De Máquinas De B/P",
        )
        unificados = {normalizar_curso(curso) for curso in variantes}
        self.assertEqual(
            unificados,
            {"Marinero De Primera De Máquinas De B/P"},
        )

    def test_unifica_variantes_de_puente(self):
        variantes = (
            "Marinero Primera De Puente De B/P",
            "Marinero De Primera De Puente De B/P",
        )
        unificados = {normalizar_curso(curso) for curso in variantes}
        self.assertEqual(
            unificados,
            {"Marinero De Primera De Puente De B/P"},
        )

    def test_normaliza_acentos_espacios_y_puntuacion(self):
        self.assertEqual(
            normalizar_curso("  marinero de maquinas "),
            "Marinero De Máquinas",
        )
        self.assertEqual(
            normalizar_curso("Timonel/Marinero de Puente"),
            "Timonel / Marinero De Puente",
        )

    def test_no_une_cursos_con_niveles_distintos(self):
        self.assertNotEqual(
            normalizar_curso("Marinero De Máquinas"),
            normalizar_curso("Marinero De Primera De Máquinas De B/P"),
        )

    def test_resumen_muestra_variantes_y_conteos(self):
        resumen = resumir_cursos(
            pd.Series(
                [
                    "Marinero Primera De Maquinas De B/P",
                    "Marinero De Primera De Máquinas De B/P",
                ]
            )
        )
        self.assertEqual(
            set(resumen["Curso unificado"]),
            {"Marinero De Primera De Máquinas De B/P"},
        )
        self.assertEqual(resumen["Registros"].sum(), 2)


if __name__ == "__main__":
    unittest.main()
