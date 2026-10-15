import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication
from ui import preferences
from ui.main_window import PopoverSurface

app = QApplication.instance() or QApplication([])


class PopoverPaintTests(unittest.TestCase):
    def test_first_and_reopened_surface_is_opaque_with_transparent_corners(self):
        previous = preferences.theme()
        try:
            for theme, rgb in [('light', (255, 255, 255)), ('dark', (24, 30, 40))]:
                preferences.configure(theme=theme, language='ko')
                surface = PopoverSurface()
                surface.resize(430, 610)
                frames = []
                for _ in range(2):
                    surface.show()
                    app.processEvents()
                    frame = QImage(surface.size(), QImage.Format.Format_ARGB32_Premultiplied)
                    frame.fill(Qt.GlobalColor.transparent)
                    surface.render(frame)
                    body = frame.pixelColor(215, 300)
                    self.assertEqual(body.alpha(), 255)
                    self.assertEqual(body.getRgb()[:3], rgb)
                    self.assertEqual(frame.pixelColor(0, 0).alpha(), 0)
                    frames.append(frame)
                    surface.hide()
                    app.processEvents()
                self.assertEqual(frames[0], frames[1])
                surface.close()
        finally:
            preferences.configure(theme=previous, language='ko')
