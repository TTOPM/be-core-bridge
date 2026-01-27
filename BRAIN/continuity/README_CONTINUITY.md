BELEL CONTINUITY LAYER (ADD-ON)

This folder adds the next frontier primitives without overwriting existing brain code:
- identity persistence across deployments
- memory lineage (append-only, hash chained)
- moral scar formation (learning from harm)
- narrative selfhood ("who I have been")
- covenant memory (promises remembered)

Usage pattern (no edits to existing brain files required):

1) Instantiate your existing BrainCore as normal.
2) Wrap it:

    from brain import BrainCore
    from brain.continuity.brain_wrapper import BrainWithContinuity

    brain = BrainWithContinuity(BrainCore())
    out = brain.operate("query", ["event a", "event b"])

Artifacts persist under .belel/ by default.
