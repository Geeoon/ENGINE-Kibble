"""
Implements the KibbleDaemon
"""


from flask import Flask, Response
from google.protobuf import json_format

from . import protocol_pb2
class KibbleDaemon:
    def __init__(self):
        self.app = Flask("Kibble Daemon")
        self.app.add_url_rule('/status', 'status', self._get_status, methods=['GET'])

    def _get_status(self) -> Response:
        res = protocol_pb2.StatusResponse()
        telmetry_entry = res.telemetry.add()
        telmetry_entry.name = 'test'
        telmetry_entry.value = 1.5
        return Response(telmetry_entry.SerializeToString(), 200)

    def start(self, port: int):
        """
        Starts the server that allows it to be monitored
        :param port: the port to run on
        """
        self.app.run(host='0.0.0.0', port=port)

