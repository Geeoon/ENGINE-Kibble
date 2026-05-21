"""
Implements the SNMPMonitor
"""

import asyncio
import time
import socket
import logging
from concurrent.futures import ThreadPoolExecutor

from pysnmp.hlapi.v3arch.asyncio import *

from Kibble.Monitoring import StatusMonitor

OIDS = {
    "ifOperStatus":        "1.3.6.1.2.1.2.2.1.8",
    "ifInErrors":          "1.3.6.1.2.1.2.2.1.14",
    "ifOutErrors":         "1.3.6.1.2.1.2.2.1.20",
    "ifInDiscards":        "1.3.6.1.2.1.2.2.1.13",
    "ifOutDiscards":       "1.3.6.1.2.1.2.2.1.19",
    "ifHCInOctets":        "1.3.6.1.2.1.31.1.1.1.6",
    "ifHCOutOctets":       "1.3.6.1.2.1.31.1.1.1.10"
}

class SNMPMonitor(StatusMonitor):
    """
    Monitors the status of a network switch using SNMP, specifically the Interface Statistics MIB (RFC 2863) 
    """

    def __init__(self, endpoints: list[str]=[], timeout: int=10, workers: int=5, port: int=161, community: str='public'):
        """
        Initializes the SNMPMonitor
        
        :param endpoints: see StatusMonitor.__init__
        :param timeout: see StatusMonitor.__init__
        :param workers: the max number of threads for the thread pool
        :param port: the UDP port to use for SNMP requests
        """
        super().__init__(endpoints, timeout)
        self._executor = ThreadPoolExecutor(workers)
        self.maintainance_logger = logging.getLogger("Kibble_Maintainance")
        self.port = port
        self.engine = SnmpEngine()
    
    def __str__(self):
        return 'SNMP'
        
    async def update_status(self):
        with self._status_lock:
            targets = []
            for id, target in self._status.items():
                if target['details']['hostname']:  # prioritze using hostname
                    targets.append((id, target['details']['hostname']))
                else:
                    targets.append((id, target['details']['ip']))

            coroutines = [self._send_snmp_await_reply(target[1]) for target in targets]
            results = await asyncio.gather(*coroutines)

            for target, result in zip(targets, results):
                self._status[target[0]]['status'] = {
                    "alive": result[0],
                    "latency": result[1],
                    "last_updated": result[2],
                    "telemetry": results[3]
                }
    
    def _get_snmp_telemetry(self, target: str) -> dict | None:
        """
        :param target: the target IP address
        :return: the result from the SNMP request(s), or None if no response/error
        """
        try:
            return asyncio.run(asyncio.wait_for(
                self._snmp_walk_multiple(self.engine, target, self.community, OIDS),
                timeout=self._timeout,
            ))
        except:
            return None
    
    async def _snmp_walk_multiple(self, engine: SnmpEngine, target: UdpTransportTarget, community: str, oids: dict) -> dict | None:
        """
        Performs multiple SNMP walks on OIDs
        :param engine: the SnmpEngine object
        :param target: the SNMP target
        :param community: the community string
        :param oids: the OIDs to perform walks on, key is the ASCII name and value is the actual OID
        :return: dict of the OIDs and their corresponding indexes and values, or None if there was an error
        """
        res = {}
        for name, oid in oids.items():
            this_res = await self._snmp_walk(engine, target, community, oid)
            if not this_res:
                return None
            res[name] = this_res

    async def _snmp_walk(self, engine: SnmpEngine, target: UdpTransportTarget, community: str, oid: str) -> dict | None:
        """
        Performs an SNMP walk on an OID
        :param engine: the SnmpEngine object
        :param target: the SNMP target
        :param community: the community string
        :param oid: the OID to perform the walk on
        :return: dict of the indexes and values, or None if there was an error
        """
        res = {}
        async for errorIndiciation, errorStatus, errorIndex, varBinds in walk_cmd(
            engine,
            CommunityData(community, mpModel=1),
            target,
            ContextData(),
            ObjectType(ObjectIdentifier(oid)),
            lexigraphicalMode=False
        ):
            if errorIndiciation or errorStatus:
                return None
            for varBind in varBinds:
                oid_str = str(varBind[0])
                index = oid_str.split(".")[-1]
                res[index] = int(varBind[1])
        return res

    async def _send_request_await_reply(self, target: str) -> tuple[bool, int, int]:
        """
        Sends SNMP request(s) and waits for replies
        
        :param target: the target to send the SNMP requests
        :return: whether or not it's alive, the latency in milliseconds, the
                timestamp of when the reply was received in milliseconds (or
                when it timed out), and the response (if there is any)
        """
        # resolve hostname
        try:
            ip = socket.gethostbyname(target)
        except socket.gaierror:
            self.maintainance_logger.critical(f"Could not resolve the hostname for {target}")
            return (False, self._timeout * 1000, round(time.time() * 1000), None)
        
        loop = asyncio.get_event_loop()
        
        request_time = time.time()
        # NOTE: could be some overhead from the thread starting and ending
        response = await loop.run_in_executor(self._executor, lambda: self._get_snmp_telemetry(ip))
        response_time = time.time() 
        # timed out
        if not response:
            return (False, self._timeout * 1000, round(response_time * 1000), None)
        
        return (True, round((response_time - request_time) * 1000), round(response_time * 1000), response)

