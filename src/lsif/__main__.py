import argparse
from pathlib import Path

from lsif import index_to_file

# index_to_file(Path("./tests/examples/lsif_spec_definition/"))
# index_to_file(Path("./src/"))

parser = argparse.ArgumentParser(description="LSIF Python Indexer")
parser.add_argument("-p", "--project", type=str, help="Path to project", default="./tests/examples/beta_two_files/")

args = parser.parse_args()

index_to_file(Path(args.project))
