from transformers import pipeline
import torch

clap_model = pipeline("audio-classification", model="laion/clap-htsat-unfused")  # Brain-like reps

def add_semantic_condition(audio_path, prompt_embeds):
    clap_out = clap_model(audio_path)  # Semantic scores
    semantic_vec = torch.tensor([out['score'] for out in clap_out])
    return torch.cat([prompt_embeds, semantic_vec.unsqueeze(0)], dim=1)  # Condition models

# In main: inputs_embeds = add_semantic_condition("polished_inst.wav", melody_embeds)
