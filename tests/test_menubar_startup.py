import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from unittest.mock import Mock, patch
from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QApplication
from platform.macos.menubar import MacMenuBar

app = QApplication.instance() or QApplication([])


class MenuBarStartupTests(unittest.TestCase):
    def setUp(self):
        self.window = Mock()
        self.window.isVisible.return_value = False
        with patch('platform.macos.menubar.QSystemTrayIcon'):
            self.menu = MacMenuBar(self.window)
        self.menu.show_initial_window()

    def tearDown(self):
        self.menu._initial_timer.stop()

    def test_waits_for_real_stable_icon_position(self):
        final = QRect(900, 0, 24, 24)
        positions = [QRect(), QRect(), QRect(1000, 0, 24, 24), final, final, final, final]
        for position in positions:
            self.menu.tray_icon.geometry.return_value = position
            self.menu._check_initial_position()
            self.window.toggle_at.assert_not_called()
        self.menu._check_initial_position()
        self.window.toggle_at.assert_called_once_with(final)
        self.assertFalse(self.menu._initial_timer.isActive())

    def test_no_icon_never_opens_at_fallback_screen_corner(self):
        self.menu.tray_icon.geometry.return_value = QRect()
        for _ in range(50):
            self.menu._check_initial_position()
        self.window.toggle_at.assert_not_called()
        self.assertFalse(self.menu._initial_timer.isActive())

    def test_user_toggle_cancels_pending_auto_open(self):
        rect = QRect(600, 0, 24, 24)
        self.menu.tray_icon.geometry.return_value = rect
        self.menu.toggle_window()
        self.assertFalse(self.menu._initial_timer.isActive())
        self.window.toggle_at.assert_called_once_with(rect)

    def test_already_visible_window_is_not_toggled_closed(self):
        self.window.isVisible.return_value = True
        self.menu.tray_icon.geometry.return_value = QRect(600, 0, 24, 24)
        for _ in range(5):
            self.menu._check_initial_position()
        self.window.toggle_at.assert_not_called()
