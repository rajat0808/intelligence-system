import argparse
import json
import sys

from app.ml.model_io import load_model


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect the latest ML model metadata.")
    parser.add_argument("--model-path", dest="model_path", default=None)
    parser.add_argument("--metadata-path", dest="metadata_path", default=None)
    args = parser.parse_args(argv)

    model, metadata = load_model(args.model_path, args.metadata_path)
    if model is None:
        raise SystemExit("No trained model found. Run retrain_model.py first.")

    if not metadata:
        print("Model loaded, but no metadata file found.")
        return

    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])
