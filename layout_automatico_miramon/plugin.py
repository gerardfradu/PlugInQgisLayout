from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication

from .converter import ConvertDialog
from .layout_builder import create_layout


class MiraMonToolsPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.actions = []
        self.menu = "Layout automatico y conversion MiraMon"
        self.toolbar = None

    def _add(self, text, icon, callback):
        action = QAction(QgsApplication.getThemeIcon(icon), text, self.iface.mainWindow())
        action.triggered.connect(callback)
        self.toolbar.addAction(action)
        self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)

    def initGui(self):
        self.toolbar = self.iface.addToolBar("Layout automatico y conversion MiraMon")
        self.toolbar.setObjectName("LayoutMiraMonToolbar")
        self._add("Convertir MiraMon a SHP/GPKG", "/mActionFileSave.svg", self.run_convert)
        self._add("Crear layout A3", "/mActionNewLayout.svg", self.run_layout)

    def unload(self):
        for a in self.actions:
            self.iface.removePluginMenu(self.menu, a)
        if self.toolbar:
            del self.toolbar
        self.actions = []

    def run_convert(self):
        dlg = ConvertDialog(self.iface)
        dlg.exec_()

    def run_layout(self):
        create_layout(self.iface)
