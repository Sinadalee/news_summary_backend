import click
from app.core.topk_precomputer import TopKPrecomputer
import json
from pathlib import Path

@click.command()
@click.option("--base-dir", default="data", help="Base directory for data files")
@click.option("--top-k", default=5, help="Number of top articles to select")
@click.option("--region-file", default="app/config/regions.json", help="Path to regions.json")
def main(base_dir, top_k, region_file):
    with open(region_file) as f:
        regions = json.load(f)

    precomputer = TopKPrecomputer(base_dir=base_dir, top_k=top_k)
    precomputer.precompute_top_k(regions=regions, top_k=top_k)

    print("Top-K precomputation complete.")

if __name__ == "__main__":
    main()