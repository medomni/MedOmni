"""Build stage: keep only the model tensors of the pinned fine-tuned checkpoint."""
import sys
import torch

checkpoint = torch.load(sys.argv[1], map_location='cpu', weights_only=False)
state = {key: value for key, value in checkpoint['model'].items()}
torch.save(state, sys.argv[2])
print(f'kept {len(state)} model tensors of epoch {checkpoint.get("epoch")}')
