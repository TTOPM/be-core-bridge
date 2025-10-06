
def to_phonemes(text, lang='en'): return text.lower().split()
def phoneme_ids(phones):
    vocab = {ch:i%64 for i,ch in enumerate(sorted(set(''.join(phones)), key=lambda x:x))}
    return [vocab.get(ch,0) for ch in ''.join(phones)]
