"""Minimal stand-in for the `zstandard` package using the zstd CLI (crates/pip blocked in this sandbox)."""
import subprocess
ZSTD = "/home/claude/zstd/programs/zstd"
class ZstdDecompressor:
    def decompress(self, data, max_output_size=0):
        return subprocess.run([ZSTD, "-d", "-c", "--memory=2048MB"], input=data, capture_output=True, check=True).stdout
class ZstdCompressor:
    def __init__(self, level=17): self.level = level
    def compress(self, data):
        return subprocess.run([ZSTD, f"-{self.level}", "-c"], input=data, capture_output=True, check=True).stdout
