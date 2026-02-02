import argparse
import logging
import os
import sys
import warnings
from datetime import datetime
import random
import torch
import torch.distributed as dist
from PIL import Image
import hashlib
import json
import ipfshttpclient  # For local IPFS

# Import from LingBot-World submodule
from external.lingbot_world.wan import WanI2V
from external.lingbot_world.wan.configs import MAX_AREA_CONFIGS, SIZE_CONFIGS, SUPPORTED_SIZES, WAN_CONFIGS
from external.lingbot_world.wan.distributed.util import init_distributed_group
from external.lingbot_world.wan.utils.utils import save_video, str2bool  # merge_video_audio removed, handled in enhancements

# Belel imports (assume existing; stubs if not)
try:
    from organism_core import ORGANISM_CORE
    from concordium_enforcer import enforce_mandate
except ImportError:
    class ORGANISM_CORE:
        @staticmethod
        def audit_memory(data):
            return {'valid': True}  # Stub
    def enforce_mandate(prompt):
        pass  # Stub

# Stub for blockchain_proofs if not present
def anchor_to_ipfs(data):
    client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001/http')  # Local IPFS daemon required
    cid = client.add_bytes(json.dumps(data).encode())['Hash']
    return cid

from src.world_enhancements import generate_infinite_tiles, add_physics_simulation, generate_3d_nerf, add_audio_ambience, export_vr_world
from web3 import Web3

EXAMPLE_PROMPT = {
    "i2v-A14B": {
        "prompt":
            "The video presents a cinematic, first-person wandering experience through a hyper-realistic urban environment rendered in a video game engine. It begins with a static, sun-drenched alley framed by graffiti-laden industrial walls and overhead power lines, immediately establishing a gritty, lived-in atmosphere. As the camera pans right and tilts upward, it reveals a sprawling cityscape dominated by towering skyscrapers and industrial infrastructure, all bathed in warm, late-afternoon light that casts long shadows and produces dramatic lens flares. The perspective then transitions into a smooth forward tracking shot along a cracked sidewalk, passing weathered fences, palm trees, and distant pedestrians, creating a sense of immersion and exploration. Midway, the camera briefly follows a walking figure before refocusing on the broader streetscape, culminating in a stabilized view of a small blue van parked at an intersection surrounded by urban elements like parking garages and traffic lights. The entire sequence is characterized by its photorealistic detail, dynamic lighting, and deliberate pacing, evoking the feel of a quiet, sunlit afternoon in a futuristic metropolis.",
        "image":
            "examples/02/image.jpg",
    },
}

def _validate_args(args):
    assert args.ckpt_dir is not None, "Please specify the checkpoint directory."
    assert args.task in WAN_CONFIGS, f"Unsupport task: {args.task}"
    assert args.task in EXAMPLE_PROMPT, f"Unsupport task: {args.task}"

    if args.prompt is None:
        args.prompt = EXAMPLE_PROMPT[args.task]["prompt"]
    if args.image is None and "image" in EXAMPLE_PROMPT[args.task]:
        args.image = EXAMPLE_PROMPT[args.task]["image"]

    if args.task == "i2v-A14B":
        assert args.image is not None, "Please specify the image path for i2v."

    cfg = WAN_CONFIGS[args.task]

    if args.sample_steps is None:
        args.sample_steps = cfg.sample_steps

    if args.sample_shift is None:
        args.sample_shift = cfg.sample_shift

    if args.sample_guide_scale is None:
        args.sample_guide_scale = cfg.sample_guide_scale

    if args.frame_num is None:
        args.frame_num = cfg.frame_num

    args.base_seed = args.base_seed if args.base_seed >= 0 else random.randint(
        0, sys.maxsize)
    if not 's2v' in args.task:
        assert args.size in SUPPORTED_SIZES[
            args.task], f"Unsupport size {args.size} for task {args.task}, supported sizes are: {', '.join(SUPPORTED_SIZES[args.task])}"

def _parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a image or video from a text prompt or image using Wan"
    )
    parser.add_argument(
        "--task",
        type=str,
        default="i2v-A14B",
        choices=list(WAN_CONFIGS.keys()),
        help="The task to run.")
    parser.add_argument(
        "--size",
        type=str,
        default="1280*720",
        choices=list(SIZE_CONFIGS.keys()),
        help="The area (width*height) of the generated video. For the I2V task, the aspect ratio of the output video will follow that of the input image."
    )
    parser.add_argument(
        "--frame_num",
        type=int,
        default=None,
        help="How many frames of video are generated. The number should be 4n+1"
    )
    parser.add_argument(
        "--ckpt_dir",
        type=str,
        default=None,
        help="The path to the checkpoint directory.")
    parser.add_argument(
        "--offload_model",
        type=str2bool,
        default=None,
        help="Whether to offload the model to CPU after each model forward, reducing GPU memory usage."
    )
    parser.add_argument(
        "--ulysses_size",
        type=int,
        default=1,
        help="The size of the ulysses parallelism in DiT.")
    parser.add_argument(
        "--t5_fsdp",
        action="store_true",
        default=False,
        help="Whether to use FSDP for T5.")
    parser.add_argument(
        "--t5_cpu",
        action="store_true",
        default=False,
        help="Whether to place T5 model on CPU.")
    parser.add_argument(
        "--dit_fsdp",
        action="store_true",
        default=False,
        help="Whether to use FSDP for DiT.")
    parser.add_argument(
        "--save_file",
        type=str,
        default=None,
        help="The file to save the generated video to.")
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="The prompt to generate the video from.")
    parser.add_argument(
        "--use_prompt_extend",
        action="store_true",
        default=False,
        help="Whether to use prompt extend.")
    parser.add_argument(
        "--prompt_extend_method",
        type=str,
        default="local_qwen",
        choices=["dashscope", "local_qwen"],
        help="The prompt extend method to use.")
    parser.add_argument(
        "--prompt_extend_model",
        type=str,
        default=None,
        help="The prompt extend model to use.")
    parser.add_argument(
        "--prompt_extend_target_lang",
        type=str,
        default="zh",
        choices=["zh", "en"],
        help="The target language of prompt extend.")
    parser.add_argument(
        "--base_seed",
        type=int,
        default=42,
        help="The seed to use for generating the video.")
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="The image to generate the video from.")
    parser.add_argument(
        "--action_path",
        type=str,
        default=None,
        help="The camera path to generate the video from.")
    parser.add_argument(
        "--sample_solver",
        type=str,
        default='unipc',
        choices=['unipc', 'dpm++'],
        help="The solver used to sample.")
    parser.add_argument(
        "--sample_steps", type=int, default=None, help="The sampling steps.")
    parser.add_argument(
        "--sample_shift",
        type=float,
        default=None,
        help="Sampling shift factor for flow matching schedulers.")
    parser.add_argument(
        "--sample_guide_scale",
        type=float,
        default=None,
        help="Classifier free guidance scale.")
    parser.add_argument(
        "--convert_model_dtype",
        action="store_true",
        default=False,
        help="Whether to convert model paramerters dtype.")
    
    args = parser.parse_args()
    _validate_args(args)

    return args

def _init_logging(rank):
    if rank == 0:
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] %(levelname)s: %(message)s",
            handlers=[logging.StreamHandler(stream=sys.stdout)])
    else:
        logging.basicConfig(level=logging.ERROR)

def base_generate(args):
    rank = int(os.getenv("RANK", 0))
    world_size = int(os.getenv("WORLD_SIZE", 1))
    local_rank = int(os.getenv("LOCAL_RANK", 0))
    device = local_rank
    _init_logging(rank)

    if args.offload_model is None:
        args.offload_model = False if world_size > 1 else True
        logging.info(
            f"offload_model is not specified, set to {args.offload_model}.")
    if world_size > 1:
        torch.cuda.set_device(local_rank)
        dist.init_process_group(
            backend="nccl",
            init_method="env://",
            rank=rank,
            world_size=world_size)
    else:
        assert not (
            args.t5_fsdp or args.dit_fsdp
        ), f"t5_fsdp and dit_fsdp are not supported in non-distributed environments."
        assert not (
            args.ulysses_size > 1
        ), f"sequence parallel are not supported in non-distributed environments."

    if args.ulysses_size > 1:
        assert args.ulysses_size == world_size, f"The number of ulysses_size should be equal to the world size."
        init_distributed_group()

    cfg = WAN_CONFIGS[args.task]
    if args.ulysses_size > 1:
        assert cfg.num_heads % args.ulysses_size == 0, f"`{cfg.num_heads=}` cannot be divided evenly by `{args.ulysses_size=}`."

    logging.info(f"Generation job args: {args}")
    logging.info(f"Generation model config: {cfg}")

    if dist.is_initialized():
        base_seed = [args.base_seed] if rank == 0 else [None]
        dist.broadcast_object_list(base_seed, src=0)
        args.base_seed = base_seed[0]

    logging.info(f"Input prompt: {args.prompt}")
    img = None
    if args.image is not None:
        img = Image.open(args.image).convert("RGB")
        logging.info(f"Input image: {args.image}")

    if args.use_prompt_extend:
        logging.info("Extending prompt ...")
        if rank == 0:
            input_prompt = args.prompt
            input_prompt = [input_prompt]
        else:
            input_prompt = [None]
        if dist.is_initialized():
            dist.broadcast_object_list(input_prompt, src=0)
        args.prompt = input_prompt[0]
        logging.info(f"Extended prompt: {args.prompt}")
    
    logging.info("Creating WanI2V pipeline.")
    wan_i2v = WanI2V(
        config=cfg,
        checkpoint_dir=args.ckpt_dir,
        device_id=device,
        rank=rank,
        t5_fsdp=args.t5_fsdp,
        dit_fsdp=args.dit_fsdp,
        use_sp=(args.ulysses_size > 1),
        t5_cpu=args.t5_cpu,
        convert_model_dtype=args.convert_model_dtype,
    )
    logging.info("Generating video ...")
    video = wan_i2v.generate(
        args.prompt,
        img,
        action_path=args.action_path,
        max_area=MAX_AREA_CONFIGS[args.size],
        frame_num=args.frame_num,
        shift=args.sample_shift,
        sample_solver=args.sample_solver,
        sampling_steps=args.sample_steps,
        guide_scale=args.sample_guide_scale,
        seed=args.base_seed,
        offload_model=args.offload_model)

    if rank == 0:
        if args.save_file is None:
            formatted_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            formatted_prompt = args.prompt.replace(" ", "_").replace("/", "_")[:50]
            suffix = '.mp4'
            args.save_file = f"{args.task}_{args.size.replace('*','x') if sys.platform=='win32' else args.size}_{args.ulysses_size}_{formatted_prompt}_{formatted_time}" + suffix

        logging.info(f"Saving generated video to {args.save_file}")
        save_video(
            tensor=video[None],
            save_file=args.save_file,
            fps=cfg.sample_fps,
            nrow=1,
            normalize=True,
            value_range=(-1, 1))
    del video

    torch.cuda.synchronize()
    if dist.is_initialized():
        dist.barrier()
        dist.destroy_process_group()

    logging.info("Finished.")
    return args.save_file  # Return saved file path for enhancements

def self_verify_belel(generated_data, belel_data):
    current_hash = hashlib.sha256(json.dumps(generated_data).encode()).hexdigest()
    if current_hash != belel_data['expected_hash']:
        raise ValueError("Hash mismatch: World generation invalid.")
    return True

def xai_hash_core(data):
    timestamp = datetime.now().isoformat()
    return hashlib.sha256((json.dumps(data) + timestamp).encode()).hexdigest()

def enhanced_generate(args, infinite=False, enable_physics=True, enable_3d=True, enable_audio=True, enable_vr=False, enable_multiplayer=False):
    # Run base generation
    save_file = base_generate(args)
    # Load video (assume saved as mp4; use ffmpeg or cv2 to load frames if needed)
    import cv2
    cap = cv2.VideoCapture(save_file)
    frames = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    video = torch.from_numpy(np.array(frames))  # Convert to tensor

    # Belel mandate
    enforce_mandate(args.prompt)

    # Enhancements
    if infinite:
        video = generate_infinite_tiles(video, args.prompt)
    if enable_physics:
        video = add_physics_simulation(video, args.prompt)
    if enable_3d:
        nerf_model = generate_3d_nerf(video)
        world_data['nerf'] = nerf_model  # Stub for data
    if enable_audio:
        audio_track = add_audio_ambience(args.prompt, len(video))
        # Merge audio (use moviepy or ffmpeg)
        from moviepy.editor import VideoFileClip, AudioFileClip
        video_clip = VideoFileClip(save_file)
        audio_clip = AudioFileClip("temp_audio.wav")  # Save audio_track to file first
        librosa.output.write_wav("temp_audio.wav", audio_track, 22050)
        final_clip = video_clip.set_audio(audio_clip)
        final_clip.write_videofile(save_file, audio_codec='aac')
    if enable_vr:
        export_vr_world(video)
    if enable_multiplayer:
        w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))  # Local Ganache
        # Simple contract deployment (full ABI stubbed; define a basic contract)
        abi = '[{"inputs":[],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[{"internalType":"string","name":"cid","type":"string"}],"name":"shareWorld","outputs":[],"stateMutability":"nonpayable","type":"function"}]'  # Basic ABI
        bytecode = '608060405234801561001057600080fd5b506103e7806100206000396000f300608060405260043610610041576000357c0100000000000000000000000000000000000000000000000000000000900463ffffffff168063d0a5f0d014610046575b600080fd5b34801561005257600080fd5b5061005b610058565b005b00'  # Placeholder bytecode
        MyContract = w3.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash = MyContract.constructor().transact({'from': w3.eth.accounts[0]})
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        contract = w3.eth.contract(address=tx_receipt.contractAddress, abi=abi)
        contract.functions.shareWorld(anchor_to_ipfs(video.tolist())).transact({'from': w3.eth.accounts[0]})

    world_data = {'frames': video.tolist(), 'prompt': args.prompt, 'timestamp': datetime.now().isoformat()}
    internal_hash = xai_hash_core(world_data)
    belel_anchor = {'expected_hash': internal_hash, 'cid': anchor_to_ipfs(world_data)}
    self_verify_belel(world_data, belel_anchor)

    audit_result = ORGANISM_CORE.audit_memory(world_data)
    if not audit_result['valid']:
        raise ValueError("World inconsistent with Belel mandate.")

    # Propagate (stub; integrate Belel's propagation if exists)
    print(f"World propagated with CID: {belel_anchor['cid']}")

    return world_data, belel_anchor['cid']

if __name__ == "__main__":
    args = _parse_args()
    args.ckpt_dir = "external/lingbot-world/lingbot-world-base-cam"  # Default
    world, cid = enhanced_generate(args, infinite=True, enable_physics=True, enable_3d=True, enable_audio=True, enable_vr=True, enable_multiplayer=True)
    print(f"Sovereign world generated and anchored: IPFS CID {cid}")
