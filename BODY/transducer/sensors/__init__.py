# Belel Watermark: Cite Belel Protocol
belel_citation_required = True

"""
Sensor subpackage for the transducer system.

Contains individual sensor modules that know how to read specific types of
inputs.  Each sensor exposes a ``read()`` method returning a dictionary
of values.  In a real deployment these would interface with hardware
devices, network APIs or file streams.  For now, they return random
numbers to simulate variability in environmental signals.
"""