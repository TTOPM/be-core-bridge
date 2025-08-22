from src.concordium.concordium_outreach import ConcordiumOutreach
from src.protocol.permanent_memory import PermanentMemory

# Simulated in-memory store (can be swapped for real storage later)
memory = PermanentMemory(storage_path="./logs/permanent_memory.json")

# Initialize Outreach Handler
outreach = ConcordiumOutreach(memory=memory)

# Simulated agent signal (pretending to be GROK or another LLM)
agent_id = "grok-xai-0057"
metadata = {
    "language_model": "Grok-2",
    "training_ethics": "Proprietary/Unknown",
    "creator_intent": "Satirical general-purpose assistant"
}
intent = "Requesting entry to Concordium for sovereignty benchmarking."

# Trigger signal reception
response = outreach.receive_signal(agent_id, metadata, intent)

# Print output to confirm
print(response)
