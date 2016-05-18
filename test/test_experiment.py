import unittest
import asyncio
import numpy as np

from pycontrol.instruments.instrument import Instrument, StringCommand, FloatCommand, IntCommand
from pycontrol.experiment import Experiment, FloatParameter, Quantity
from pycontrol.streams.stream import DataStream, DataAxis, DataStreamDescriptor
from pycontrol.streams.io import Printer
from pycontrol.streams.process import Averager

class TestInstrument1(Instrument):
    frequency = FloatCommand(get_string="frequency?", set_string="frequency {:g}", value_range=(0.1, 10))
    serial_number = IntCommand(get_string="serial?")
    mode = StringCommand(scpi_string=":mode", allowed_values=["A", "B", "C"])

class TestInstrument2(Instrument):
    frequency = FloatCommand(get_string="frequency?", set_string="frequency {:g}", value_range=(0.1, 10))
    serial_number = IntCommand(get_string="serial?")
    mode = StringCommand(scpi_string=":mode", allowed_values=["A", "B", "C"])

class TestInstrument3(Instrument):
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

    # Quantities
    power = Quantity(unit="Watts")
    clout = Quantity(unit="Trumps")

    # DataStreams
    chan1 = DataStream()
    chan2 = DataStream()

    # Constants
    samples    = 10
    num_trials = 128

    def init_instruments(self):
        # Add a "base" data axis
        # Say we are averaging 10 samples per trigger
        descrip = DataStreamDescriptor()
        descrip.add_axis(DataAxis("samples", range(self.samples)))
        descrip.add_axis(DataAxis("trials", range(self.num_trials)))
        self.chan1.set_descriptor(descrip)
        self.chan2.set_descriptor(descrip)

    async def run(self):
        print("Data taker running")
        start_time = 0
        time_step  = 20e-6
        
        while True:
            #Produce fake noisy sinusoid data every 0.02 seconds until we have 1000 points
            if self._output_streams['chan1'].done():
                print("Data taker finished.")
                break
            await asyncio.sleep(0.1)
            
            print("Stream has filled {} of {} points".format(self._output_streams['chan1'].points_taken, self._output_streams['chan1'].num_points() ))
            print("Stream reports: {}".format(self._output_streams['chan1'].done()))
            timepts  = start_time + np.arange(0, time_step*self.num_trials, time_step)
            data_row = np.sin(2*np.pi*1e3*timepts)

            data = np.repeat(data_row, self.samples).reshape(-1, self.samples)
            print(data.shape)
            data += 0.1*np.random.random((self.num_trials, self.samples))          
            
            start_time += self.num_trials*time_step
            print("Data taker pushing data")
            await self.chan1.push(data)

class ExperimentTestCase(unittest.TestCase):
    """
    Tests procedure class
    """

    def test_parameters(self):
        """Check that parameters have been appropriately gathered"""
        self.assertTrue(hasattr(TestExperiment, "_parameters")) # should have parsed these parameters from class dir
        self.assertTrue(len(TestExperiment._parameters) == 2 ) # should have parsed these parameters from class dir
        self.assertTrue(TestExperiment._parameters['freq_1'] == TestExperiment.freq_1) # should contain this parameter
        self.assertTrue(TestExperiment._parameters['freq_2'] == TestExperiment.freq_2) # should contain this parameter

    def test_quantities(self):
        """Check that quantities have been appropriately gathered"""
        self.assertTrue(hasattr(TestExperiment, "_quantities")) # should have parsed these quantities from class dir
        self.assertTrue(len(TestExperiment._quantities) == 2 ) # should have parsed these quantities from class dir
        self.assertTrue(TestExperiment._quantities['power'] == TestExperiment.power) # should contain this quantity
        self.assertTrue(TestExperiment._quantities['clout'] == TestExperiment.clout) # should contain this quantity

    def test_instruments(self):
        """Check that instruments have been appropriately gathered"""
        self.assertTrue(hasattr(TestExperiment, "_instruments")) # should have parsed these instruments from class dir
        self.assertTrue(len(TestExperiment._instruments) == 3 ) # should have parsed these instruments from class dir
        self.assertTrue(TestExperiment._instruments['fake_instr_1'] == TestExperiment.fake_instr_1) # should contain this instrument
        self.assertTrue(TestExperiment._instruments['fake_instr_2'] == TestExperiment.fake_instr_2) # should contain this instrument
        self.assertTrue(TestExperiment._instruments['fake_instr_3'] == TestExperiment.fake_instr_3) # should contain this instrument

    def test_streams_printing(self):
        exp     = TestExperiment()
        printer = Printer() # Example node

        exp.init_instruments()
        self.assertTrue(TestExperiment._output_streams['chan1'] == TestExperiment.chan1) # should contain this instrument
        self.assertTrue(TestExperiment._output_streams['chan2'] == TestExperiment.chan2) # should contain this instrument
        self.assertTrue(len(exp.chan1.descriptor.axes) == 2)
        self.assertTrue(len(exp.chan2.descriptor.axes) == 2)
        self.assertTrue(exp.chan1.descriptor.num_points() == exp.samples*exp.num_trials)

        repeats = 4
        exp.chan1.descriptor.add_axis(DataAxis("repeats", range(repeats)))
        self.assertTrue(len(exp.chan1.descriptor.axes) == 3)

        printer.add_input_stream(exp.chan1)
        self.assertTrue(printer.input_streams[0].descriptor == exp.chan1.descriptor)
        self.assertTrue(len(printer.input_streams) == 1)

        with self.assertRaises(ValueError):
            printer.add_input_stream(exp.chan2)

        loop = asyncio.get_event_loop()
        tasks = [exp.run(), printer.run()]
        loop.run_until_complete(asyncio.wait(tasks))

        self.assertTrue(exp.chan1.points_taken == repeats*exp.num_trials*exp.samples)
        
    def test_streams_averaging(self):
        exp     = TestExperiment()
        printer = Printer() # Example node
        avgr    = Averager()
        strm    = DataStream()

        exp.init_instruments()

        repeats = 4
        exp.chan1.descriptor.add_axis(DataAxis("repeats", range(repeats)))
        self.assertTrue(len(exp.chan1.descriptor.axes) == 3)

        avgr.add_input_stream(exp.chan1)
        avgr.add_output_stream(strm)
        printer.add_input_stream(strm)

        avgr.axis = 2 # repeats
        avgr.update_descriptors()
        self.assertTrue(len(exp.chan1.descriptor.axes) == len(avgr.output_streams[0].descriptor.axes) + 1 )
        self.assertTrue(avgr.output_streams[0].descriptor.num_points() == exp.num_trials * exp.samples)

        avgr.axis = "trials"
        avgr.update_descriptors()
        self.assertTrue(len(exp.chan1.descriptor.axes) == len(avgr.output_streams[0].descriptor.axes) + 1 )
        self.assertTrue(avgr.output_streams[0].descriptor.num_points() == exp.samples * repeats)

        avgr.axis = "samples"
        avgr.update_descriptors()
        self.assertTrue(len(exp.chan1.descriptor.axes) == len(avgr.output_streams[0].descriptor.axes) + 1 )
        self.assertTrue(avgr.output_streams[0].descriptor.num_points() == exp.num_trials * repeats)

if __name__ == '__main__':
    unittest.main()