# Offline / Local-Only Operation

- The default adapters (Piper + faster-whisper) run entirely on your machine.
- To enforce **no egress**, deploy your Docker stack behind a firewall or set Docker's default network to none
  for production containers and explicitly whitelist internal services only.
- For Kubernetes, use NetworkPolicies to **deny egress** by default and allow only cluster-local DNS and storage.
- Logs contain no external URLs; watermarking & disclosure are ON by default.
