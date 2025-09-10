import config  # initialize logging configuration
from core.curriculum import generate_curriculum
import argparse
import asyncio
import logging
import json  # added for fallback parsing

def _cli():
    parser = argparse.ArgumentParser(
        description="Generate SAT curriculum via multi-agent pipeline."
    )
    parser.add_argument("topic", help="Topic name (quoted)")
    args = parser.parse_args()

    logging.info(f"⚙️  Generating curriculum for: {args.topic}")
    cur = asyncio.run(generate_curriculum(args.topic))
    if cur:
        logging.info("Generated files:")
        for lid, u in cur.items():
            logging.info(f"{lid}:")
            logging.info(f"  Doc  → {u['doc']}")
            # Ensure 'sheets' is always a dict for iteration
            sheets = u['sheets']
            if isinstance(sheets, str):
                try:
                    sheets = json.loads(sheets)
                except json.JSONDecodeError:
                    sheets = {"all": sheets}
            for diff, url in sheets.items():
                logging.info(f"  {diff.title()} MCQs → {url}")
    else:
        logging.error("No curriculum produced – check logs for issues.")

if __name__ == "__main__":
    _cli()
