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
    def __init__(self, endpoints: list[str], timeout: int=10):
        """
        Initializes the status monitor
        
        :param endpoints: a list of IP addresses to monitor
        :type endpoints: list[str]
        :param timeout: the amount of time for a response before an endpoint is
                considered dead
        :type timeout: int
        """
        # checks if all are valid IP addresses
        # raises ValueError if an IP address is not correct
        [ipaddress.ip_address(ip) for ip in endpoints]
        self._timeout = timeout
        self._status_lock = threading.Lock()
        self._status = dict.fromkeys(endpoints)

    def add_endpoint(self, additional: list[str]=[]) -> list[str]:
        """
        Adds additional endpoints to be monitored.  If an endpoint already
            exists, it's previous status will be destroyed.
        
        :param endpoints: a list of IP addresses to monitor
        :type endpoints: list[str]

        :return: the updated list of endpoints
        :rtype: list[str]
        """
        with self._status_lock:
            self._status |= dict.fromkeys(additional)
            return list(self._status.keys())
    
    def remove_endpoint(self, removal: list[str]) -> list[str]:
        """
        Removes an endpoint from monitoring.  If an endpoint doesn't exist,
        it will be skipped.
        
        :param self: Description
        :param removal: Description
        :type removal: list[str]

        :return: the updated list of endpoints
        :rtype: list[str]
        """
        with self._status_lock:
            for key in removal:
                self._status.pop(key, None)
            return list(self._status.keys())
    
    @abstractmethod
    async def update_status(self):
        """
        Updates the status of all of the endpoints
        """
        pass

    def get_status(self) -> dict:
        """
        Retrieves the status of the endpoints since the last time they were checked.

        :return: a dictionary with endpoints as keys.  The value should be
                another dict with the key "alive" with True or False and the
                key "last_updated" with the value of the UNIX timestamp in
                milliseconds of when the entry was updated. If the endpoint
                has not been probed yet, the value of its key will be None.
                The rest of thefields can be any additional information
                depending on the implementation.
        :rtype: dict
        """
        with self._status_lock:
            return self._status
