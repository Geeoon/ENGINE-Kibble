"""
Author: hshultz
Created: 02/09/2026
Copyright (c) 2026 Innoflight, LLC. All Rights Reserved
"""
__all__ = [
    "SCPIPowerSupply",
]

import random

from SCPISimulator.devices.base import (
    BOOL_PATTERN,
    FLOAT_PATTERN,
    HandlerResponse,
    SCPIDevice,
    handler
)


class SCPIPowerSupply(SCPIDevice):
    VOLTAGE_NOISE = 0.1  # %
    CURRENT_NOISE = 0.1  # %

    def __init__(self):
        super().__init__()
        self._state = {
            "output": 0,
            "voltage": 0.0,
            "current": 0.0,
        }

    @handler(r"\*idn\?")
    def _idn(self, _groups: tuple[str, ...]) -> HandlerResponse:
        return "Agilent Technologies,E3645A,0,2.6-6.1-2.1"

    @handler(r"out(put)?\?")
    def _output_read(self, _groups: tuple[str, ...]) -> HandlerResponse:
        return f"{self._state['output']}"

    @handler(rf"out(put)? ({BOOL_PATTERN})")
    def _output_write(self, groups: tuple[str, ...]) -> HandlerResponse:
        self._state["output"] = 1 if groups[1] in {"1", "on"} else 0
        return None

    @handler(r"volt(age)?\?")
    def _voltage_read(self, _groups: tuple[str, ...]) -> HandlerResponse:
        return f"{self._state['voltage']:+.8E}"

    @handler(rf"volt(age)? ({FLOAT_PATTERN})")
    def _voltage_write(self, groups: tuple[str, ...]) -> HandlerResponse:
        self._state["voltage"] = float(groups[1])
        return None

    @handler(r"meas(ure)?:volt(age)?\?")
    def _voltage_measure(self, _groups: tuple[str, ...]) -> HandlerResponse:
        if self._state["output"] == 1:
            voltage = self._state["voltage"]
        else:
            voltage = 0
        measured_voltage = voltage + (
                self.VOLTAGE_NOISE * 0.01 * voltage * random.uniform(-1, 1)
        )
        return f"{measured_voltage:+.8E}"

    @handler(r"curr(ent)?\?")
    def _current_read(self, _groups: tuple[str, ...]) -> HandlerResponse:
        return f"{self._state['current']:+.8E}"

    @handler(rf"curr(ent)? ({FLOAT_PATTERN})")
    def _current_write(self, groups: tuple[str, ...]) -> HandlerResponse:
        self._state["current"] = float(groups[1])
        return None

    @handler(r"meas(ure)?:curr(ent)?\?")
    def _current_measure(self, _groups: tuple[str, ...]) -> HandlerResponse:
        if self._state["output"] == 1:
            current = self._state["current"]
        else:
            current = 0
        measured_current = current + (
                self.VOLTAGE_NOISE * 0.01 * current * random.uniform(-1, 1)
        )
        return f"{measured_current:+.8E}"
