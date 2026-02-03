import torch.optim as optim
from torch.utils.data import DataLoader
# Load extended datasets (SingStyle131, etc.)
optimizer = optim.AdamW(heart_model.parameters(), lr=5e-6)
for epoch in range(15):
    for batch in dataloader:  # Enhanced with emotional labels
        loss = heart_model(**batch).loss
        loss.backward()
        optimizer.step()
torch.save(heart_model.state_dict(), "ultra_plus_heartmula.pth")
