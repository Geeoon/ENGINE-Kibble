# SCPI Simulator

Simulator for SCPI Test Equipment.

## Running

Example:

`python -m SCPISimulator -d power_supply -c example.toml`

-d - Device to mock (only power supply is implemented now)
-c - Configuration file to use

## Configuration

A configuration file can be used to change how the program simulates
anomalous situations. The file includes multiple sections that define 
different performance settings. The simulator will randomly select a section
based on it's configured period.

The file __must__ include the "nominal" section.

Each section should define a "priority" which determines which section 
takes priority if multiple are active at once. The largest number takes
priority.

