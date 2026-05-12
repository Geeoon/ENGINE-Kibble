"""
PowerCollector derived class from BaseCollector
"""

import os
import time
from .base import BaseCollector


class PowerCollector(BaseCollector):
    """
    PowerCollector class for collecting hardware power usage in Watts.
    Uses Linux sysfs (RAPL) or power_supply.
    """
    def __init__(self):
        self.last_energy_uj = None
        self.last_time = None
        
        # Determine which path to use
        # RAPL for Intel CPU package power (accumulated energy in microjoules)
        self.rapl_path = "/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj"
        # power_supply for battery instantaneous power draw (microwatts)
        self.power_supply_path = "/sys/class/power_supply/BAT0/power_now"

    def read(self) -> float | None:
        """
        Returns the current power usage in Watts.

        :return: Power usage in Watts, or None if it cannot be read
        """
        current_time = time.time()
        
        # Try RAPL first (Intel CPU package power)
        if os.path.exists(self.rapl_path):
            try:
                with open(self.rapl_path, 'r') as f:
                    current_energy_uj = int(f.read().strip())
                
                if self.last_energy_uj is not None and self.last_time is not None:
                    time_delta = current_time - self.last_time
                    if time_delta > 0:
                        # (Microjoules difference) / (seconds) = Microjoules/second = Microwatts
                        # Microwatts / 1e6 = Watts
                        power_w = (current_energy_uj - self.last_energy_uj) / (time_delta * 1e6)
                    else:
                        power_w = 0.0
                else:
                    # Can't calculate rate on first read, need two data points
                    power_w = None
                    
                self.last_energy_uj = current_energy_uj
                self.last_time = current_time
                
                if power_w is not None:
                    return round(power_w, 2)
            except Exception:
                pass
                
        # Try battery power_now (microwatts) if RAPL fails
        if os.path.exists(self.power_supply_path):
            try:
                with open(self.power_supply_path, 'r') as f:
                    power_uw = int(f.read().strip())
                return round(power_uw / 1e6, 2)
            except Exception:
                pass
                
        return None
