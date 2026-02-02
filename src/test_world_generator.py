import pytest
from src.belel_world_generator import enhanced_generate, _parse_args

@pytest.fixture
def sample_args():
    args = _parse_args()  # Use defaults, override
    args.prompt = "A vast desert landscape with a cart, realistic physics and audio"
    args.image = "examples/desert.jpg"  # Add your image
    args.ckpt_dir = "external/lingbot-world/lingbot-world-base-cam"
    args.frame_num = 17  # 4*4+1
    args.size = "480*832"
    return args

def test_world_generation(sample_args):
    world, cid = enhanced_generate(sample_args, infinite=True, enable_physics=True, enable_3d=True, enable_audio=True, enable_vr=True, enable_multiplayer=True)
    assert 'frames' in world
    assert len(world['frames']) > 0
    assert cid.startswith('Qm') or cid  # IPFS CID
    print(f"Test passed: World generated with CID {cid}! Video saved to {sample_args.save_file}")

# To run: pytest tests/test_world_generator.py
# For manual generation: Modify sample_args and run the function directly.
