# Copyright 2016 Raytheon BBN Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0

import unittest
import asyncio
import time
import numpy as np

from auspex.instruments.instrument import SCPIInstrument, StringCommand, FloatCommand, IntCommand
from auspex.experiment import Experiment
from auspex.parameter import FloatParameter
from auspex.stream import DataStream, DataAxis, DataStreamDescriptor, OutputConnector
from auspex.filters.debug import Print, Passthrough
from auspex.filters.average import Averager
from auspex.log import logger, logging
logger.setLevel(logging.DEBUG)

class TestInstrument1(SCPIInstrument):
    frequency = FloatCommand(get_string="frequency?", set_string="frequency {:g}", value_range=(0.1, 10))
    serial_number = IntCommand(get_string="serial?")
    mode = StringCommand(scpi_string=":mode", allowed_values=["A", "B", "C"])

class TestInstrument2(SCPIInstrument):
    frequency = FloatCommand(get_string="frequency?", set_string="frequency {:g}", value_range=(0.1, 10))
    serial_number = IntCommand(get_string="serial?")
    mode = StringCommand(scpi_string=":mode", allowed_values=["A", "B", "C"])

class TestInstrument3(SCPIInstrument):
    power = FloatCommand(get_string="power?")
    serial_number = IntCommand(get_string="serial?")
    mode = StringCommand(scpi_string=":mode", allowed_values=["A", "B", "C"])

class TestExperiment(Experiment):

    # Create instances of instruments
    fake_instr_1 = TestInstrument1("FAKE::RESOURE::NAME")
    fake_instr_2 = TestInstrument2("FAKE::RESOURE::NAME")
    fake_instr_3 = TestInstrument3("FAKE::RESOURE::NAME")

    # Parameters
    freq_1 = FloatParameter(unit="Hz")
    freq_2 = FloatParameter(unit="Hz")

    # DataStreams
    chan1 = OutputConnector()
    chan2 = OutputConnector()

    # Constants
    samples    = 3
    num_trials = 5
    time_val   = 0.0

    def init_instruments(self):
        self.freq_1.assign_method(lambda x: print("Set: {}".format(x)))
        self.freq_2.assign_method(lambda x: print("Set: {}".format(x)))

    def init_streams(self):
        self.chan1.add_axis(DataAxis("samples", list(range(self.samples))))
        self.chan1.add_axis(DataAxis("trials", list(range(self.num_trials))))
        self.chan2.add_axis(DataAxis("samples", list(range(self.samples))))
        self.chan2.add_axis(DataAxis("trials", list(range(self.num_trials))))

    async def run(self):
        logger.debug("Data taker running (inner loop)")
        time_step = 0.1
        await asyncio.sleep(0.2)
        data_row = np.ones(self.samples*self.num_trials) + 0.1*np.random.random(self.samples*self.num_trials)
        self.time_val += time_step
        await self.chan1.push(data_row)
        logger.debug("Stream pushed points {}.".format(data_row))
        logger.debug("Stream has filled {} of {} points".format(self.chan1.points_taken, self.chan1.num_points() ))

class ExperimentTestCase(unittest.TestCase):

    def test_final_average_runs(self):
        exp             = TestExperiment()
        printer_final   = Print(name="Final")
        avgr            = Averager('trials', name="TestAverager")

        edges = [(exp.chan1, avgr.sink),
                 (avgr.final_average, printer_final.sink)]

        exp.set_graph(edges)
        exp.run_sweeps()

    def test_partial_average_runs(self):
        exp             = TestExperiment()
        printer_partial = Print(name="Partial")
        avgr            = Averager('trials', name="TestAverager")

        edges = [(exp.chan1, avgr.sink),
                 (avgr.partial_average, printer_partial.sink)]

        exp.set_graph(edges)
        exp.run_sweeps()

    def test_sameness(self):
        exp             = TestExperiment()
        printer_partial = Print(name="Partial")
        printer_final   = Print(name="Final")
        avgr            = Averager(name="TestAverager")

        edges = [(exp.chan1, avgr.sink),
                 (avgr.partial_average, printer_partial.sink),
                 (avgr.final_average, printer_final.sink)]
        exp.set_graph(edges)

        exp.add_sweep(exp.freq_1, np.linspace(0,9,10))
        avgr.axis.value = 'freq_1'
        avgr.update_descriptors()
        exp.run_sweeps()
    # def test_add_axis_to_averager(self):
    #     exp             = TestExperiment()
    #     printer_final   = Print(name="Final")
    #     avgr            = Averager('samples', name="TestAverager")

    #     edges = [(exp.chan1, avgr.sink),
    #              (avgr.final_average, printer_final.sink)]

    #     exp.set_graph(edges)
    #     exp.init_instruments()
    #     repeats = 2
    #     exp.chan1.descriptor.add_axis(DataAxis("repeats", list(range(repeats))))
    #     exp.update_descriptors()
    #     self.assertTrue(len(exp.chan1.descriptor.axes) == 3)
    #     exp.run_sweeps()

if __name__ == '__main__':
    unittest.main()
