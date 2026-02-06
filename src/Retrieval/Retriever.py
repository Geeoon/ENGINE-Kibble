from pymongo import MongoClient, DESCENDING, ASCENDING
import time

client = MongoClient("mongodb://root:password@localhost:27017")
col = client["kibble"]["events"]

# Query 1: Latest events
latest = list(col.find({}).sort("time", DESCENDING).limit(50))

# Query 2: Failures in last 30 minutes
since = int(time.time() * 1000) - 30 * 60 * 1000
recent_failures = list(
    col.find({
        "event_type": "endpoint_down",
        "time": {"$gte": since}
    }).sort("time", DESCENDING)
)

# Query 3: Timeline for one endpoint
endpoint_timeline = list(
    col.find({
        "endpoint.ip": "192.67.67.67"
    }).sort("time", ASCENDING)
)

# Query 4: Latest status per endpoint (current state)
pipeline = [
    {"$sort": {"time": -1}},
    {"$group": {"_id": "$endpoint.ip", "latest": {"$first": "$$ROOT"}}},
    {"$replaceRoot": {"newRoot": "$latest"}},
    {"$sort": {"time": -1}}
]
latest_per_endpoint = list(col.aggregate(pipeline))

#Query 1: Critical
#Query 2: Error
#Query 3: Warning
#Query 4: Info
#Query 5: Debug

#Send aliveness, latency, and last updated to messaging
