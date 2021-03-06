# Copyright 2016 Raytheon BBN Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0

from __future__ import print_function, division
import time
import logging
# logging.basicConfig(format='%(levelname)s:\t%(message)s', level=logging.INFO)

import numpy as np
import scipy as sp
import pandas as pd

from auspex.instruments.kepco import BOP2020M
from auspex.instruments.stanford import SR830
from auspex.instruments.magnet import Electromagnet
from auspex.instruments.hall_probe import HallProbe
from auspex.sweep import Sweep
from auspex.experiment import FloatParameter, Quantity, Procedure

# import ipdb

class MeasureLockinVoltage(Procedure):
    set_field = FloatParameter(name="Set Field", unit="G")
    field     = Quantity(name="Field", unit="G")
    voltage   = Quantity(name="Magnitude", unit="V")

    bop       = BOP2020M("GPIB0::1::INSTR")
    lock      = SR830("GPIB0::9::INSTR")
    hp        = HallProbe("calibration/HallProbe.cal", lock.set_ao1, lock.get_ai1)
    mag       = Electromagnet('calibration/GMW.cal', hp.get_field, bop.set_current, bop.get_current)

    def init_instruments(self):
        self.tc_delay = self.lock.measure_delay()
        self.averages = 10

        def lockin_measure():
            time.sleep(self.tc_delay)
            vals = []
            for i in range(self.averages):
                vals.append(self.lock.r)
            return np.mean(vals)

        self.set_field.assign_method(self.mag.set_field)
        self.field.assign_method(self.mag.get_field)
        self.voltage.assign_method(lockin_measure)

        for param in self._parameters:
            self._parameters[param].push()

    def run(self):
        """This is run for each step in a sweep."""
        for param in self._parameters:
            self._parameters[param].push()
        for quant in self._quantities:
            self._quantities[quant].measure()
        logging.info("Field, Lockin Magnitude: {:f}, {:g}".format(self.field.value, self.voltage.value) )

    def shutdown_instruments(self):
        self.bop.current = 0.0

if __name__ == '__main__':

    proc = MeasureLockinVoltage()

    # Define a sweep over prarameters
    sw = Sweep(proc)
    values = np.append(np.arange(-800, -99, 10), np.arange(-100, -801, -10)).tolist()
    sw.add_parameter(proc.set_field, values)

    # Define a writer
    # sw.add_writer('data/FieldLoops.h5', 'SWS2129(2,0)G-(009,05)', 'MinorLoop-3.3K', proc.field, proc.voltage)

    # Define a plotter
    sw.add_plotter("Resistance Vs Field", proc.field, proc.voltage, color="firebrick", line_width=2)

    sw.run()
