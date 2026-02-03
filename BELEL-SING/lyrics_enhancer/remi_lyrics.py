from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("heartmula/HeartMuLa-7B-finetuned-remi")  # Assume fine-tune on rhyme datasets
tokenizer = AutoTokenizer.from_pretrained("heartmula/HeartMuLa-7B-finetuned-remi")

def generate_lyrics(prompt):
    inputs = tokenizer(prompt + " [ReMi: emotional rhyme]", return_tensors="pt").to(device)
    lyrics = model.generate(**inputs, max_new_tokens=256)
    return tokenizer.decode(lyrics[0])

# Integrate: In prompt_to_song, use generate_lyrics(prompt) before structure.
