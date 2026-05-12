#!/usr/bin/env python
import argparse

from batchgenerators.utilities.file_and_folder_operations import isfile, load_pickle, save_pickle


def main() -> None:
    parser = argparse.ArgumentParser(description="Clamp nnU-Net v1 plans batch size for U-MyoPS Stage2.")
    parser.add_argument("--plans", required=True, help="Path to nnUNet plans pickle.")
    parser.add_argument("--batch-size", required=True, type=int, help="Target batch size for stage 0.")
    args = parser.parse_args()

    if args.batch_size < 1:
        raise ValueError("--batch-size must be >= 1")
    if not isfile(args.plans):
        raise FileNotFoundError(args.plans)

    plans = load_pickle(args.plans)
    old_batch_size = plans["plans_per_stage"][0]["batch_size"]
    plans["plans_per_stage"][0]["batch_size"] = args.batch_size
    save_pickle(plans, args.plans)
    print(f"Updated {args.plans}: batch_size {old_batch_size} -> {args.batch_size}")


if __name__ == "__main__":
    main()
