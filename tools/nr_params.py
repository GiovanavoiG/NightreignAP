"""
Dump Elden Ring: Nightreign params from regulation.bin to CSV, using the field layouts from
vswarte/fromsoftware-rs (crates/nightreign/src/param.rs).

Usage:
  python tools/nr_params.py --regulation "<Game>/regulation.bin" --param-rs <fromsoftware-rs>/crates/nightreign/src/param.rs \
      --out research/params [--only EquipParamGoods NightBossMenuParam ...]

Requires the `regulation_io` module from 4laric/nightreign-enemy-rando on PYTHONPATH (AES key + DCX/BND4 handling)
and either the `zstandard` package or a stand-in that shells out to the zstd CLI.
"""
import argparse
import csv
import os
import re
import struct
import sys

TYPE_FMT = {"u8": "B", "i8": "b", "u16": "H", "i16": "h", "u32": "I", "i32": "i", "f32": "f", "u64": "Q", "i64": "q"}


def parse_param_rs(path):
    """Return {STRUCT_NAME: [(field, fmt, size), ...]} from the generated Rust file."""
    src = open(path, encoding="utf-8").read()
    structs = {}
    for m in re.finditer(r"pub struct (\w+) \{(.*?)\n\}", src, re.S):
        name, body = m.group(1), m.group(2)
        fields = []
        for line in body.splitlines():
            line = line.strip().rstrip(",")
            if not line or line.startswith("//"):
                continue
            fm = re.match(r"(?:pub )?(\w+): (.+)", line)
            if not fm:
                continue
            fname, ftype = fm.group(1), fm.group(2).strip()
            am = re.match(r"\[u8; (\d+)\]", ftype)
            if am:
                n = int(am.group(1))
                fields.append((fname, f"{n}s", n))
            elif ftype in TYPE_FMT:
                fields.append((fname, TYPE_FMT[ftype], struct.calcsize("<" + TYPE_FMT[ftype])))
            else:
                fields = None
                break
        if fields:
            structs[name] = fields
    return structs


def read_param(param: bytes):
    """Parse an ER/NR PARAM (64-bit offsets). Returns (param_type, [(row_id, name, data_bytes)], row_size)."""
    row_count = struct.unpack_from("<H", param, 0x0A)[0]
    type_off = struct.unpack_from("<q", param, 0x10)[0]
    ptype = param[type_off:param.index(b"\0", type_off)].decode("ascii", "replace") if 0 < type_off < len(param) else "?"
    rows = []
    for stride in (24, 16):
        rows = []
        ok = True
        for i in range(row_count):
            q = 0x40 + i * stride
            rid = struct.unpack_from("<i", param, q)[0]
            doff = struct.unpack_from("<q", param, q + 8)[0]
            noff = struct.unpack_from("<q", param, q + 16)[0] if stride == 24 else 0
            if not (0 < doff <= len(param)):
                ok = False
                break
            rows.append((rid, doff, noff))
        if ok:
            break
    if not rows:
        return ptype, [], 0
    offs = sorted(set(d for _, d, _ in rows))
    row_size = (offs[1] - offs[0]) if len(offs) > 1 else (len(param) - offs[0])
    # Trailing names region (if present) starts after the last row; clamp row size.
    out = []
    for rid, doff, noff in rows:
        name = ""
        if noff and 0 < noff < len(param):
            end = param.find(b"\0\0", noff)
            try:
                name = param[noff:end + 1].decode("utf-16-le", "replace").strip("\0")
            except Exception:
                name = ""
        out.append((rid, name, param[doff:doff + row_size]))
    return ptype, out, row_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regulation", required=True)
    ap.add_argument("--param-rs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*", default=None)
    args = ap.parse_args()

    import regulation_io  # noqa: E402  (4laric/nightreign-enemy-rando)
    reg = regulation_io.Regulation.load(args.regulation)
    bnd = bytes(reg.bnd)
    b = reg._bnd4
    structs = parse_param_rs(args.param_rs)
    os.makedirs(args.out, exist_ok=True)

    summary = []
    for i in range(b.file_count):
        p = 0x40 + i * b.header_size
        name_off = struct.unpack_from("<I", bnd, p + 32)[0]
        size = struct.unpack_from("<q", bnd, p + 8)[0]
        off = struct.unpack_from("<I", bnd, p + 24)[0]
        fname = b._name(name_off).split("\\")[-1]
        pname = fname[:-6]
        if args.only and pname not in args.only:
            continue
        ptype, rows, row_size = read_param(bnd[off:off + size])
        layout = structs.get(ptype)
        lsize = sum(sz for _, _, sz in layout) if layout else 0
        if layout and lsize == row_size:
            status = "ok"
        elif layout and lsize < row_size:
            status = f"prefix layout={lsize} row={row_size}"   # newer regulation appended fields (or a 1-row name table)
        elif layout:
            status = f"size-mismatch layout={lsize} row={row_size}"
        else:
            status = "no-layout"
        summary.append((pname, ptype, len(rows), row_size, status))
        with open(os.path.join(args.out, pname + ".csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if layout and lsize <= row_size:
                w.writerow(["row_id", "row_name"] + [fn for fn, _, _ in layout] + (["extra_hex"] if lsize < row_size else []))
                fmt = "<" + "".join(ft for _, ft, _ in layout)
                for rid, rname, data in rows:
                    vals = struct.unpack(fmt, data[:lsize])
                    row = [rid, rname] + [v.hex() if isinstance(v, bytes) else v for v in vals]
                    if lsize < row_size:
                        row.append(data[lsize:].hex())
                    w.writerow(row)
            else:
                w.writerow(["row_id", "row_name", "raw_hex"])
                for rid, rname, data in rows:
                    w.writerow([rid, rname, data.hex()])
    with open(os.path.join(args.out, "_summary.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["param", "type", "rows", "row_size", "status"])
        w.writerows(summary)
    bad = [s for s in summary if not s[4].startswith(("ok", "prefix"))]
    print(f"{len(summary)} params dumped, {len(bad)} without a matching layout")
    for s in bad:
        print("  ", s)


if __name__ == "__main__":
    main()
