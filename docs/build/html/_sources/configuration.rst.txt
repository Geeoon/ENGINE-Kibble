Configuration Parameters
========================

The following parameters can be configured for the Kibble system.

MongoDB Parameters
------------------

``db_name``
    Name of the MongoDB database used by Kibble.

``host``
    MongoDB host address. Example: ``database.internal``

``port``
    MongoDB port number. Default: ``27017``

``user``
    Username for MongoDB authentication.

``passwd``
    Password for MongoDB authentication.

``update_frequency``
    Frequency, in seconds, for batched writes to MongoDB.

Email Alert Parameters
----------------------

``EMAIL_PASSWD``
    Environment variable containing the Gmail app password used for email alerts.

``smtp_server``
    SMTP server used for outbound mail. Current value: ``smtp.gmail.com``

``port``
    SMTP SSL port. Current value: ``465``

Logging Parameters
------------------

``EVENTS_COLLECTION``
    MongoDB collection name for time-series events.

``DEVICES_COLLECTION``
    MongoDB collection name for device metadata.

``DEVICE_TYPES_COLLECTION``
    MongoDB collection name for device-type metadata.