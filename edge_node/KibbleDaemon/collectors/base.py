"""
Metric collector base class
"""

from abc import ABC, abstractmethod


class BaseCollector(ABC):
    """
    Abstract class for metric collecting
    """

    def __init__(self):
        self.name = "Base"
    @abstractmethod
    def read(self) -> float | None:
        """
        Abstract method to read the metric value.

        :return: The metric value, or None if the metric cannot be read
        """
        pass
