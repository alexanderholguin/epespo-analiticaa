import unittest

import pandas as pd

from estadisticas_areas import resumir_areas_especialidades


class EstadisticasAreasTests(unittest.TestCase):
    def test_resume_areas_cursos_y_tasas_con_todos_los_estados(self):
        datos = pd.DataFrame(
            {
                "area_operativa": [
                    "Área de Cubierta",
                    "Área de Cubierta",
                    "Área de Cubierta",
                    "Área de Máquinas",
                    "Área de Máquinas",
                ],
                "curso": [
                    "Marinero Pescador",
                    "Marinero Pescador",
                    "Timonel",
                    "Marinero De Máquinas",
                    "Marinero De Máquinas",
                ],
                "es_graduado": [True, False, False, True, False],
                "condicion": [
                    "Graduado",
                    "No culminó",
                    "No culmino",
                    "Graduado",
                    "En curso",
                ],
            }
        )

        areas, cursos = resumir_areas_especialidades(datos)
        areas = areas.set_index("area_operativa")
        marinero = cursos.set_index("curso").loc["Marinero Pescador"]

        self.assertEqual(areas.loc["Área de Cubierta", "registros"], 3)
        self.assertEqual(areas.loc["Área de Cubierta", "graduados"], 1)
        self.assertEqual(areas.loc["Área de Cubierta", "no_culmino"], 2)
        self.assertAlmostEqual(
            areas.loc["Área de Cubierta", "graduados_pct"],
            100 / 3,
        )
        self.assertEqual(areas.loc["Área de Máquinas", "otros"], 1)
        self.assertEqual(marinero["registros"], 2)
        self.assertEqual(marinero["graduados"], 1)
        self.assertEqual(marinero["no_culmino"], 1)
        self.assertEqual(marinero["tasa_no_culminacion"], 50)

    def test_devuelve_esquema_vacio(self):
        areas, cursos = resumir_areas_especialidades(pd.DataFrame())

        self.assertEqual(
            areas.columns.tolist(),
            [
                "area_operativa",
                "registros",
                "graduados",
                "graduados_pct",
                "no_culmino",
                "no_culmino_pct",
                "otros",
                "otros_pct",
            ],
        )
        self.assertIn("tasa_no_culminacion", cursos.columns)


if __name__ == "__main__":
    unittest.main()
