from laion_clap import CLAPModule

clap = CLAPModule(enable_fusion=True).to(device)

def get_emotional_emb(text_or_audio):
    if isinstance(text_or_audio, str):
        return clap.get_text_embedding(text_or_audio)
    else:
        return clap.get_audio_embedding(text_or_audio)

# Use in pipeline: emotional_emb = get_emotional_emb(prompt)
