import unittest
from fileio.json_file_reader import read_json_file
from entities.callpath import Callpath
from entities.parameter import Parameter
from entities.coordinate import Coordinate
from entities.metric import Metric
import timeit


class Test_TestFiles(unittest.TestCase):

    def test_read_1(self):
        experiment = read_json_file("data/json/input_1.JSON")
        x = Parameter('x')
        self.assertListEqual(experiment.parameters, [x])
        self.assertListEqual(experiment.coordinates, [
            Coordinate([(x, 20)]),
            Coordinate([(x, 30)]),
            Coordinate([(x, 40)]),
            Coordinate([(x, 50)]),
            Coordinate([(x, 60)])
        ])
        self.assertListEqual(experiment.metrics, [
            Metric('time')
        ])
        self.assertListEqual(experiment.callpaths, [
            Callpath('sweep')
        ])

    def test_read_2(self):
        experiment = read_json_file("data/json/input_2.JSON")

    def test_read_3(self):
        experiment = read_json_file("data/json/input_3.JSON")

    def test_read_4(self):
        experiment = read_json_file("data/json/input_4.JSON")

    def test_read_5(self):
        experiment = read_json_file("data/json/input_5.JSON")

    def test_read_6(self):
        experiment = read_json_file("data/json/input_6.JSON")

    def test_read_7(self):
        experiment = read_json_file("data/json/input_7.JSON")

    def test_read_8(self):
        experiment = read_json_file("data/json/input_8.JSON")

    def test_read_9(self):
        experiment = read_json_file("data/json/input_9.JSON")

    def test_read_10(self):
        experiment = read_json_file("data/json/input_10.JSON")

    def test_read_11(self):
        experiment = read_json_file("data/json/input_11.JSON")