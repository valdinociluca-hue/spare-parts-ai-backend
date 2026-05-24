"""
scripts/embed_catalogue.py — Catalogue embedding script for RAG.

One-time (and periodic re-run) script that:
  1. Loads spare parts catalogue data from a source (CSV, Excel, DB)
  2. Chunks each entry into embeddable text (part number + description + metadata)
  3. Calls the embedder to generate dense vectors
  4. Upserts vectors + metadata into the vector store

Run this script:
  - Once before deploying RAG functionality
  - Whenever the catalogue is updated (new parts, updated descriptions)
  - After changing the embedding model (vectors are model-specific)

Usage:
    python scripts/embed_catalogue.py --source data/catalogue.csv
    python scripts/embed_catalogue.py --source data/catalogue.csv --batch-size 100

TODO:
  - Implement catalogue loading (CSV, Excel, or DB query)
  - Implement chunking strategy (one chunk per part? description chunking?)
  - Implement batch embedding with progress bar (tqdm)
  - Add --dry-run flag (count items without writing)
  - Add --overwrite flag (re-embed all vs. skip existing)
"""

import argparse


def main():
    parser = argparse.ArgumentParser(description="Embed spare parts catalogue into vector store")
    parser.add_argument("--source", required=True, help="Path to catalogue file (CSV/Excel)")
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()

    # TODO: load catalogue, chunk, embed, upsert to vector store
    print(f"TODO: embed catalogue from {args.source}")


if __name__ == "__main__":
    main()
