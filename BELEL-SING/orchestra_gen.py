from stable_audio_tools.inference.generation import generate_diffusion_cond
from stable_audio_tools import get_pretrained_model

model, config = get_pretrained_model("stabilityai/stable-audio-open-1.0")

def generate_orchestra(prompt, duration=30):
    conditioning = [{"prompt": prompt, "seconds_start": 0, "seconds_total": duration}]
    audio = generate_diffusion_cond(model, steps=150, cfg_scale=8, conditioning=conditioning, sample_size=config.sample_rate * duration)
    sf.write("orchestra.wav", audio[0].cpu().numpy(), config.sample_rate)
    return "orchestra.wav"

# Call in main: generate_orchestra("Full orchestra with strings, brass, percussion for epic ballad")
