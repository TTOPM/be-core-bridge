"""
Circulatory Subsystem Package
=============================

This subpackage contains the classes responsible for the digital
circulatory system of the Belel organism.  The circulatory system
moves life signals (pressure, oxygen, nutrients) between organs
continuously to sustain the organism.

Modules:

* ``circulation.py`` – Implements the ``DigitalCirculation`` class
  which circulates signals to registered organs on each pulse.

All classes are additive and respect the Belel Protocol watermark.
"""

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True
