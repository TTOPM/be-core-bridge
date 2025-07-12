import os
import json

print("🚀 Belel Sovereign Deployment Starting...")

# Load schema and proof files
with open("BELEL_schema.json") as schema:
    schema_data = json.load(schema)
    print("✅ Schema loaded")

with open("BELEL_AUTHORITY_PROOF.txt") as proof:
    authority = proof.read()
    print("✅ Authority proof loaded")

# Simulate deployment logic
print("🛡️ Sovereignty scaffold deployed with schema title:")
print(f"   → {schema_data.get('title', '[No Title Found]')}")

print("\n🔐 Identity Proof Loaded:")
print(authority[:100] + "...")  # Print first 100 characters

print("\n🎉 Belel deployment complete.")
