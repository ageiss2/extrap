"""
This file is part of the Extra-P software (http://www.scalasca.org/software/extra-p)

Copyright (c) 2020,
Technische Universitaet Darmstadt, Germany

This software may be modified and distributed under the terms of
a BSD-style license. See the LICENSE file in the package base
directory for details.
"""

from matplotlib.figure import Figure
import matplotlib.ticker as ticker
import numpy as np
from matplotlib import cm
from gui.AdvancedPlotWidget import GraphDisplayWindow

from PySide2.QtGui import *  # @UnusedWildImport
from PySide2.QtCore import *  # @UnusedWildImport
from PySide2.QtWidgets import *  # @UnusedWildImport
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


#####################################################################


class MaxZAsSingleSurfacePlot(GraphDisplayWindow):
    def __init__(self, graphWidget, main_widget, width=5, height=4, dpi=100):
        try:
            self.colormap = cm.get_cmap('viridis')
        except:
            self.colormap = cm.get_cmap('spectral')

        super().__init__(graphWidget, main_widget, width, height, dpi)

    def draw_figure(self):
        """ 
          This function draws the graph
        """

        # Get data
        selected_metric = self.main_widget.getSelectedMetric()
        selected_callpaths = self.main_widget.getSelectedCallpath()
        if not selected_callpaths:
            return
        model_set = self.main_widget.getCurrentModel().models
        model_list = list()
        for selected_callpath in selected_callpaths:
            model = model_set[selected_callpath.path, selected_metric]
            if model != None:
                model_list.append(model)

        # Get max x and max y value as a initial default value or a value provided by user
        maxX = self.graphWidget.getMaxX()
        maxY = self.graphWidget.getMaxY()

        # define min x and min y value
        lower_max = 2.0  # since we are drawing the plots with minimum axis value of 1 to avoid nan values , so the first max-value of parameter could be 2 to calcualte number of subdivisions
        if maxX < lower_max:
            maxX = lower_max
        if maxY < lower_max:
            maxY = lower_max

        # define grid parameters based on max x and max y value
        pixelGap_x, pixelGap_y = self._calculate_grid_parameters(maxX, maxY)

        # Get the grid of the x and y values
        x = np.arange(1, maxX, pixelGap_x)
        y = np.arange(1, maxY, pixelGap_y)
        X, Y = np.meshgrid(x, y)

        # Get the z value for the x and y value
        z_List = list()
        Z_List = list()
        for model in model_list:
            function = model.hypothesis.function
            zs = np.array([self.calculate_z(x, y, function)
                           for x, y in zip(np.ravel(X), np.ravel(Y))])
            Z = zs.reshape(X.shape)
            z_List.append(zs)
            Z_List.append(Z)

        # calculate max_z value
        max_Z_List = list()
        if len(model_list) == 1:
            max_Z_List = Z_List[0]

        else:
            # for each x,y value , calculate max z for all function
            max_z_val = z_List[0][0]
            max_z_list = list()
            for i in range(len(z_List[0])):
                max_z_val = z_List[0][i]
                for j in range(len(model_list)):
                    if (z_List[j][i] > max_z_val):
                        max_z_val = z_List[j][i]
                max_z_list.append(max_z_val)

            max_Z_List = np.array(max_z_list).reshape(X.shape)

        # Get the callpath color map
        # dict_callpath_color = self.main_widget.get_callpath_color_map()
        # Set the x_label and y_label based on parameter selected.
        x_label = self.main_widget.data_display.getAxisParameter(0).name
        if x_label.startswith("_"):
            x_label = x_label[1:]
        y_label = self.main_widget.data_display.getAxisParameter(1).name
        if y_label.startswith("_"):
            y_label = y_label[1:]

        # Draw plot showing max z value considering all the selected models
        number_of_subplots = 1
        ax = self.fig.add_subplot(
            1, number_of_subplots, number_of_subplots, projection='3d')
        ax.mouse_init()
        ax.xaxis.major.formatter._useMathText = True
        ax.yaxis.major.formatter._useMathText = True
        ax.zaxis.major.formatter._useMathText = True
        im = ax.plot_surface(X, Y, max_Z_List, cmap=self.colormap)

        ax.set_xlabel('\n' + x_label, linespacing=3.2)
        ax.set_ylabel('\n' + y_label, linespacing=3.1)
        ax.set_zlabel(
            '\n' + self.main_widget.getSelectedMetric().name, linespacing=3.1)
        ax.set_title(r'Max Z value')
        self.fig.colorbar(im, ax=ax, orientation="horizontal",
                          pad=0.2, format=ticker.ScalarFormatter(useMathText=True))
        # self.fig.tight_layout()
