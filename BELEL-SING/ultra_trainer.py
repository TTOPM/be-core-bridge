import torch.optim as optim
from torch.utils.data import DataLoader
# Assume dataset loader for SingStyle111/Opencpop
optimizer = optim.Adam(heart_model.parameters(), lr=1e-5)
for epoch in range(10):
    for batch in dataloader:
        loss = heart_model(**batch).loss
        loss.backward()
        optimizer.step()
torch.save(heart_model.state_dict(), "fine_tuned_heartmula.pth")
