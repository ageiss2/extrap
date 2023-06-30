# This file is part of the Extra-P software (http://www.scalasca.org/software/extra-p)
#
# Copyright (c) 2020-2023, Technical University of Darmstadt, Germany
#
# This software may be modified and distributed under the terms of a BSD-style license.
# See the LICENSE file in the base directory for details.

import signal
import sys
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Optional, Sequence, Tuple

from PySide6 import QtGui
from PySide6.QtCore import *  # @UnusedWildImport
from PySide6.QtGui import *  # @UnusedWildImport
from PySide6.QtWidgets import *  # @UnusedWildImport

import extrap
from extrap.entities.calltree import Node
from extrap.entities.experiment import Experiment
from extrap.entities.model import Model
from extrap.fileio.experiment_io import read_experiment, write_experiment
from extrap.fileio.file_reader import all_readers
from extrap.fileio.file_reader.cube_file_reader2 import CubeFileReader2
from extrap.gui.ColorWidget import ColorWidget
from extrap.gui.CubeFileReader import CubeFileReader
from extrap.gui.DataDisplay import DataDisplayManager, GraphLimitsWidget
from extrap.gui.LogWidget import LogWidget
from extrap.gui.ModelerWidget import ModelerWidget
from extrap.gui.PlotTypeSelector import PlotTypeSelector
from extrap.gui.components.ProgressWindow import ProgressWindow
from extrap.gui.SelectorWidget import SelectorWidget
from extrap.gui.components import file_dialog
from extrap.gui.components.model_color_map import ModelColorMap
from extrap.gui.components.plot_formatting_options import PlotFormattingOptions, PlotFormattingDialog
from extrap.modelers.model_generator import ModelGenerator
from extrap.util.deprecation import deprecated

DEFAULT_MODEL_NAME = "Default Model"


class CallPathEnum(Enum):
    constant = "constant"
    logarithmic = "logarithmic"
    polynomial = "polynomial"
    exponential = "exponential"


class MainWidget(QMainWindow):

    def __init__(self, *args, **kwargs):
        """
        Initializes the extrap application widget.
        """
        super(MainWidget, self).__init__(*args, **kwargs)
        self.max_value = 0
        self.min_value = 0
        self.old_x_pos = 0
        self._experiment = None
        self.model_color_map = ModelColorMap()
        self.plot_formatting_options = PlotFormattingOptions()
        self.experiment_change = True
        self.initUI()
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        # switch for using mean or median measurement values for modeling
        # is used when loading the data from a file and then modeling directly
        self.median = False

        if sys.platform.startswith('darwin'):
            self._macos_update_title_bar()

    # noinspection PyAttributeOutsideInit
    def initUI(self):
        """
        Initializes the User Interface of the extrap widget. E.g. the menus.
        """

        self.setWindowTitle(extrap.__title__)
        # Status bar
        # self.statusBar()

        # Main splitter
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setDockNestingEnabled(True)

        # Left side: Callpath and metric selection
        dock = QDockWidget("Selection", self)
        self.selector_widget = SelectorWidget(self, dock)
        dock.setWidget(self.selector_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        # middle: Graph

        self.data_display = DataDisplayManager(self, self)
        central_widget = self.data_display

        # Right side: Model configurator
        dock = QDockWidget("Modeler", self)
        self.modeler_widget = ModelerWidget(self, dock)
        dock.setWidget(self.modeler_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        # bottom widget
        dock = QDockWidget("Color Info", self)
        self.color_widget = ColorWidget()
        dock.setWidget(self.color_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        dock = QDockWidget("Graph Limits", self)
        self.graph_limits_widget = GraphLimitsWidget(self, self.data_display)
        dock.setWidget(self.graph_limits_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock, Qt.Horizontal)

        dock2 = QDockWidget("Log", self)
        self.log_widget = LogWidget(self)
        dock2.setWidget(self.log_widget)
        self.tabifyDockWidget(dock, dock2)
        dock2.hide()
        # Menu creation

        # File menu
        screenshot_action = QAction('S&creenshot', self)
        screenshot_action.setShortcut('Ctrl+I')
        screenshot_action.setStatusTip('Creates a screenshot of the Extra-P GUI')
        screenshot_action.triggered.connect(self.screenshot)

        exit_action = QAction('E&xit', self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(self.close)

        file_imports = []
        for reader in all_readers.values():
            if reader is CubeFileReader2:
                file_imports.append((reader.GUI_ACTION, reader.DESCRIPTION, self.open_cube_file))
            else:
                file_mode = QFileDialog.FileMode.Directory if reader.LOADS_FROM_DIRECTORY else None
                file_imports.append((reader.GUI_ACTION, reader.DESCRIPTION,
                                     self._make_import_func(reader.DESCRIPTION, reader().read_experiment,
                                                            filter=reader.FILTER, file_mode=file_mode,
                                                            model=reader.GENERATE_MODELS_AFTER_LOAD)))

        open_experiment_action = QAction('&Open experiment', self)
        open_experiment_action.setStatusTip('Opens experiment file')
        open_experiment_action.setShortcut(QKeySequence.Open)
        open_experiment_action.triggered.connect(self.open_experiment)

        save_experiment_action = QAction('&Save experiment', self)
        save_experiment_action.setStatusTip('Saves experiment file')
        save_experiment_action.setShortcut(QKeySequence.Save)
        save_experiment_action.triggered.connect(self.save_experiment)
        save_experiment_action.setEnabled(False)
        self.save_experiment_action = save_experiment_action

        # View menu
        change_font_action = QAction('Plot &formatting options', self)
        change_font_action.setStatusTip('Change the formatting of the plots')
        change_font_action.triggered.connect(self.open_plot_format_dialog_box)

        select_view_action = QAction('Select plot &type', self)
        select_view_action.setStatusTip('Select the plots you want to view')
        select_view_action.triggered.connect(self.open_select_plots_dialog_box)

        # Plots menu
        graphs = ['&Line graph', 'Selected models in same &surface plot', 'Selected models in &different surface plots',
                  'Dominating models in a 3D S&catter plot',
                  'Max &z as a single surface plot', 'Dominating models and max z as &heat map',
                  'Selected models in c&ontour plot', 'Selected models in &interpolated contour plots',
                  '&Measurement points']
        graph_actions = [QAction(g, self) for g in graphs]
        for i, g in enumerate(graph_actions):
            slot = (lambda k: lambda: self.data_display.reloadTabs((k,)))(i)
            g.triggered.connect(slot)

        # Model menu
        model_delete_action = QAction('&Delete model', self)
        model_delete_action.setShortcut('Ctrl+D')
        model_delete_action.setStatusTip('Delete the current model')
        model_delete_action.triggered.connect(self.selector_widget.model_delete)

        model_rename_action = QAction('&Rename model', self)
        model_rename_action.setShortcut('Ctrl+R')
        model_rename_action.setStatusTip('Rename the current model')
        model_rename_action.triggered.connect(self.selector_widget.model_rename)

        metric_delete_action = QAction('Dele&te metrics', self)
        metric_delete_action.triggered.connect(self.selector_widget.delete_metric)

        # compare menu
        compare_action = QAction('&Compare with experiment', self)
        compare_action.setStatusTip('Compare the current models with ')
        compare_action.triggered.connect(self.selector_widget.model_delete)

        # Filter menu
        # filter_callpath_action = QAction('Filter Callpaths', self)
        # filter_callpath_action.setShortcut('Ctrl+F')
        # filter_callpath_action.setStatusTip('Select the callpath you want to hide')
        # filter_callpath_action.triggered.connect(self.hide_callpath_dialog_box)

        # Main menu bar
        menubar = self.menuBar()
        menubar.setNativeMenuBar(True)

        file_menu = menubar.addMenu('&File')
        for name, tooltip, command in file_imports:
            action = QAction(name, self)
            action.setStatusTip(tooltip)
            action.triggered.connect(command)
            file_menu.addAction(action)
        file_menu.addSeparator()
        file_menu.addAction(open_experiment_action)
        file_menu.addAction(save_experiment_action)
        file_menu.addSeparator()
        file_menu.addAction(screenshot_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu('&View')
        view_menu.addAction(change_font_action)
        view_menu.addAction(select_view_action)
        ui_parts_menu = self.createPopupMenu()
        if ui_parts_menu:
            ui_parts_menu_action = view_menu.addMenu(ui_parts_menu)
            ui_parts_menu_action.setText('Tool &windows')

        plots_menu = menubar.addMenu('&Plots')
        for g in graph_actions:
            plots_menu.addAction(g)

        model_menu = menubar.addMenu('&Model')
        model_menu.addAction(model_delete_action)
        model_menu.addAction(model_rename_action)
        model_menu.addSeparator()
        model_menu.addAction(metric_delete_action)

        # filter_menu = menubar.addMenu('Filter')
        # filter_menu.addAction(filter_callpath_action)

        # Help menue
        help_menu = menubar.addMenu('&Help')

        doc_action = QAction('&Documentation', self)
        doc_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(extrap.__documentation_link__)))
        help_menu.addAction(doc_action)

        about_action = QAction('&About', self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        # Main window
        self.resize(1200, 800)
        self.setCentralWidget(central_widget)
        self.experiment_change = False
        self.show()

    def set_experiment(self, experiment, file_name="", *, compared=False):
        if experiment is None:
            raise ValueError("Experiment cannot be none.")
        self.experiment_change = True
        self._experiment = experiment
        self._set_opened_file_name(file_name, compared=compared)
        self.save_experiment_action.setEnabled(True)
        self.selector_widget.on_experiment_changed()
        self.data_display.experimentChange()
        self.modeler_widget.experimentChanged()
        self.experiment_change = False
        self.updateMinMaxValue()
        self.update()

    def on_selection_changed(self):
        if not self.experiment_change:
            self.data_display.updateWidget()
            self.update()
            self.updateMinMaxValue()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()

    def closeEvent(self, event):
        if not self.windowFilePath():
            event.accept()
            return
        msg_box = QMessageBox(QMessageBox.Question, 'Quit', "Are you sure to quit?",
                              QMessageBox.No | QMessageBox.Yes, self, Qt.Sheet)
        msg_box.setDefaultButton(QMessageBox.No)

        if msg_box.exec() == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def getExperiment(self) -> Experiment:
        return self._experiment

    def get_selected_metric(self):
        return self.selector_widget.getSelectedMetric()

    def get_selected_call_tree_nodes(self) -> Sequence[Node]:
        return self.selector_widget.get_selected_call_tree_nodes()

    def get_current_model_gen(self) -> Optional[ModelGenerator]:
        return self.selector_widget.getCurrentModel()

    def get_selected_models(self) -> Tuple[Optional[Sequence[Model]], Optional[Sequence[Node]]]:
        return self.selector_widget.get_selected_models()

    def open_plot_format_dialog_box(self):
        dialog = PlotFormattingDialog(self.plot_formatting_options, self, Qt.Sheet)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.data_display.updateWidget()
            self.update()

    def open_select_plots_dialog_box(self):
        dialog = PlotTypeSelector(self, self.data_display)
        dialog.setModal(True)
        dialog.open()

    # def hide_callpath_dialog_box(self):
    #     callpathList = list()
    #     for callpath in CallPathEnum:
    #         callpathList.append(callpath.value)
    #     answer,ok = QInputDialog.getItem(
    #         self, "Callpath Filter", "Select the call path to hide:", callpathList, 0, True)

    @deprecated
    def getFontSize(self):
        return self.plot_formatting_options.font_size

    def screenshot(self, _checked=False, target=None, name_addition=""):
        """
        This function creates a screenshot of this or the target widget
        and stores it into a file. It opens a file dialog to
        specify the file name and type.
        """
        if not target:
            target = self
        pixmap = target.grab()
        image = pixmap.toImage()

        def _save(file_name):
            with ProgressWindow(self, "Saving Screenshot"):
                image.save(file_name)

        initial_path = Path(self.windowFilePath()).stem + name_addition
        file_filter = ';;'.join(
            [f"{str(f, 'utf-8').upper()} image (*.{str(f, 'utf-8')})" for f in QImageWriter.supportedImageFormats() if
             str(f, 'utf-8') not in ['icns', 'cur', 'ico']])
        dialog = file_dialog.showSave(self, _save, "Save Screenshot", initial_path, file_filter)
        dialog.selectNameFilter("PNG image (*.png)")

    def model_experiment(self, experiment, file_name=""):
        # initialize model generator
        model_generator = ModelGenerator(experiment, use_median=self.median, name=DEFAULT_MODEL_NAME)
        with ProgressWindow(self, 'Modeling') as pbar:
            # create models from data
            model_generator.model_all(pbar)
        self.set_experiment(experiment, file_name)

    def _make_import_func(self, title, reader_func, **kwargs):
        return partial(self.import_file, reader_func, title, **kwargs)

    def import_file(self, reader_func, title='Open File', filter='', model=True, progress_text="Loading File",
                    file_name=None, file_mode=None):
        def _import_file(file_name):
            with ProgressWindow(self, progress_text) as pw:
                experiment = reader_func(file_name, pw)
                # call the modeler and create a function model
                if model:
                    self.model_experiment(experiment, file_name)
                else:
                    self.set_experiment(experiment, file_name)

        if file_name:
            _import_file(file_name)
        else:
            file_dialog.show(self, _import_file, title, filter=filter, file_mode=file_mode)

    def _set_opened_file_name(self, file_name, *, compared=False):
        if file_name:
            self.setWindowFilePath(file_name if not compared else "")
            self.setWindowTitle(Path(file_name).name + " – " + extrap.__title__)
        else:
            self.setWindowFilePath("")
            self.setWindowTitle(extrap.__title__)

    def open_experiment(self, file_name=None):
        self.import_file(read_experiment, 'Open Experiment',
                         filter='Experiments (*.extra-p)',
                         model=False,
                         progress_text="Loading experiment",
                         file_name=file_name)

    def save_experiment(self):
        def _save(file_name):
            with ProgressWindow(self, "Saving Experiment") as pw:
                write_experiment(self.getExperiment(), file_name, pw)
                self._set_opened_file_name(file_name)

        file_dialog.showSave(self, _save, 'Save Experiment', filter='Experiments (*.extra-p)')

    def open_cube_file(self):
        def _process_cube(dir_name):
            dialog = CubeFileReader(self, dir_name)
            dialog.setWindowFlag(Qt.Sheet, True)
            dialog.setModal(True)
            dialog.exec()  # do not use open, wait for loading to finish
            if dialog.valid:
                self.model_experiment(dialog.experiment, dir_name)

        file_dialog.showOpenDirectory(self, _process_cube, 'Select a Directory with a Set of CUBE Files')

    def updateMinMaxValue(self):
        if not self.experiment_change:
            self.color_widget.update_min_max(*self.selector_widget.update_min_max_value())

    def show_about_dialog(self):
        QMessageBox.about(self, "About " + extrap.__title__,
                          f"""<h1>{extrap.__title__}</h1>
<p>Version {extrap.__version__}</p>
<p>{extrap.__description__}</p>
<p>{extrap.__copyright__}</p>
""")

    activate_event_handlers = []

    def event(self, e: QEvent) -> bool:
        if e.type() == QEvent.Type.WindowActivate:
            for h in self.activate_event_handlers:
                h(e)
        elif e.type() == QEvent.Type.LayoutRequest or e.type() == QEvent.Type.WinIdChange:
            if sys.platform.startswith('darwin'):
                self._macos_update_title_bar()
        return super().event(e)

    def _macos_update_title_bar(self):
        try:
            import objc
            from AppKit import NSWindow, NSView, NSColor, NSColorSpace
            ns_view = objc.objc_object(c_void_p=int(self.winId()))
            ns_window = ns_view.window()
            ns_window.setTitlebarAppearsTransparent_(True)
            ns_window.setColorSpace_(NSColorSpace.sRGBColorSpace())
            c = self.palette().window().color()
            ns_window_color = NSColor.colorWithDeviceRed_green_blue_alpha_(c.redF(), c.greenF(), c.blueF(), c.alphaF())
            ns_window.setBackgroundColor_(ns_window_color)
        except ImportError:
            pass
