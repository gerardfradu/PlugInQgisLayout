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


def _extent_for_layers(layers, crs, project):
    extent = QgsRectangle()
    for layer in layers:
        layer_extent = layer.extent()
        if not layer_extent.isFinite() or layer_extent.isEmpty():
            continue
        transform = QgsCoordinateTransform(layer.crs(), crs, project.transformContext())
        extent.combineExtentWith(transform.transformBoundingBox(layer_extent))
    return extent


def _theme_layers(collection, project, theme_name, excluded_ids=()):
    return [
        project.mapLayer(layer_id)
        for layer_id in collection.mapThemeVisibleLayerIds(theme_name)
        if layer_id not in excluded_ids and project.mapLayer(layer_id) is not None
    ]


def _normalized_theme_name(name):
    return "".join(character for character in name.casefold() if character.isalnum())


def _set_theme_layers(map_item, collection, theme_name, layers):
    map_item.setLayers(layers)
    map_item.setKeepLayerSet(True)
    map_item.setKeepLayerStyles(True)
    map_item.setLayerStyleOverrides(collection.mapThemeStyleOverrides(theme_name))


def _add_grid(map_item, extent):
    grid = QgsLayoutItemMapGrid("Graella", map_item)
    grid.setEnabled(True)
    grid.setCrs(map_item.crs())
    grid.setUnits(QgsLayoutItemMapGrid.MapUnit)
    interval = _nice_interval(extent.width() / 6)
    grid.setIntervalX(interval)
    grid.setIntervalY(interval)
    grid.setStyle(QgsLayoutItemMapGrid.Solid)
    grid.setLineSymbol(QgsLineSymbol.createSimple({
        "color": "100,100,100,150", "width": "0.25"}))
    grid.setAnnotationEnabled(True)
    grid.setAnnotationPrecision(0 if interval >= 1 else 3)
    if map_item.crs().mapUnits() == QgsUnitTypes.DistanceMeters:
        grid.setAnnotationFormat(QgsLayoutItemMapGrid.CustomFormat)
        grid.setAnnotationExpression(
            "to_string(round(@grid_number / 1000, 0)) || ' km'"
        )
    grid.setAnnotationFont(QFont("Arial", 9))
    grid.setFrameStyle(QgsLayoutItemMapGrid.LineBorder)
    grid.setFrameWidth(2)
    for side in (QgsLayoutItemMapGrid.Left, QgsLayoutItemMapGrid.Right,
                 QgsLayoutItemMapGrid.Top, QgsLayoutItemMapGrid.Bottom):
        grid.setAnnotationPosition(QgsLayoutItemMapGrid.OutsideMapFrame, side)
    grid.setAnnotationDirection(QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Left)
    grid.setAnnotationDirection(QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Right)
    grid.setAnnotationFrameDistance(3)
    map_item.grids().addGrid(grid)


def _add_theme_legend(layout, map_item, theme_name, layer_ids, x, y, width, height, item_id):
    legend = QgsLayoutItemLegend(layout)
    layout.addLayoutItem(legend)
    legend.setLinkedMap(map_item)
    legend.setTitle("Leyenda" if theme_name is None else "Leyenda - {}".format(theme_name))
    legend.setAutoUpdateModel(False)
    root = legend.model().rootGroup()
    visible_ids = set(layer_ids)
    for node in root.findLayers():
        if node.layerId() not in visible_ids:
            node.parent().removeChildNode(node)
    for group in root.findGroups(True):
        if not group.children():
            group.parent().removeChildNode(group)
    _place(legend, x, y, width, height)
    legend.setId(item_id)
    return legend


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
    excluded_ids = {layer.id() for layer in excluded if layer is not None}
    themes = project.mapThemeCollection()
    theme_names = themes.mapThemes()
    location_theme = next(
        (name for name in theme_names if _normalized_theme_name(name) == "temalocalizacion"),
        None,
    )
    map_themes = [name for name in theme_names if name != location_theme]
    reference_theme = next(
        (name for name in map_themes if _normalized_theme_name(name) == "tema1"),
        map_themes[0] if map_themes else None,
    )
    if reference_theme is not None:
        map_themes.remove(reference_theme)
        map_themes.insert(0, reference_theme)

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

    two_themes = len(map_themes) == 2
    multiple_themes = len(map_themes) > 1

    if reference_theme is not None:
        thematic = _theme_layers(themes, project, reference_theme, excluded_ids)
    else:
        thematic = [layer for layer in canvas.mapSettings().layers() if layer.id() not in excluded_ids]

    main_crs = canvas.mapSettings().destinationCrs()
    ext = _extent_for_layers(thematic, main_crs, project)
    if ext.isNull():
        ext = canvas.extent()
    ext.scale(1.05)

    maps = []
    map_count = len(map_themes) if map_themes else 1
    map_layouts = []
    if multiple_themes:
        columns = 2
        rows = (map_count + columns - 1) // columns
        cell_gap = 6
        cell_width = (map_w - cell_gap) / columns
        cell_height = (map_h - cell_gap * (rows - 1)) / rows
        label_height = 10
        panel_map_height = min(cell_width, max(35, cell_height - label_height - 45))
    else:
        columns = rows = 1
        cell_gap = 0
        cell_width = map_w
        cell_height = map_h
        label_height = 0
        panel_map_height = map_h

    for index in range(map_count):
        row = index // columns
        column = index % columns
        cell_x = margin + column * (cell_width + cell_gap)
        cell_y = top + row * (cell_height + cell_gap)
        map_y = cell_y + label_height
        map_height = panel_map_height
        legend_y = map_y + map_height + 2
        legend_height = max(20, cell_y + cell_height - legend_y)

        map_item = QgsLayoutItemMap(layout)
        layout.addLayoutItem(map_item)
        _place(map_item, cell_x, map_y, cell_width, map_height)
        map_item.setCrs(main_crs)
        if map_themes:
            theme_name = map_themes[index]
            theme_layers = _theme_layers(themes, project, theme_name, excluded_ids)
            _set_theme_layers(map_item, themes, theme_name, theme_layers)
            map_item.setId("Mapa {}".format(theme_name))
            if multiple_themes:
                theme_label = QgsLayoutItemLabel(layout)
                theme_label.setText(theme_name)
                theme_label.setFont(QFont("Arial", 11, QFont.Bold))
                theme_label.setHAlign(Qt.AlignHCenter)
                theme_label.setVAlign(Qt.AlignVCenter)
                layout.addLayoutItem(theme_label)
                _place(theme_label, cell_x, cell_y, cell_width, label_height)
        else:
            map_item.setLayers(thematic)
            map_item.setKeepLayerSet(True)
            map_item.setId("Mapa principal")
        map_item.zoomToExtent(ext)
        _frame(map_item)
        _add_grid(map_item, map_item.extent())
        maps.append(map_item)
        map_layouts.append((cell_x, cell_y, cell_width, map_y, legend_y, legend_height))

    main = maps[0]
    reference_extent = main.extent()
    for map_item in maps[1:]:
        map_item.setExtent(reference_extent)
        map_item.setScale(main.scale())
        map_item.refresh()

    y = top

    if locator is not None or location_theme is not None:
        loc_h = 85
        loc = QgsLayoutItemMap(layout)
        layout.addLayoutItem(loc)
        if two_themes:
            _, _, cell_width, map_y, _, _ = map_layouts[0]
            loc_x = margin
            loc_y = map_y + panel_map_height + 12
            loc_w = min(110, cell_width)
        else:
            loc_x, loc_y, loc_w = side_x, y, side_w
        _place(loc, loc_x, loc_y, loc_w, loc_h)
        if location_theme is not None:
            location_layers = _theme_layers(themes, project, location_theme)
            if not location_layers and locator is not None:
                location_layers = [locator]
            location_crs = main.crs()
            loc.setCrs(location_crs)
            _set_theme_layers(loc, themes, location_theme, location_layers)
            lext = _extent_for_layers(location_layers, location_crs, project)
        else:
            loc.setCrs(locator.crs())
            loc.setLayers([locator])
            loc.setKeepLayerSet(True)
            lext = locator.extent()
        if lext.isNull():
            lext = canvas.extent()
        lext.scale(1.1)
        loc.setExtent(lext)
        _frame(loc)
        loc.setId("Mapa localizacion")
        overview = QgsLayoutItemMapOverview("Zona", loc)
        overview.setEnabled(True)
        overview.setLinkedMap(main)
        overview.setStackingPosition(QgsLayoutItemMapItem.StackAboveMapLabels)
        overview.setFrameSymbol(QgsFillSymbol.createSimple({
            "color": "255,0,0,15", "outline_color": "255,0,0,255", "outline_width": "0.8"}))
        loc.overviews().addOverview(overview)
        y += loc_h + 5

    for index, map_item in enumerate(maps):
        theme_name = map_themes[index] if map_themes else None
        layer_ids = (
            [layer.id() for layer in _theme_layers(themes, project, theme_name, excluded_ids)]
            if theme_name is not None
            else [layer.id() for layer in thematic]
        )
        if two_themes:
            if index != 1:
                continue
            _add_theme_legend(
                layout, map_item, theme_name, layer_ids, side_x, top + 32,
                side_w, ph - margin - top - 92, "Leyenda {}".format(theme_name),
            )
        elif multiple_themes:
            cell_x, _, cell_width, _, legend_y, legend_height = map_layouts[index]
            _add_theme_legend(
                layout, map_item, theme_name, layer_ids, cell_x, legend_y,
                cell_width, legend_height, "Leyenda {}".format(theme_name),
            )
        else:
            _add_theme_legend(
                layout, map_item, theme_name, layer_ids, side_x, y, side_w,
                ph - margin - y - 60, "Leyenda",
            )

    north = QgsLayoutItemPicture(layout)
    layout.addLayoutItem(north)
    north.setPicturePath(NORTH_SVG)
    north.setLinkedMap(main)
    north_y = top if two_themes else ph - margin - 55
    _place(north, side_x + side_w / 2 - 10, north_y, 20, 25)
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
