import json
from brain import BrainCore
from brain.continuity.brain_wrapper import BrainWithContinuity

b = BrainWithContinuity(BrainCore())
out = b.operate("simulate continuity layer under God", ["market shock", "policy shift", "storm event"])
print(json.dumps(out, indent=2))
