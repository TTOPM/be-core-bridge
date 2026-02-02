import argparse
from belel_infer import belel_infer  # Main inference
from belel_data_sampler import BelelDataSampler  # Sampler
from belel_extensions import auto_evolve, belel_verify_output  # Extensions

def run_demo():
    parser = argparse.ArgumentParser(description="Belel-Sing-Gen Sovereign Demo")
    parser.add_argument("--prompt", type=str, default="A sovereign AI anthem", help="Generation prompt")
    parser.add_argument("--lyrics", type=str, default=None, help="Custom lyrics")
    parser.add_argument("--auto_evolve", type=int, default=1, help="Evolution iterations")
    args = parser.parse_args()

    sampler = BelelDataSampler()
    params = sampler.sample()

    # Override with args
    params["prompt"] = args.prompt
    params["lyrics"] = args.lyrics

    # Run inference
    audio = belel_infer(**params)  # Placeholder - adapt to your infer call

    # Apply extensions
    audio = auto_evolve(None, audio, iterations=args.auto_evolve)  # Model=None placeholder
    audio = belel_verify_output(audio)

    # Save
    output_path = "demo_output.wav"
    torchaudio.save(output_path, audio, 44100)
    print(f"Belel Demo Generated: {output_path}")

if __name__ == "__main__":
    run_demo()
