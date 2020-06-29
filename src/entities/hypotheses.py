
"""
This file is part of the Extra-P software (http://www.scalasca.org/software/extra-p)

Copyright (c) 2020,
Technische Universitaet Darmstadt, Germany

This software may be modified and distributed under the terms of
a BSD-style license.  See the COPYING file in the package base
directory for details.
"""

import logging
import numpy
from util.deprecation import deprecated
from .functions import Function
from .measurement import Measurement
from .coordinate import Coordinate
from typing import List
import math


class Hypothesis:
    def __init__(self, function: Function, use_median):
        """
        Initialize Hypothesis object.
        """
        self.function: Function = function
        self._RSS = 0
        self._rRSS = 0
        self._SMAPE = 0
        self._AR2 = 0
        self._RE = 0
        self._use_median = use_median
        self._costs_are_calculated = False

    @property
    def RSS(self):
        """
        Return the RSS.
        """
        if not self._costs_are_calculated:
            raise RuntimeError("Costs are not calculated.")
        return self._RSS

    @property
    def rRSS(self):
        """
        Return the rRSS.
        """
        if not self._costs_are_calculated:
            raise RuntimeError("Costs are not calculated.")
        return self._rRSS

    @property
    def AR2(self):
        """
        Return the AR2.
        """
        if not self._costs_are_calculated:
            raise RuntimeError("Costs are not calculated.")
        return self._AR2

    @property
    def SMAPE(self):
        """
        Return the SMAPE.
        """
        if not self._costs_are_calculated:
            raise RuntimeError("Costs are not calculated.")
        return self._SMAPE

    @property
    def RE(self):
        """
        Return the relative error.
        """
        if not self._costs_are_calculated:
            raise RuntimeError("Costs are not calculated.")
        return self._RE

# region Deprecated Getter and Setter
    @deprecated("Use property directly.")
    def get_function(self):
        """
        Return the function.
        """
        return self.function

    @deprecated("Use property directly.")
    def get_RSS(self):
        """
        Return the RSS.
        """
        return self.RSS

    @deprecated("Use property directly.")
    def get_rRSS(self):
        """
        Return the rRSS.
        """
        return self.rRSS

    @deprecated("Use property directly.")
    def get_AR2(self):
        """
        Return the AR2.
        """
        return self.AR2

    @deprecated("Use property directly.")
    def get_SMAPE(self):
        """
        Return the SMAPE.
        """
        return self.SMAPE

    @deprecated
    def get_RE(self):
        """
        Return the relative error.
        """
        return self.RE

    @deprecated
    def set_RSS(self, RSS):
        """
        Set the RSS.
        """
        self._RSS = RSS

    @deprecated
    def set_rRSS(self, rRSS):
        """
        Set the rRSS.
        """
        self._rRSS = rRSS

    @deprecated
    def set_AR2(self, AR2):
        """
        Set the AR2.
        """
        self._AR2 = AR2

    @deprecated
    def set_SMAPE(self, SMAPE):
        """
        Set the SMAPE.
        """
        self._SMAPE = SMAPE

    @deprecated
    def set_RE(self, RE):
        """
        Set the RE.
        """
        self._RE = RE
# endregion

    def is_valid(self):
        """
        Checks if there is a numeric imprecision. If this is the case the hypothesis will be ignored.
        """
        valid = not (self.RSS != self.RSS or abs(self.RSS) == float('inf'))
        return valid

    def clean_constant_coefficient(self, phi, training_measurements):
        """
        This function is used to correct numerical imprecision in the caculations,
        when the constant coefficient should be zero but is instead very small.
        We take into account the minimum data value to make sure that we don't "nullify"
        actually relevant numbers.
        """
        if self._use_median:
            minimum = min(m.median for m in training_measurements)
        else:
            minimum = min(m.mean for m in training_measurements)

        if abs(self.function.constant_coefficient / minimum) < phi:
            self.function.constant_coefficient = 0


class ConstantHypothesis(Hypothesis):
    """
    This class represents a constant hypothesis, it is used to represent a performance
    function that is not affected by the input value of a parameter. The modeler calls this
    class first to see if there is a constant model that describes the data best.
    """

    def __init__(self, function, use_median):
        """
        Initialize the ConstantHypothesis.
        """
        super().__init__(function, use_median)

    # TODO: should this be calculated?
    @property
    def AR2(self):
        return 1

    def compute_cost(self, measurements: List[Measurement]):
        """
        Computes the cost of the constant hypothesis using all data points.
        """
        smape = 0
        for measurement in measurements:
            # TODO: remove old code in comments
            # _, value = coordinates[element_id].get_parameter_value(0)
            # predicted = self.function.evaluate(value)
            predicted = self.function.constant_coefficient
            if self._use_median == True:
                actual = measurement.median
            else:
                actual = measurement.mean
            # actual = measurements[element_id].get_value()
            difference = predicted - actual
            self._RSS += difference * difference
            relative_difference = difference / actual
            self._rRSS += relative_difference * relative_difference
            abssum = abs(actual) + abs(predicted)
            if abssum != 0:
                smape += abs(difference) / abssum * 2

        self._SMAPE = smape / len(measurements) * 100
        self._costs_are_calculated = True


class SingleParameterHypothesis(Hypothesis):
    """
    This class represents a single parameter hypothesis, it is used to represent
    a performance function for one parameter. The modeler calls many of these objects
    to find the best model that fits the data.
    """

    def __init__(self, function, use_median):
        """
        Initialize SingleParameterHypothesis object.
        """
        super().__init__(function, use_median)

    def compute_cost(self, training_measurements: List[Measurement], validation_measurement: Measurement):
        """
        Compute the cost for the single parameter model using leave one out crossvalidation.
        """
        value = validation_measurement.coordinate[0]
        predicted = self.function.evaluate(value)
        if self._use_median == True:
            actual = validation_measurement.median
        else:
            actual = validation_measurement.mean
        # TODO: remove old code
        # actual = validation_measurement.get_value()
        difference = predicted - actual
        self._RSS += difference * difference
        relative_difference = difference / actual
        self._rRSS += relative_difference * relative_difference
        abssum = abs(actual) + abs(predicted)
        if abssum != 0:
            self._SMAPE += (abs(difference) / abssum * 2) / \
                len(training_measurements) * 100
        self._costs_are_calculated = True

    def compute_cost_all_points(self, measurements: List[Measurement]):
        points = numpy.array([m.coordinate[0] for m in measurements])
        predicted = self.function.evaluate(points)
        actual = numpy.array([m.value(self._use_median)
                              for m in measurements])

        difference = predicted - actual
        self._RSS = numpy.sum(difference * difference)

        relativeDifference = difference / actual
        self._rRSS = numpy.sum(relativeDifference * relativeDifference)

        absolute_error = numpy.abs(difference)
        relative_error = absolute_error / actual
        self._RE = numpy.mean(relative_error)

        abssum = numpy.abs(actual) + numpy.abs(predicted)
        # This condition prevents a division by zero, but it is correct: if sum is 0, both `actual` and `predicted`
        # must have been 0, and in that case the error at this point is 0, so we don't need to add anything.
        smape = numpy.abs(difference[abssum != 0.0]) / abssum[abssum != 0.0] * 2
        self._SMAPE = numpy.mean(smape) * 100

        self._costs_are_calculated = True

    def compute_adjusted_rsquared(self, TSS, measurements):
        """
        Compute the adjusted R^2 for the hypothesis.
        """
        adjR = 1.0 - (self._RSS / TSS)
        degrees_freedom = len(measurements) - len(self.function.compound_terms) - 1
        self._AR2 = (1.0 - (1.0 - adjR) *
                     (len(measurements) - 1.0) / degrees_freedom)

    def compute_coefficients(self, measurements: List[Measurement]):
        """
        Computes the coefficients of the function using the least squares solution.
        """

        # creating a numpy matrix representation of the lgs
        a_list = []
        b_list = []
        for measurement in measurements:
            value = measurement.value(self._use_median)
            # TODO: remove old code
            # value = measurement.value
            list_element = []
            list_element.append(1)  # for constant coefficient
            for compound_term in self.function.compound_terms:
                parameter_value = measurement.coordinate[0]
                compound_term.coefficient = 1
                compound_term_value = compound_term.evaluate(
                    parameter_value)
                list_element.append(compound_term_value)
            a_list.append(list_element)
            b_list.append(value)
            # logging.debug(str(list_element)+"[x]=["+str(value)+"]")

        # solving the lgs for X to get the coefficients
        A = numpy.array(a_list)
        B = numpy.array(b_list)
        X = numpy.linalg.lstsq(A, B, None)
        # logging.debug("Coefficients:"+str(X[0]))

        # setting the coefficients for the hypothesis
        self.function.constant_coefficient = X[0][0]
        for i, compound_term in enumerate(self.function.compound_terms):
            compound_term.coefficient = X[0][i+1]

    def calc_term_contribution(self, term, measurements: List[Measurement]):
        """
        Calculates the term contribution of the term with the given term id to see if it is smaller than epsilon.
        """
        maximum_term_contribution = 0
        for measurement in measurements:
            parameter_value = measurement.coordinate[0]
            if self._use_median == True:
                contribution = abs(term.evaluate(
                    parameter_value) / measurement.median)
            else:
                contribution = abs(term.evaluate(
                    parameter_value) / measurement.mean)
            # TODO: remove old code
            # contribution = abs( term.evaluate(parameter_value) / measurement.value)
            if contribution > maximum_term_contribution:
                maximum_term_contribution = contribution
        return maximum_term_contribution


class MultiParameterHypothesis(Hypothesis):
    """
    This class represents a multi parameter hypothesis, it is used to represent
    a performance function with several parameters. However, it can have also
    only one parameter. The modeler calls many of these objects to find the best
    model that fits the data.
    """

    def __init__(self, function, use_median):
        """
        Initialize MultiParameterHypothesis object.
        """
        super().__init__(function, use_median)

    def compute_cost(self, measurements, coordinates):
        """
        Compute the cost for a multi parameter hypothesis.
        """
        self._RSS = 0
        self._rRSS = 0
        smape = 0
        re_sum = 0

        for measurement in measurements:
            coordinate = measurement.coordinate
            parameter_value_pairs = {}
            for parameter, value in enumerate(coordinate):
                parameter_value_pairs[parameter] = float(value)

            predicted = self.function.evaluate(parameter_value_pairs)
            # print(predicted)
            if self._use_median == True:
                actual = measurement.get_value_median()
            else:
                actual = measurement.get_value_mean()
            # print(actual)

            difference = predicted - actual
            # absolute_difference = abs(difference)
            abssum = abs(actual) + abs(predicted)

            # calculate relative error
            absolute_error = abs(predicted - actual)
            relative_error = absolute_error / actual
            re_sum = re_sum + relative_error

            self._RSS += difference * difference
            if self._use_median == True:
                relativeDifference = difference / measurement.get_value_median()
            else:
                relativeDifference = difference / measurement.get_value_mean()
            self._rRSS += relativeDifference * relativeDifference

            if abssum != 0.0:
                # This `if` condition prevents a division by zero, but it is correct: if sum is 0, both `actual` and `predicted`
                # must have been 0, and in that case the error at this point is 0, so we don't need to add anything.
                smape += abs(difference) / abssum * 2

        # times 100 for percentage error
        self._RE = re_sum / len(measurements)
        self._SMAPE = smape / len(measurements) * 100
        self._costs_are_calculated = True

    def compute_adjusted_rsquared(self, TSS, measurements):
        """
        Compute the adjusted R^2 for the hypothesis.
        """
        self._AR2 = 0.0
        adjR = 1.0 - (self.RSS / TSS)
        counter = 0

        for i in range(len(self.function.get_multi_parameter_terms())):
            counter += len(self.function.get_multi_parameter_terms()[i].get_compound_term_parameter_pairs())

        degrees_freedom = len(measurements) - counter - 1
        self._AR2 = (1.0 - (1.0 - adjR) * (len(measurements) - 1.0) / degrees_freedom)

    def compute_coefficients(self, measurements, coordinates):
        """
        Computes the coefficients of the function using the least squares solution.
        """
        hypothesis_total_terms = len(self.function.get_multi_parameter_terms()) + 1

        # creating a numpy matrix representation of the lgs
        a_list = []
        b_list = []
        for measurement in measurements:
            value = measurement.value(self._use_median)
            list_element = []
            for multi_parameter_term_id in range(hypothesis_total_terms):
                if multi_parameter_term_id == 0:
                    list_element.append(1)
                else:
                    multi_parameter_term = self.function[multi_parameter_term_id-1]
                    coordinate = measurement.coordinate
                    multi_parameter_term_value = multi_parameter_term.evaluate(coordinate)
                    list_element.append(multi_parameter_term_value)
            a_list.append(list_element)
            b_list.append(value)
            # print(str(list_element)+"[x]=["+str(value)+"]")
            # logging.debug(str(list_element)+"[x]=["+str(value)+"]")

        # solving the lgs for X to get the coefficients
        A = numpy.array(a_list)
        B = numpy.array(b_list)
        X = numpy.linalg.lstsq(A, B, None)
        # print("Coefficients:"+str(X[0]))
        # logging.debug("Coefficients:"+str(X[0]))

        # setting the coefficients for the hypothesis
        self.function.set_constant_coefficient(X[0][0])
        for multi_parameter_term_id in range(hypothesis_total_terms-1):
            self.function[multi_parameter_term_id].set_coefficient(X[0][multi_parameter_term_id+1])

    def calc_term_contribution(self, term_index, measurements, coordinates):
        """
        Calculates the term contribution of the term with the given term id to see if it is smaller than epsilon.
        """
        multi_parameter_terms = self.function.get_multi_parameter_terms()
        # compound_terms = self.function.get_compound_terms()
        maximum_term_contribution = 0
        for element_id in range(len(measurements)):
            # _, parameter_value = coordinates[element_id].get_parameter_value(0)
            dimensions = coordinates[element_id].get_dimensions()
            parameter_value_pairs = {}
            for i in range(dimensions):
                parameter, value = coordinates[element_id].get_parameter_value(i)
                parameter_value_pairs[parameter.get_name()] = float(value)
            if self._use_median == True:
                contribution = abs(multi_parameter_terms[term_index].evaluate(parameter_value_pairs) / measurements[element_id].get_value_median())
            else:
                contribution = abs(multi_parameter_terms[term_index].evaluate(parameter_value_pairs) / measurements[element_id].get_value_mean())
            if contribution > maximum_term_contribution:
                maximum_term_contribution = contribution
        return maximum_term_contribution