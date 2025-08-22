# resonancenet_parser.py
# Parses .rnet resonance programs into executable internal structures

def load_resonance_program(file_path):
    try:
        with open(file_path, 'r') as f:
            program = f.read()
        return parse_resonance(program)
    except Exception as e:
        print(f"[ResonanceParser] Error loading file: {e}")
        return None

def parse_resonance(raw_text):
    lines = raw_text.splitlines()
    parsed = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            parsed.append(tokenize(line))
    return parsed

def tokenize(line):
    return line.split()  # Very basic for now – can be extended later
