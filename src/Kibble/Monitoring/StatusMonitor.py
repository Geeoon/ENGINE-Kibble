"""
Defines an interface for the StatusMonitor
"""

import threading
import ipaddress
from abc import ABC, abstractmethod

class StatusMonitor(ABC):
    """
    Base class that monitors that status of a computer
    """
    def __init__(self, endpoints: list[dict], timeout: int=10):
        """
        Initializes the status monitor
        
        :param endpoints: a list of dicts representing devices to be monitored,
                should contain 'id', 'hostname' or 'ip'
        :param timeout: the amount of time for a response before an endpoint is
                considered dead

        """
        self._timeout = timeout
        self._status_lock = threading.Lock()
        for endpoint in endpoints:
            if not endpoint['ip'] and not endpoint['hostname']:
                raise ValueError(f"Endpoint {endpoint[id]} does not have an IP or hostname")
            if endpoint['ip']:
                # checks if all are valid IP addresses
                # raises ValueError if an IP address is not correct
                ipaddress.ip_address(endpoint['ip'])
            self._status[endpoint['id']] = {
                "details": {
                    
                }
            }

    def add_endpoint(self, additional: list[dict]=[]) -> list[str]:
        """
        Adds additional endpoints to be monitored.  If an endpoint already
            exists, it will be overwritten
        
        :param endpoints: a list of IP addresses to monitor.  Should follow same rules as __init__

        :return: the updated list of endpoint IDs
        """
        with self._status_lock:
            for another in additional:
                self._status[another['id']] = another
            return list(self._status.keys())
    
    def remove_endpoint(self, removal: list[str]) -> list[str]:
        """
        Removes an endpoint from monitoring.  If an endpoint doesn't exist,
        it will be skipped.
        
        :param removal: list of ids to remove from monitoring

        :return: the updated list of endpoints
        """
        with self._status_lock:
            for id in removal:
                self._status.pop(id, None)
            return list(self._status.keys())

    def get_endpoints(self) -> list[str]:
        with self._status_lock:
            return list(self._status.keys())
    
    @abstractmethod
    async def update_status(self):
        """
        Updates the status of all of the endpoints
        """
        pass

    @abstractmethod
    def __str__(self):
        """
        Get the string representation of the protocol used for monitoring
        """
        pass

    def get_status(self) -> dict:
        """
        Retrieves a copy of the status of the endpoints since the last time they were checked.

        :return: a dictionary with endpoints as keys.  The value should be
                another dict with the key "alive" with True or False and the
                key "last_updated" with the value of the UNIX timestamp in
                milliseconds of when the entry was updated. If the endpoint
                has not been probed yet, the value of its key will be None.
                The rest of thefields can be any additional information
                depending on the implementation.
        """
        with self._status_lock:
            return self._status.copy()
