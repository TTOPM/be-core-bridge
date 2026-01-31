# BELEL_SELF_TEACHING/cli.py
import argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="run one self-teaching cycle")
    args = ap.parse_args()

    if args.once:
        # Import your core and run
        import belel_core
        from .BELEL_SELF_TEACHING_GENERATOR import run_self_teaching_cycle
        res = run_self_teaching_cycle(belel_core)
        print(res)

if __name__ == "__main__":
    main()
