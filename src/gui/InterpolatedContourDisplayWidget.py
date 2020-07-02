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

from matplotlib.colors import LinearSegmentedColormap
from gui.AdvancedPlotWidget import GraphDisplayWindow

from PySide2.QtGui import *  # @UnusedWildImport
from PySide2.QtCore import *  # @UnusedWildImport
from PySide2.QtWidgets import *  # @UnusedWildImport
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

#####################################################################


class InterpolatedContourDisplay(GraphDisplayWindow):
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

        # Get font size for legend
        fontSize = self.graphWidget.getFontSize()

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
        if maxX <= 1000:
            numberOfPixels_x = 100
            pixelGap_x = self.getPixelGap(0, maxX, numberOfPixels_x)
        elif maxX > 1000 and maxX <= 1000000000:
            numberOfPixels_x = 75
            pixelGap_x = self.getPixelGap(0, maxX, numberOfPixels_x)
        else:
            numberOfPixels_x = 50
            pixelGap_x = self.getPixelGap(0, maxX, numberOfPixels_x)

        if maxY <= 1000:
            numberOfPixels_y = 100
            pixelGap_y = self.getPixelGap(0, maxY, numberOfPixels_y)
        elif maxY > 1000 and maxY <= 1000000000:
            numberOfPixels_y = 75
            pixelGap_y = self.getPixelGap(0, maxY, numberOfPixels_y)
        else:
            numberOfPixels_y = 50
            pixelGap_y = self.getPixelGap(0, maxY, numberOfPixels_y)

        # Get the grid of the x and y values
        x = np.arange(1.0, maxX, pixelGap_x)
        y = np.arange(1.0, maxY, pixelGap_y)
        X, Y = np.meshgrid(x, y)

        # Get the z value for the x and y value
        Z_List = list()
        z_List = list()
        for model in model_list:
            function = model.hypothesis.function
            zs = np.array([self.calculate_z(x, y, function)
                           for x, y in zip(np.ravel(X), np.ravel(Y))])
            Z = zs.reshape(X.shape)
            z_List.append(zs)
            Z_List.append(Z)

        # Get the callpath color map
        #dict_callpath_color = self.main_widget.get_callpath_color_map()

        # define the number of subplots
        number_of_subplots = 1
        if(len(Z_List) > 1):
            number_of_subplots = len(Z_List)

        # Adjusting subplots in order to avoid overlapping of labels
        # Reference : https://stackoverflow.com/questions/2418125/matplotlib-subplots-adjust-hspace-so-titles-and-xlabels-dont-overlap
        left = 0.1  # the left side of the subplots of the figure
        right = 0.9  # the right side of the subplots of the figure
        bottom = 0.2  # the bottom of the subplots of the figure
        top = 0.9    # the top of the subplots of the figure
        wspace = 0.5  # the amount of width reserved for blank space between subplots
        hspace = 0.2
        self.fig.subplots_adjust(
            left=left, bottom=bottom, right=right, top=top, wspace=wspace, hspace=hspace)

        # Set the x_label and y_label based on parameter selected.
        x_label = self.main_widget.data_display.getAxisParameter(0).name
        if x_label.startswith("_"):
            x_label = x_label[1:]
        y_label = self.main_widget.data_display.getAxisParameter(1).name
        if y_label.startswith("_"):
            y_label = y_label[1:]

        numOfCurves = 15
        #cm = self.getColorMap()
        #cm ='viridis'
        # cm='hot'

        for i in range(len(Z_List)):
            maxZ = max([max(row) for row in Z_List[i]])
            levels = np.arange(0, maxZ, (1 / float(numOfCurves)) * maxZ)
            ax = self.fig.add_subplot(1, number_of_subplots, i+1)
            ax.xaxis.major.formatter._useMathText = True
            ax.yaxis.major.formatter._useMathText = True
            CM = ax.pcolormesh(X, Y, Z_List[i], cmap=self.colormap)
            self.fig.colorbar(CM, ax=ax, orientation="horizontal",
                              pad=0.2, format=ticker.ScalarFormatter(useMathText=True))
            try:
                CS = ax.contour(X, Y, Z_List[i], colors="white", levels=levels)
                ax.clabel(CS, CS.levels[::1], inline=True, fontsize=8)
            except ValueError:  # raised if function selected is constant
                pass
            ax.set_xlabel('\n' + x_label)
            ax.set_ylabel('\n' + y_label)

            titleName = selected_callpaths[i].name
            if titleName.startswith("_"):
                titleName = titleName[1:]
            ax.set_title(titleName)
            for item in ([ax.xaxis.label, ax.yaxis.label]):
                item.set_fontsize(10)
            for item in ([ax.title]):
                item.set_fontsize(fontSize)

    def getColorMap(self):
        colors = [(0, 0, 1), (0, 1, 0), (1, 0, 0)]
        n_bin = 100
        cmap_name = 'my_list'
        colorMap = LinearSegmentedColormap.from_list(
            cmap_name, colors, N=n_bin)
        return colorMap
