"""
Implements the KibbleDaemon
"""
from flask import Flask, Response
from waitress import serve
from . import protocol_pb2

from KibbleDaemon.collectors import BaseCollector, CpuCollector, DiskCollector, MemoryCollector, NetworkIoCollector, TemperatureCollector, PowerCollector

class KibbleDaemon:
    def __init__(self):
        self.app = Flask("Kibble Daemon")
        self.app.add_url_rule('/status', 'status', self._get_status, methods=['GET'])
        self.collectors: list[BaseCollector] = [CpuCollector(), DiskCollector(), MemoryCollector(), NetworkIoCollector(), TemperatureCollector(), PowerCollector()]

    def _get_status(self) -> Response:
        res = protocol_pb2.StatusResponse()
        for collector in self.collectors:
            val = collector.read()
            if val is None:  # skip, cannot be read
                continue
            entry = res.telemetry.add()
            entry.name = collector.name
            entry.value = val
        return Response(res.SerializeToString(), 200, content_type="application/x-protobuf")

    def start(self, port: int):
        """
        Starts the server that allows it to be monitored
        :param port: the port to run on
        """
        serve(self.app, host='0.0.0.0', port=port)

