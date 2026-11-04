import math

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import QInputDialog
from qgis.core import (
    QgsProject, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel,
    QgsLayoutItemLegend, QgsLayoutItemScaleBar, QgsLayoutItemPicture,
    QgsLayoutItemMapGrid, QgsLayoutItemMapOverview,
    QgsLayoutItemMapItem, QgsLayoutPoint,
    QgsLayoutSize, QgsUnitTypes, QgsLayoutMeasurement, QgsFillSymbol,
        QgsLineSymbol,         QgsLayoutItemPage, QgsRectangle, QgsCoordinateTransform,
)

NORTH_SVG = ":/images/north_arrows/layout_default_north_arrow.svg"
LOCATOR_NAMES = ("localizacion", "localización", "loclaizacion", "localitzacio", "localització")
MM = QgsUnitTypes.LayoutMillimeters


def _place(item, x, y, w, h):
    item.attemptMove(QgsLayoutPoint(x, y, MM))
    item.attemptResize(QgsLayoutSize(w, h, MM))


def _find_locator():
    for lyr in QgsProject.instance().mapLayers().values():
        if lyr.name().strip().lower() in LOCATOR_NAMES:
            return lyr
    return None


def _unique_name(base):
    mgr = QgsProject.instance().layoutManager()
    name, n = base, 1
    while mgr.layoutByName(name):
        n += 1
        name = "{} {}".format(base, n)
    return name


def _frame(item):
    item.setFrameEnabled(True)
    item.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, MM))


def _nice_interval(raw):
    if raw <= 0:
        return 1
    exp = math.floor(math.log10(raw))
    base = raw / (10 ** exp)
    for n in (1, 2, 5, 10):
        if base <= n:
            return n * (10 ** exp)
    return 10 ** (exp + 1)


def create_layout(iface):
    project = QgsProject.instance()
    canvas = iface.mapCanvas()
    title, ok = QInputDialog.getText(iface.mainWindow(), "Layout A3", "Titulo del mapa:")
    if not ok:
        return

    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(_unique_name("Layout A3"))
    layout.pageCollection().page(0).setPageSize("A3", QgsLayoutItemPage.Landscape)

    locator = _find_locator()
    excluded = []
    if locator is not None:
        excluded = [locator]
        parent = project.layerTreeRoot().findLayer(locator.id()).parent()
        if parent is not project.layerTreeRoot():
            excluded = [n.layer() for n in parent.findLayers()]
    margin, pw, ph = 10, 420, 297
    title_h = 16
    top = margin + title_h + 4
    side_w = 100
    map_w = pw - 2 * margin - side_w - 5
    map_h = ph - margin - top
    side_x = margin + map_w + 5

    lbl = QgsLayoutItemLabel(layout)
    lbl.setText(title)
    f = QFont()
    f.setPointSize(26)
    f.setBold(True)
    lbl.setFont(f)
    lbl.setHAlign(Qt.AlignHCenter)
    lbl.setVAlign(Qt.AlignVCenter)
    layout.addLayoutItem(lbl)
    _place(lbl, margin, margin, pw - 2 * margin, title_h)
    _frame(lbl)
    lbl.setId("Titulo")

    main = QgsLayoutItemMap(layout)
    layout.addLayoutItem(main)
    _place(main, margin, top, map_w, map_h)
    main.setCrs(canvas.mapSettings().destinationCrs())
    thematic = [l for l in canvas.mapSettings().layers() if l not in excluded]
    main.setLayers(thematic)
    ext = QgsRectangle()
    to_canvas = project.transformContext()
    for lyr in thematic:
        if not lyr.extent().isFinite() or lyr.extent().isEmpty():
            continue
        tr = QgsCoordinateTransform(lyr.crs(), main.crs(), to_canvas)
        ext.combineExtentWith(tr.transformBoundingBox(lyr.extent()))
    if ext.isNull():
        ext = canvas.extent()
    ext.scale(1.05)
    main.zoomToExtent(ext)
    ext = main.extent()
    _frame(main)
    main.setId("Mapa principal")

    grid = QgsLayoutItemMapGrid("Graella", main)
    grid.setEnabled(True)
    grid.setCrs(main.crs())
    grid.setUnits(QgsLayoutItemMapGrid.MapUnit)
    interval = _nice_interval(ext.width() / 6)
    grid.setIntervalX(interval)
    grid.setIntervalY(interval)
    grid.setStyle(QgsLayoutItemMapGrid.Solid)
    grid.setLineSymbol(QgsLineSymbol.createSimple({
        "color": "0,0,0,255", "width": "0.35"}))
    grid.setAnnotationEnabled(True)
    grid.setAnnotationPrecision(0 if interval >= 1 else 3)
    grid.setAnnotationFont(QFont("Arial", 8))
    grid.setFrameStyle(QgsLayoutItemMapGrid.Zebra)
    grid.setFrameWidth(2)
    for side in (QgsLayoutItemMapGrid.Left, QgsLayoutItemMapGrid.Right,
                 QgsLayoutItemMapGrid.Top, QgsLayoutItemMapGrid.Bottom):
        grid.setAnnotationPosition(QgsLayoutItemMapGrid.OutsideMapFrame, side)
    grid.setAnnotationDirection(QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Left)
    grid.setAnnotationDirection(QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Right)
    grid.setAnnotationFrameDistance(1.5)
    main.grids().addGrid(grid)

    y = top

    if locator is not None:
        loc_h = 85
        loc = QgsLayoutItemMap(layout)
        layout.addLayoutItem(loc)
        _place(loc, side_x, y, side_w, loc_h)
        loc.setCrs(locator.crs())
        loc.setLayers([locator])
        loc.setKeepLayerSet(True)
        lext = locator.extent()
        lext.scale(1.1)
        loc.setExtent(lext)
        _frame(loc)
        loc.setId("Mapa localizacion")
        overview = QgsLayoutItemMapOverview("Zona", loc)
        overview.setEnabled(True)
        overview.setLinkedMap(main)
        overview.setStackingPosition(QgsLayoutItemMapItem.StackAboveMapLabels)
        overview.setFrameSymbol(QgsFillSymbol.createSimple({
            "color": "255,0,0,40", "outline_color": "255,0,0", "outline_width": "0.6"}))
        loc.overviews().addOverview(overview)
        y += loc_h + 5

    legend = QgsLayoutItemLegend(layout)
    layout.addLayoutItem(legend)
    legend.setLinkedMap(main)
    legend.setTitle("Leyenda")
    legend.setAutoUpdateModel(False)
    if locator is not None:
        root = legend.model().rootGroup()
        for lyr in excluded:
            node = root.findLayer(lyr.id())
            if node:
                node.parent().removeChildNode(node)
        for g in root.findGroups(True):
            if not g.children():
                g.parent().removeChildNode(g)
    _place(legend, side_x, y, side_w, ph - margin - y - 60)
    legend.setId("Leyenda")

    north = QgsLayoutItemPicture(layout)
    layout.addLayoutItem(north)
    north.setPicturePath(NORTH_SVG)
    north.setLinkedMap(main)
    _place(north, side_x + side_w / 2 - 10, ph - margin - 55, 20, 25)
    north.setId("Norte")

    sb = QgsLayoutItemScaleBar(layout)
    layout.addLayoutItem(sb)
    sb.setLinkedMap(main)
    sb.setStyle("Single Box")
    sb.setUnits(QgsUnitTypes.DistanceKilometers)
    sb.setNumberOfSegments(2)
    sb.setNumberOfSegmentsLeft(0)
    sb.applyDefaultSize(QgsUnitTypes.DistanceKilometers)
    sb.attemptMove(QgsLayoutPoint(side_x, ph - margin - 22, MM))
    sb.setId("Escala")

    sc = QgsLayoutItemLabel(layout)
    layout.addLayoutItem(sc)
    sc.setText("Escala 1:{:,.0f}".format(main.scale()).replace(",", "."))
    sc.setFont(QFont("Arial", 11))
    _place(sc, side_x, ph - margin - 8, side_w, 8)
    sc.setId("Escala numerica")

    project.layoutManager().addLayout(layout)
    iface.openLayoutDesigner(layout)
