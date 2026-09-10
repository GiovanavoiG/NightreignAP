"""Decrypt + decompress raw slices produced by the _ap_extract PowerShell scripts.
Usage: PYTHONPATH=<enemy-rando> python3 nr_extract.py <bhd_dir> <raw_dir> <out_dir>"""
import sys, os, glob, struct, subprocess
import data_archive as da
OODLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oodle_dec")
ZSTD = "/home/claude/zstd/programs/zstd"

def dcx_decompress(dcx: bytes) -> bytes:
    if dcx[:4] != b"DCX\0":
        return dcx  # not compressed
    method = dcx[0x28:0x2C]
    unc = struct.unpack_from(">I", dcx, 0x1C)[0]; comp = struct.unpack_from(">I", dcx, 0x20)[0]
    i = dcx.find(b"DCA\0"); start = i + struct.unpack_from(">I", dcx, i + 4)[0]
    payload = dcx[start:start + comp]
    if method == b"ZSTD":
        return subprocess.run([ZSTD, "-d", "-c"], input=payload, capture_output=True, check=True).stdout
    if method == b"KRAK":
        open("/tmp/_in.bin", "wb").write(payload)
        r = subprocess.run([OODLE, "/tmp/_in.bin", "/tmp/_out.bin", str(unc)], capture_output=True, text=True)
        if r.returncode: raise RuntimeError(r.stderr)
        return open("/tmp/_out.bin", "rb").read()
    raise ValueError(method)

def main(bhd_dir, raw_dir, out_dir):
    a = da.DataArchive(bhd_dir)
    os.makedirs(out_dir, exist_ok=True)
    for raw in sorted(glob.glob(os.path.join(raw_dir, "*.raw"))):
        base = os.path.basename(raw)[:-4]; path = "/" + base.replace("__", "/")
        hit = a._index.get(da.path_hash(path))
        data = bytearray(open(raw, "rb").read())
        if hit and hit[1].aes_key:
            da._aes_decrypt_ranges(data, hit[1].aes_key, hit[1].aes_ranges)
        try:
            out = dcx_decompress(bytes(data))
            open(os.path.join(out_dir, base.replace(".dcx", "")), "wb").write(out)
            print("ok", base, len(out), out[:4])
        except Exception as e:
            print("FAIL", base, e)

if __name__ == "__main__":
    main(*sys.argv[1:4])
