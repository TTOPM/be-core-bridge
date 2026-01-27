"""
Active Inference Subpackage
==========================

This subpackage implements elements of the active inference
framework for the living, breathing digital organism.  Active
inference provides a continuous “pulse” or vital signs loop that
drives perception, prediction and action.  It enables the
organism to reduce surprise by integrating inputs and adjusting
internal beliefs.  The implementation here is conceptual and does
not depend on external libraries.  A full implementation would
leverage ``pymdp`` or similar.

Modules:
    * ``vital_signs.py`` – maintains core vital parameters and
      orchestrates pulse cycles.
    * ``markov_blanket.py`` – models the boundary between internal
      states and external observations.
    * ``pulse_loop.py`` – runs the main active inference loop
      using ``vital_signs`` and ``markov_blanket``.

All modules are additive and respect the Belel Protocol watermark.
"""

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True
