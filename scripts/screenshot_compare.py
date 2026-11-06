#!/usr/bin/env python3
"""Optional screenshot comparison using ImageMagick; reports NOT RUN when unavailable."""
from pathlib import Path
import argparse, json, shutil, subprocess, sys

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("runtime", type=Path)
    parser.add_argument("--diff", type=Path, help="Output diff image path")
    parser.add_argument("--metric", choices=("AE", "RMSE", "MAE", "PSNR", "FUZZ"), default="RMSE")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = {"reference": str(args.reference), "runtime": str(args.runtime), "status": "NOT RUN",
              "tool": "ImageMagick compare", "metric": args.metric}
    if not args.reference.is_file() or not args.runtime.is_file():
        result["reason"] = "Reference or runtime screenshot file is missing"
        code = 2
    elif not shutil.which("compare"):
        result["reason"] = "ImageMagick 'compare' command is not installed; no comparison performed"
        code = 3
    else:
        diff = args.diff or args.runtime.with_name(args.runtime.stem + "_diff.png")
        diff.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["compare", "-metric", args.metric, str(args.reference), str(args.runtime), str(diff)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        # ImageMagick may return 1 when images differ; that is not an execution error.
        metric_text = (proc.stderr or proc.stdout).strip()
        result.update({"status": "COMPARED" if proc.returncode in (0, 1) else "ERROR",
                       "diff_path": str(diff) if diff.exists() else None,
                       "metric_value": metric_text,
                       "exit_code": proc.returncode,
                       "note": "Metric is not a quality score. Review the diff manually; compare only matching dimensions/states."})
        code = 0 if proc.returncode in (0, 1) else 4
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for k, v in result.items(): print(f"{k}: {v}")
        if result["status"] == "NOT RUN": print("No visual pass/fail conclusion is available.")
    return code

if __name__ == "__main__":
    sys.exit(main())
