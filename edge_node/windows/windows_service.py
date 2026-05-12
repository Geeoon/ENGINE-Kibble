"""
Windows service wrapper for the Kibble telemetry collector.
"""

import sys
import threading
import servicemanager
import win32event
import win32service
import win32serviceutil


sys.path.insert(0, r"C:\Program Files\Kibble\edge_agent")
from telemetry_collector import run


class KibbleTelemetryService(win32serviceutil.ServiceFramework):
    """
    Windows service wrapper for the Kibble telemetry collector.
    """
    _svc_name_ = "KibbleTelemetry"
    _svc_display_name_ = "Kibble Edge Node Telemetry Collector"
    _svc_description_ = "Collects system telemetry for Kibble monitoring."

    def __init__(self, args):
        super().__init__(args)
        self._stop_event = threading.Event()

    def SvcStop(self):
        """
        Signals the collector to stop and reports the stop status.
        """
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._stop_event.set()

    def SvcDoRun(self):
        """
        Called by Windows when the service starts.
        """
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        run(self._stop_event)


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(KibbleTelemetryService)
