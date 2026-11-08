import os

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel,
    QComboBox, QLineEdit, QFileDialog, QCheckBox, QMessageBox,
)
from qgis.core import QgsVectorLayer, QgsVectorFileWriter, QgsProject, QgsRasterLayer

MM_EXT = "*.pol *.arc *.pnt *.img"


def convert_file(src, out_dir, fmt, load=True):
    name = os.path.splitext(os.path.basename(src))[0]
    if src.lower().endswith(".img"):
        return convert_raster(src, name, out_dir, load)
    layer = QgsVectorLayer(src, name, "ogr")
    if not layer.isValid():
        return None, "No se pudo abrir (necesita GDAL >= 3.9 con driver MiraMon)"

    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.fileEncoding = "UTF-8"
    if fmt == "gpkg":
        out = os.path.join(out_dir, name + ".gpkg")
        opts.driverName = "GPKG"
        opts.layerName = name
    else:
        out = os.path.join(out_dir, name + ".shp")
        opts.driverName = "ESRI Shapefile"

    res = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, out, QgsProject.instance().transformContext(), opts)
    if res[0] != QgsVectorFileWriter.NoError:
        return None, res[1]

    if load:
        target = out if fmt != "gpkg" else "{}|layername={}".format(out, name)
        new = QgsVectorLayer(target, name, "ogr")
        if new.isValid():
            QgsProject.instance().addMapLayer(new)
    return out, None


def convert_raster(src, name, out_dir, load=True):
    from osgeo import gdal
    gdal.UseExceptions()
    out = os.path.join(out_dir, name + ".tif")
    try:
        ds = gdal.Open(src)
        if ds is None:
            return None, "No se pudo abrir el raster (necesita GDAL >= 3.9)"
        res = gdal.Translate(out, ds, format="GTiff",
                             creationOptions=["COMPRESS=LZW", "TILED=YES"])
        if res is None:
            return None, "Fallo al escribir el GeoTIFF"
        res = None
        ds = None
    except Exception as e:
        return None, str(e)
    if load:
        rl = QgsRasterLayer(out, name)
        if rl.isValid():
            QgsProject.instance().addMapLayer(rl)
    return out, None


class ConvertDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.setWindowTitle("Convertir MiraMon a SHP / GPKG")
        self.resize(560, 420)
        lay = QVBoxLayout(self)

        lay.addWidget(QLabel("Ficheros MiraMon (.pol, .arc, .pnt, .img):"))
        self.files = QListWidget()
        lay.addWidget(self.files)
        row = QHBoxLayout()
        b_add = QPushButton("Anadir...")
        b_add.clicked.connect(self.add_files)
        b_clear = QPushButton("Vaciar")
        b_clear.clicked.connect(self.files.clear)
        row.addWidget(b_add)
        row.addWidget(b_clear)
        lay.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Formato:"))
        self.fmt = QComboBox()
        self.fmt.addItem("GeoPackage (.gpkg)", "gpkg")
        self.fmt.addItem("Shapefile (.shp)", "shp")
        row.addWidget(self.fmt)
        row.addWidget(QLabel("(los .img siempre se guardan como GeoTIFF)"))
        lay.addLayout(row)

        row = QHBoxLayout()
        self.out = QLineEdit()
        b_out = QPushButton("Carpeta de salida...")
        b_out.clicked.connect(self.pick_out)
        row.addWidget(self.out)
        row.addWidget(b_out)
        lay.addLayout(row)

        self.load = QCheckBox("Cargar resultados en el proyecto")
        self.load.setChecked(True)
        lay.addWidget(self.load)

        b_run = QPushButton("Convertir")
        b_run.clicked.connect(self.run)
        lay.addWidget(b_run)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Ficheros MiraMon", "", "MiraMon ({})".format(MM_EXT))
        for p in paths:
            self.files.addItem(p)
        if paths and not self.out.text():
            self.out.setText(os.path.dirname(paths[0]))

    def pick_out(self):
        d = QFileDialog.getExistingDirectory(self, "Carpeta de salida", self.out.text())
        if d:
            self.out.setText(d)

    def run(self):
        out_dir = self.out.text()
        if self.files.count() == 0 or not out_dir:
            QMessageBox.warning(self, "Conversion MiraMon", "Anade ficheros y elige carpeta de salida.")
            return
        os.makedirs(out_dir, exist_ok=True)
        ok, errs = [], []
        for i in range(self.files.count()):
            src = self.files.item(i).text()
            out, err = convert_file(src, out_dir, self.fmt.currentData(), self.load.isChecked())
            if err:
                errs.append("{}: {}".format(os.path.basename(src), err))
            else:
                ok.append(out)
        msg = "Convertidos: {}".format(len(ok))
        if errs:
            msg += "\n\nErrores:\n" + "\n".join(errs)
        QMessageBox.information(self, "Conversion MiraMon", msg)
