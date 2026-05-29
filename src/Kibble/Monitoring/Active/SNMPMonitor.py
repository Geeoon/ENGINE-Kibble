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

WALK_OIDS = {
    "ifOperStatus":        "1.3.6.1.2.1.2.2.1.8",  # port status (up or down)
    "ifLastChange":        "1.3.6.1.2.1.2.2.1.9",  # last port status change
    "ifHighSpeed":         "1.3.6.1.2.1.31.1.1.1.15",  # port speed
    # "ifInErrors":          "1.3.6.1.2.1.2.2.1.14",
    # "ifOutErrors":         "1.3.6.1.2.1.2.2.1.20",
    # "ifInDiscards":        "1.3.6.1.2.1.2.2.1.13",
    # "ifOutDiscards":       "1.3.6.1.2.1.2.2.1.19",
    # "ifHCInOctets":        "1.3.6.1.2.1.31.1.1.1.6",
    # "ifHCOutOctets":       "1.3.6.1.2.1.31.1.1.1.10",
}

GET_OIDS = {
    "sysUpTime":           "1.3.6.1.2.1.1.3.0",  # switch uptime
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
        self.community = community
    
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

            coroutines = [self._send_request_await_reply(target[1]) for target in targets]
            results = await asyncio.gather(*coroutines)
            for target, result in zip(targets, results):
                self._status[target[0]]['status'] = {
                    "alive": result[0],
                    "latency": result[1],
                    "last_updated": result[2],
                    "telemetry": result[3]
                }
    
    def _get_snmp_telemetry(self, target: str) -> dict | None:
        """
        :param target: the target IP address
        :return: the result from the SNMP request(s), or None if no response/error
        """
        try:
            walk_res, walk_latency = asyncio.run(asyncio.wait_for(
                self._snmp_walk_multiple(target, self.community, WALK_OIDS),
                timeout=self._timeout,
            ))
            if walk_res is None:
                return None
            get_res, get_latency = asyncio.run(asyncio.wait_for(
                self._snmp_get_multiple(target, self.community, GET_OIDS),
                timeout=self._timeout
            ))
            if get_res is None:
                return None
            latency = (walk_latency * len(WALK_OIDS) + get_latency * len(GET_OIDS)) / (len(WALK_OIDS) + len(GET_OIDS))  # weighted average
            return walk_res | get_res | {'latency': latency}
        except:
            return None
        
    async def _snmp_get_multiple(self, target: str, community: str, oids: dict) -> dict | None:
        """
        Performs multiple SNMP gets on OIDs
        :param target: the SNMP target IP
        :param community: the community string
        :param oids: the OIDs to perform gets on, key is the ASCII name and the value is the actual OID
        :return: dict of the OIDs' names and their corresponding value, or None if there was an error
        """
        res = {}
        cumulative = 0
        for name, oid in oids.items():
            start_time = time.time()
            this_res = await self._snmp_get(target, community, oid)
            end_time = time.time()
            cumulative += end_time - start_time
            if not this_res:
                return None
            res[name] = this_res
        return res, cumulative / len(oids)
    
    async def _snmp_walk_multiple(self, target: str, community: str, oids: dict) -> dict | None:
        """
        Performs multiple SNMP walks on OIDs
        :param target: the SNMP target IP
        :param community: the community string
        :param oids: the OIDs to perform walks on, key is the ASCII name and value is the actual OID
        :return: dict of the OIDs' names and their corresponding indexes and values, or None if there was an error
        """
        res = {}
        cumulative = 0
        for name, oid in oids.items():
            start_time = time.time()
            this_res = await self._snmp_walk(target, community, oid)
            end_time = time.time()
            cumulative += end_time - start_time
            if not this_res:
                return None
            res[name] = this_res
        return res, cumulative / len(oids)
    
    async def _snmp_walk(self, target: str, community: str, oid: str) -> dict | None:
        """
        Performs an SNMP walk on an OID
        :param target: the SNMP target IP
        :param community: the community string
        :param oid: the OID to perform the walk on
        :return: dict of the indexes and values, or None if there was an error
        """
        engine = SnmpEngine()
        sock = await UdpTransportTarget.create((target, self.port))
        res = {}
        async for errorIndiciation, errorStatus, errorIndex, varBinds in walk_cmd(
            engine,
            CommunityData(community, mpModel=1),
            sock,
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
            lexicographicMode=False
        ):
            if errorIndiciation or errorStatus:
                return None
            for varBind in varBinds:
                oid_str = str(varBind[0])
                index = oid_str.split(".")[-1]
                res[index] = int(varBind[1])
        return res
    
    async def _snmp_get(self, target: str, community: str, oid: str) -> int | None:
        """
        Performs an SNMP get on an OID
        :param target: the SNMP target IP
        :param community: the community string
        :param oid: the OID to perform the get on
        :return: the result of the SNMP get
        """
        engine = SnmpEngine()
        sock = await UdpTransportTarget.create((target, self.port))
        errorIndication, errorStatus, errorIndex, varBinds = await get_cmd(
            engine,
            CommunityData(community, mpModel=1),
            sock,
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
        )
        if errorIndication or errorStatus:
            return None
        return int(varBinds[0][1])


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
        
        # NOTE: could be some overhead from the thread starting and ending
        response = await loop.run_in_executor(self._executor, lambda: self._get_snmp_telemetry(ip))
        response_time = time.time() 
        # timed out
        if not response:
            return (False, self._timeout * 1000, round(response_time * 1000), None)
        
        request_time = response.pop('latency', None)
        return (True, round(request_time * 1000), round(response_time * 1000), response)

