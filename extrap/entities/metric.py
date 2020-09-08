"""
This file is part of the Extra-P software (http://www.scalasca.org/software/extra-p)

Copyright (c) 2020,
Technische Universitaet Darmstadt, Germany

This software may be modified and distributed under the terms of
a BSD-style license. See the LICENSE file in the package base
directory for details.
"""
import itertools

from extrap.util.deprecation import deprecated
from extrap.util.serialization_schema import make_value_schema


class Metric:
    """
    This class represents a metric such as time or FLOPS.
    """
    """
    Counter for global metric ids
    """
    ID_COUNTER = itertools.count()

    def __init__(self, name):
        """
        Initializes the metric object.
        """
        self.name = name
        self.id = next(Metric.ID_COUNTER)

    @deprecated("Use property directly.")
    def get_name(self):
        """
        Returns the name of the metric.
        """
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if not isinstance(other, Metric):
            return NotImplemented
        return self is other or self.name == other.name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Metric({self.name})"


MetricSchema = make_value_schema(Metric, 'name')