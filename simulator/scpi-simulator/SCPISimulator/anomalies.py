"""
Author: hshultz
Created: 02/09/2026
Copyright (c) 2026 Innoflight, LLC. All Rights Reserved
"""
__all__ = [
    "AnomalyManager",
]

import logging
import random
import time
from dataclasses import dataclass

from SCPISimulator.utils.data import clamp


@dataclass(kw_only=True)
class OperationModeSettings:

    def __hash__(self):
        return super().__hash__()

    # Priority if multiple modes are enabled at once
    priority: int = 0

    # Misc boolean settings
    # Stop sending responses
    no_response: bool = False
    # Drop all client connections
    drop_clients: bool = False

    # Latency settings
    latency_min: float = 0.1
    latency_max: float = 0.1
    latency_mean: float = 0.1
    latency_stddev: float = 0.01

    @property
    def latency(self) -> float:
        return clamp(
            random.gauss(self.latency_mean, self.latency_stddev),
            self.latency_min,
            self.latency_max
        )

    # Period settings (how often to enable the mode)
    period_min: float = 10 * 60
    period_max: float = 10 * 60
    period_mean: float = 10 * 60
    period_stddev: float = 0.01

    @property
    def period(self) -> float:
        return clamp(
            random.gauss(self.period_mean, self.period_stddev),
            self.period_min,
            self.period_max
        )

    # Duration settings (how long to enable the mode)
    duration_min: float = 10 * 60
    duration_max: float = 10 * 60
    duration_mean: float = 10 * 60
    duration_stddev: float = 0.01

    @property
    def duration(self) -> float:
        return clamp(
            random.gauss(self.duration_mean, self.duration_stddev),
            self.duration_min,
            self.duration_max
        )


class AnomalyManager:

    def __init__(self, config: dict):
        self._logger = logging.getLogger(self.__class__.__name__)

        # Build dictionary of mode settings
        self._modes = {
            k: OperationModeSettings(**v)
            for k, v in config.items()
        }
        # Nominal mode is always active
        self._active_modes: set[OperationModeSettings] = {
            self._modes["nominal"]
        }

        # Set initial activation/deactivation times for each node
        now = time.time()
        self._next_activate_times = {}
        self._next_deactivate_times = {}
        for k, v in self._modes.items():
            activation = now + v.period
            deactivation = activation + v.duration
            self._next_activate_times[k] = activation
            self._next_deactivate_times[k] = deactivation

    @property
    def settings(self) -> OperationModeSettings:
        # Sort active modes by priority, return highest
        return sorted(
            list(self._active_modes),
            key=lambda x: x.priority,
            reverse=True
        )[0]

    def update(self) -> None:
        now = time.time()

        for name, mode in self._modes.items():
            # Skip "nominal", always active
            if name == "nominal":
                continue
            # Check if it's time to activate this mode
            if now >= self._next_activate_times[name]:
                self._logger.info("Activating mode: '%s'", name)
                self._active_modes.add(mode)
                # Set next activation time
                self._next_activate_times[name] = (
                    self._next_deactivate_times[name] + mode.period
                )

            # Check if it's time to deactivate this mode
            if now >= self._next_deactivate_times[name]:
                self._logger.info("Deactivating mode: '%s'", name)
                self._active_modes.remove(mode)
                # Set next deactivation time
                self._next_deactivate_times[name] = (
                    self._next_activate_times[name] + mode.duration
                )


