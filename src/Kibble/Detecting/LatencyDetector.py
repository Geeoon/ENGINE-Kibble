"""
LatencyDetector class
"""

from Kibble.Logging import LogLevel
from Kibble.Detecting import Detector

class LatencyDetector(Detector):
    """
    Simple latency detector that logs when an endpoint is taking longer than it should
    """
    def __init__(self, depth: int=2, warn_thresh: int = 500, error_thresh: int = 2000):
        """
        Initialize the LatencyDetector.  Requires 'latency' key in logs
        
        :param depth: the number of points to store.  Does not need to be
                greater than 2 for this simple detector
        :type depth: int
        :param warn_thresh: the latency threshold for a warning in ms
        :type warn_thresh: int
        :param error_thresh: the latency threshold for an error in ms
        :type error_thresh: int
        """
        assert depth > 1, "depth must be greater than 1"
        self.latency_history: dict = {}
        self.depth = depth
        self.warn_thresh = warn_thresh
        self.error_thresh = error_thresh

    def get_level(self, endpoint: str, log: dict) -> LogLevel:
        """
        Determines the severity of a log.  Shall be called every time a new log
        is generated.
        
        :param log: the log to check
        :type log: dict
        :return: the severity of the log
        :rtype: LogLevel
        """
        level = LogLevel.INFO
        latency = log['latency']
        if not log['alive']:
            level = LogLevel.CRITICAL  # device is down
        elif latency > self.error_thresh:
            level = LogLevel.ERROR
        elif latency > self.warn_thresh:
            level = LogLevel.WARNING
        
        self._add_to_history(endpoint, latency, level)
        return level

    def _add_to_history(self, endpoint, latency, level):
        if not endpoint in self.latency_history:
            # new endpoint, add a list
            self.latency_history[endpoint] = []

        # if latency is full, pop the elements
        overfill = len(self.latency_history[endpoint]) - self.depth
        self.latency_history[endpoint] = self.latency_history[endpoint][overfill:]

        # add latest to list
        self.latency_history[endpoint].append({ 'latency': latency, 'level': level })

    def get_alerts(self) -> dict:
        """
        Gets a list of new alerts that should be published.  Shall be called
        once after the log for each new endpoint is added.
        
        :return: a dictionary of endpoitns corresponding to new alerts
        :rtype: dict
        """

        # if severity level has increased since the last one, do an alert
        out = {}
        for endpoint in self.latency_history.keys():
            history = self.latency_history[endpoint]
            if len(history) == 0:
                # skip it, no history
                continue
            elif len(history) == 1:
                # there's only one, check if it's alert-worthy
                if history[0]['level'] > LogLevel.INFO:
                    out[endpoint] = { 'level': history[0]['level'] }
                continue
            
            # if the newest log is of greater severity
            if history[-1]['level'] > history[-2]['level']:
                out[endpoint] = { 'level': history[-1]['level']}
        
        return out
