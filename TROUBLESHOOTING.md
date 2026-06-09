# Troubleshooting
## Kibble Repeatedly Fails to Start Then Gives Up
If you see repeated messages about uncaught exceptions before it gives up.  You should see the exception that was thrown.  Due to the extensive error handling, this should rarely occur; however if it does.  Refer to the exception to trace the location of the fault and follow standard Python debugging procedures to figure out the issue.

## Kibble Complains About No Connection To the Database
If the connection to the database fails, Kibble will continue to run, relying on the following local files: `device_types.json` and `devices.json`.  Ini the event that the database is down, Kibble will slow down, attempting to make repeated connections to the database.  Kibble will log the exact error message thrown.  It will likely be due to authentication failures or the database being down.  Follow standard network troubleshooting to debug the issue.

## Kibble Complains About Running Behind
This is likely due to the ratio of monitored devices to worker threads being too high.  Increase the number of worker threads using `--threads` or increase the scan period `--scan-period`.  If the issue only arises when device(s) are down, you can try the methods mentioned before, or you can try decreasing the timeout period `--device-timeout`.

## Kibble's Alerting Threshold is Too Sensitive
This is because your latency thresholds are too low.  Increase `--low-thresh`, `--medium-thresh`, and/or `--high-thresh` accordingly.

## Kibble Says A Device is Down When It Isn't
There are multiple reasons this could occur.  The most basic reason is because the monitoring device can't connect to the endpoint device.  If you are certain the device is reachable, the issue is likely due to the device timeout being too low.  Change `--device-timeout` accordingly.

## Kibble Isn't Adding a New Device Dynamically
Try restarting Kibble.  This will force a new database search for devices.

## Kibble Isn't Recognizing Device Changes
Try restarting Kibble.  This will force Kibble to update its device properties.

## Kibble Complains About Permissions
You may need to run the program as administrator/root
