"""Synthetic output-contract fixture, not a real reportmaker."""
from pathlib import Path

if __name__ == "__main__":
    output = Path("/output")
    with (output / "report.md").open("x", encoding="utf-8") as stream:
        stream.write("# Sandbox fixture\n\nSynthetic test data, not a real report.\n")
    with (output / "READY").open("x", encoding="ascii") as stream:
        stream.write("ready\n")
