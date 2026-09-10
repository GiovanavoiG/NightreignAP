#!/usr/bin/env python3
"""
nr_scan.py -- static scanner for nightreign.exe (Elden Ring: Nightreign, x64 PE).

Produces the RVAs / byte signatures an Archipelago mod DLL needs without running
the game.  Pure Python 3 (struct/re/json only).

What it does
  1. Parses PE sections (RVA <-> file offset), VERSIONINFO (ProductName / ProductVersion).
  2. Re-implements the `from-singleton` (Dasaav-dsv) FD4DerivedSingleton / FD4Singleton
     null-check pattern walkers over .text (see find.rs) plus a `cmp qword [rip+X],0`
     variant that the Rust crate does not match but MSVC emits in this build.
     FD4Singleton names are resolved *statically*:
        lea rcx,[rip+key] ; call get_name      (key = 1-byte static used as a lookup handle)
        -> the `DLRuntimeClassImpl<FD4Singleton<T,TImp>>` vftable slot 3 is a tiny
           `lea rax,[rip+key]; ret` getter -> vftable -> RTTI locator -> `.?AV?$DLRuntimeClassImpl@
           V?$FD4Singleton@V<T>@CS@@...` type name.
        Fallback: nearest `DLRuntimeClass` lazy-registration slot (`mov rax,[rip+X]; test; jne;
        call; lea rcx,[rip+"Name"]; mov [rax+38h],rcx`) within +/-0x40 of the static slot.
  3. MSVC RTTI: TypeDescriptors (`.?AV...`), RTTICompleteObjectLocators, vftables.
  4. Data-xref heuristics: vftable -> constructor (`lea rax,[rip+vft]`) -> callers ->
     `mov [rip+static], rax` within 64 bytes after the call.
  5. ItemGib / item-give candidates (prologue AOB + named-function string refs + call graph).
  6. Event-flag get/set: CSFD4VirtualMemoryFlag::GetFlag/SetFlag found by the
     `mov r,[rcx+1Ch]; xor edx,edx; div` divisor idiom, then the CSEventFlagMan wrappers via callers.
  7. Re-tests the Elden Ring AOB templates (Erd-Tools / fromsoftware-rs mapper profile).

Usage:  python3 nr_scan.py <nightreign.exe> [-o out_dir]
"""
import bisect
import json
import os
import re
import struct
import sys
import time
from collections import Counter, defaultdict

# ----------------------------------------------------------------------------- PE

class PE:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.d = f.read()
        d = self.d
        pe = struct.unpack_from('<I', d, 0x3c)[0]
        assert d[pe:pe + 4] == b'PE\0\0', 'not a PE'
        nsec = struct.unpack_from('<H', d, pe + 6)[0]
        optsz = struct.unpack_from('<H', d, pe + 20)[0]
        opt = pe + 24
        self.magic = struct.unpack_from('<H', d, opt)[0]
        self.image_base = struct.unpack_from('<Q', d, opt + 24)[0]
        self.sections = []          # (name, va, vsize, raw_off, raw_size)
        secs = opt + optsz
        for i in range(nsec):
            s = d[secs + i * 40: secs + i * 40 + 40]
            name = s[:8].rstrip(b'\0').decode('latin1')
            vs, va, rs, ro = struct.unpack_from('<IIII', s, 8)
            self.sections.append((name, va, vs, ro, rs))
        # data directories (resource, exception)
        self.datadirs = {}
        for i, n in enumerate(['export', 'import', 'resource', 'exception', 'security', 'basereloc',
                               'debug', 'arch', 'globalptr', 'tls', 'loadcfg', 'bound', 'iat',
                               'delay', 'clr']):
            va, sz = struct.unpack_from('<II', d, opt + 112 + i * 8)
            self.datadirs[n] = (va, sz)

    def section(self, name, nth=0):
        hits = [s for s in self.sections if s[0] == name]
        return hits[nth]

    def rva2off(self, rva):
        for name, va, vs, ro, rs in self.sections:
            if va <= rva < va + rs:          # only file-backed part
                return ro + (rva - va)
        return None

    def off2rva(self, off):
        for name, va, vs, ro, rs in self.sections:
            if ro <= off < ro + rs:
                return va + (off - ro)
        return None

    def sec_of(self, rva):
        for name, va, vs, ro, rs in self.sections:
            if va <= rva < va + vs:
                return name
        return None

    def cstr(self, rva, maxlen=512):
        o = self.rva2off(rva)
        if o is None:
            return None
        e = self.d.find(b'\0', o, o + maxlen)
        if e < 0:
            return None
        s = self.d[o:e]
        try:
            return s.decode('ascii')
        except UnicodeDecodeError:
            return None

    def u64(self, rva):
        o = self.rva2off(rva)
        return None if o is None else struct.unpack_from('<Q', self.d, o)[0]

    def u32(self, rva):
        o = self.rva2off(rva)
        return None if o is None else struct.unpack_from('<I', self.d, o)[0]


# ------------------------------------------------------------------- VERSIONINFO

def version_info(pe):
    """Walk .rsrc for RT_VERSION (16) and return fixed + string version info."""
    d = pe.d
    rva, sz = pe.datadirs['resource']
    if not rva:
        return {}
    base = pe.rva2off(rva)
    if base is None:
        return {}

    def entries(off):
        n_named, n_id = struct.unpack_from('<HH', d, off + 12)
        out = []
        for i in range(n_named + n_id):
            nm, off2 = struct.unpack_from('<II', d, off + 16 + i * 8)
            out.append((nm, off2))
        return out

    def find_version():
        for nm, off2 in entries(base):
            if nm == 16 and off2 & 0x80000000:                     # RT_VERSION
                for nm2, off3 in entries(base + (off2 & 0x7fffffff)):
                    if off3 & 0x80000000:
                        for nm3, off4 in entries(base + (off3 & 0x7fffffff)):
                            data_rva, data_sz = struct.unpack_from('<II', d, base + off4)
                            return pe.rva2off(data_rva), data_sz, nm3
        return None

    hit = find_version()
    if not hit:
        return {}
    off, size, lang = hit
    blob = d[off:off + size]
    info = {'lang_id_of_resource': lang}
    # VS_FIXEDFILEINFO
    sig = blob.find(struct.pack('<I', 0xFEEF04BD))
    if sig >= 0:
        (sig_, sver, fvms, fvls, pvms, pvls) = struct.unpack_from('<6I', blob, sig)
        info['fixed_file_version'] = '%d.%d.%d.%d' % (fvms >> 16, fvms & 0xffff, fvls >> 16, fvls & 0xffff)
        info['fixed_product_version'] = '%d.%d.%d.%d' % (pvms >> 16, pvms & 0xffff, pvls >> 16, pvls & 0xffff)
    # StringFileInfo: scan for UTF-16 keys
    def utf16_at(p):
        e = p
        while e + 1 < len(blob) and blob[e:e + 2] != b'\0\0':
            e += 2
        return blob[p:e].decode('utf-16-le', 'replace'), e + 2
    strings = {}
    for key in ['ProductName', 'ProductVersion', 'FileVersion', 'FileDescription', 'InternalName',
                'OriginalFilename', 'CompanyName', 'LegalCopyright']:
        k = key.encode('utf-16-le')
        p = blob.find(k)
        if p < 0:
            continue
        # header: wLength, wValueLength, wType, szKey, padding, value
        wlen, vlen, wtype = struct.unpack_from('<HHH', blob, p - 6)
        val_start = p + len(k) + 2
        val_start = (val_start + 3) & ~3
        s, _ = utf16_at(val_start)
        strings[key] = s
    info['strings'] = strings
    # translation
    t = blob.find('Translation'.encode('utf-16-le'))
    if t >= 0:
        vs = (t + len('Translation'.encode('utf-16-le')) + 2 + 3) & ~3
        lang_, cp = struct.unpack_from('<HH', blob, vs)
        info['translation'] = {'lang': lang_, 'codepage': cp}
    return info


# ------------------------------------------------------------------------- RTTI

class Rtti:
    """MSVC x64 RTTI: TypeDescriptor -> CompleteObjectLocator -> vftable."""

    def __init__(self, pe):
        self.pe = pe
        d = pe.d
        base = pe.image_base
        self.td = {}            # td_rva -> mangled name
        for m in re.finditer(rb'\.\?A[VU][^\0]{1,400}\0', d):
            off = m.start() - 16          # TypeDescriptor {vftable, spare, name[]}
            r = pe.off2rva(off)
            if r is None:
                continue
            self.td[r] = m.group()[:-1].decode('latin1')
        rname, rva_, rvs, roff, rsz = pe.section('.rdata')
        rdata = d[roff:roff + rsz]
        self.locs = {}          # locator_rva -> (name, offset)
        for m in re.finditer(rb'\x01\x00\x00\x00', rdata):
            p = m.start()
            if p % 4 or p + 24 > len(rdata):
                continue
            sig, off, cd, tdr, cdr, selfr = struct.unpack_from('<6I', rdata, p)
            if selfr == rva_ + p and tdr in self.td:
                self.locs[rva_ + p] = (self.td[tdr], off)
        ptrs = defaultdict(list)
        for i in range(0, rsz - 7, 8):
            q = struct.unpack_from('<Q', rdata, i)[0] - base
            if q in self.locs:
                ptrs[q].append(rva_ + i + 8)
        self.vft = defaultdict(list)     # name -> [(vftable_rva, offset)]
        for loc, (name, off) in self.locs.items():
            for v in ptrs.get(loc, []):
                self.vft[name].append((v, off))
        # function pointer -> set(vftable names) (first 64 slots)
        self.fn2vft = defaultdict(set)
        text_lo = pe.section('.text')[1]
        text_hi = max(va + vs for n, va, vs, ro, rs in pe.sections if n == '.text')
        for name, lst in self.vft.items():
            for v, off in lst:
                o = pe.rva2off(v)
                for k in range(64):
                    q = struct.unpack_from('<Q', d, o + k * 8)[0] - base
                    if not (text_lo <= q < text_hi) or (rva_ <= q < rva_ + rvs):
                        break
                    self.fn2vft[q].add(name)

    def vftable(self, cls, ns='CS'):
        """primary (offset 0) vftable RVA for `.?AV<cls>@<ns>@@`"""
        key = '.?AV%s@%s@@' % (cls, ns)
        for v, off in self.vft.get(key, []):
            if off == 0:
                return v
        lst = self.vft.get(key)
        return lst[0][0] if lst else None

    def vfuncs(self, v, n=64):
        d, base = self.pe.d, self.pe.image_base
        o = self.pe.rva2off(v)
        out = []
        text_lo = self.pe.section('.text')[1]
        for k in range(n):
            q = struct.unpack_from('<Q', d, o + k * 8)[0] - base
            if not (text_lo <= q < 0x7fffffff) or self.pe.sec_of(q) not in ('.text',):
                break
            out.append(q)
        return out


# ----------------------------------------------------------------- code model

class Code:
    """.text view, .pdata function table (with Arxan chained-unwind chunk -> root), xrefs, calls."""

    RIP_PAT = re.compile(rb'(?:[\x40-\x4f])?(?:\x8b|\x8d|\x89|\x3b|\x39|\x63|\x0f\xb6|\x0f\xb7|\x0f\xbe)'
                         rb'[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]', re.S)

    def __init__(self, pe):
        self.pe = pe
        n, self.tva, self.tvs, self.toff, self.tsz = pe.section('.text')
        self.text = pe.d[self.toff:self.toff + self.tsz]
        n, self.dva, self.dvs, self.doff, self.dsz = pe.section('.data')
        n, self.rva_, self.rvs, self.roff, self.rsz = pe.section('.rdata')
        # pdata
        prva, psz = pe.datadirs['exception']
        po = pe.rva2off(prva)
        self.funcs = []
        for i in range(0, psz, 12):
            b, e, u = struct.unpack_from('<III', pe.d, po + i)
            if b:
                self.funcs.append((b, e, u))
        self.funcs.sort()
        self.begins = [f[0] for f in self.funcs]
        self._root_cache = {}
        self.root_chunks = defaultdict(list)
        for f in self.funcs:
            self.root_chunks[self.root_of(f)[0]].append(f)
        # xref index (rip-relative operands into .data / .rdata)
        self.xref = defaultdict(list)
        t = self.text
        for m in self.RIP_PAT.finditer(t):
            e = m.end()
            if e + 4 > len(t):
                continue
            disp = struct.unpack_from('<i', t, e)[0]
            tgt = (self.tva + e + 4 + disp) & 0xffffffff
            if self.dva <= tgt < self.dva + self.dvs or self.rva_ <= tgt < self.rva_ + self.rvs:
                self.xref[tgt].append((self.tva + m.start(), t[m.start():e]))
        # call index
        self.calls = defaultdict(list)
        for m in re.finditer(b'\xe8', t):
            i = m.start()
            if i + 5 > len(t):
                continue
            rel = struct.unpack_from('<i', t, i + 1)[0]
            tgt = (self.tva + i + 5 + rel) & 0xffffffff
            if self.tva <= tgt < self.tva + self.tsz:
                self.calls[tgt].append(self.tva + i)
        self.jmps = defaultdict(list)
        for m in re.finditer(b'\xe9', t):
            i = m.start()
            if i + 5 > len(t):
                continue
            rel = struct.unpack_from('<i', t, i + 1)[0]
            tgt = (self.tva + i + 5 + rel) & 0xffffffff
            if self.tva <= tgt < self.tva + self.tsz:
                self.jmps[tgt].append(self.tva + i)

    # -- helpers
    def in_text(self, rva):
        return self.tva <= rva < self.tva + self.tsz

    def in_data(self, rva):
        return self.dva <= rva < self.dva + self.dvs

    def func_of(self, rva):
        i = bisect.bisect_right(self.begins, rva) - 1
        if i >= 0 and self.funcs[i][0] <= rva < self.funcs[i][1]:
            return self.funcs[i]
        return None

    def root_of(self, f):
        if f is None:
            return None
        if f[0] in self._root_cache:
            return self._root_cache[f[0]]
        cur = f
        for _ in range(16):
            uo = self.pe.rva2off(cur[2])
            if uo is None:
                break
            flags = self.pe.d[uo] >> 3
            cnt = self.pe.d[uo + 2]
            if not flags & 4:
                break
            p = uo + 4 + ((cnt + 1) & ~1) * 2
            b, e, u = struct.unpack_from('<III', self.pe.d, p)
            cur = (b, e, u)
        self._root_cache[f[0]] = cur
        return cur

    def root_rva(self, rva):
        f = self.func_of(rva)
        return self.root_of(f)[0] if f else None

    def body(self, start, end):
        return self.text[start - self.tva:end - self.tva]

    def bytes_at(self, rva, n):
        return self.text[rva - self.tva:rva - self.tva + n]

    def rip_target(self, site_rva, instr_len):
        disp = struct.unpack_from('<i', self.text, site_rva - self.tva + instr_len - 4)[0]
        return (site_rva + instr_len + disp) & 0xffffffff

    def aob(self, pattern):
        parts = pattern.split()
        rx = b''.join(b'.' if p in ('?', '??') else re.escape(bytes([int(p, 16)])) for p in parts)
        return [self.tva + m.start() for m in re.finditer(rx, self.text, re.S)]

    def string_sites(self, s):
        """code sites that reference the C string `s` (rip-relative)."""
        out = []
        for m in re.finditer(re.escape(s.encode()) + rb'\0', self.pe.d):
            r = self.pe.off2rva(m.start())
            if r is not None:
                out += [a for a, _ in self.xref.get(r, [])]
        return out

    # -- per-root aggregate info
    def root_info(self, root, statics):
        chunks = self.root_chunks.get(root) or [self.func_of(root) or (root, root + 0x200, 0)]
        info = {'root': root, 'chunks': len(chunks), 'size': sum(c[1] - c[0] for c in chunks),
                'statics': [], 'strings': [], 'consts': Counter(), 'calls': []}
        for (s, e, u) in chunks:
            b = self.body(s, e)
            for m in self.RIP_PAT.finditer(b):
                ee = m.end()
                if ee + 4 > len(b):
                    continue
                disp = struct.unpack_from('<i', b, ee)[0]
                t = (s + ee + 4 + disp) & 0xffffffff
                if t in statics:
                    info['statics'].append(statics[t])
                elif self.rva_ <= t < self.rva_ + self.rvs:
                    st = self.pe.cstr(t, 80)
                    if st and len(st) >= 4 and all(32 <= ord(c) < 127 for c in st):
                        info['strings'].append(st)
            for c, nm in [(b'\x00\x00\x00\x40', '0x40000000'), (b'\x00\x00\x00\x80', '0x80000000'),
                          (b'\x00\x00\x00\xc0', '0xC0000000'), (b'\x00\x00\x00\x10', '0x10000000'),
                          (b'\x00\x00\x00\x20', '0x20000000'), (b'\xff\xff\xff\x0f', '0x0FFFFFFF'),
                          (b'\x00\x00\x00\xf0', '0xF0000000'), (b'\xff\xff\xff\x00', '0x00FFFFFF'),
                          (b'\x83\xf8\x0a', 'cmp eax,0Ah')]:
                n = b.count(c)
                if n:
                    info['consts'][nm] += n
            for m in re.finditer(b'\xe8', b):
                i = m.start()
                if i + 5 > len(b):
                    continue
                rel = struct.unpack_from('<i', b, i + 1)[0]
                t = (s + i + 5 + rel) & 0xffffffff
                if self.in_text(t):
                    info['calls'].append(t)
        return info


# ------------------------------------------------------ from-singleton port

LEA_RCX = b'\x48\x8d\x0d'
LEA_R8 = b'\x4c\x8d\x05'
LEA_R9 = b'\x4c\x8d\x0d'
MOV_R9 = b'\x4c\x8b\xc8'
CALL = 0xe8


def candidates_iter(text):
    """Port of find.rs::candidates_iter. Yields ('derived', pos, r9_disp_pos) / ('fd4', pos)."""
    for m in re.finditer(b'\xba', text):
        pos = m.start()
        ins = [('edx', pos)]

        def nxt(i):
            k, p = i
            return p + 5 if k == 'edx' else (p + 3 if k == 'r9m' else p + 7)
        ok = True
        while len(ins) < 4:
            np_ = nxt(ins[-1])
            c = text[np_:np_ + 3]
            if c == LEA_RCX:
                ins.append(('rcx', np_))
            elif c == LEA_R8:
                ins.append(('r8', np_))
            elif c == LEA_R9:
                ins.append(('r9', np_))
            elif c == MOV_R9:
                ins.append(('r9m', np_))
            elif c[:1] == b'\xe8':
                break
            else:
                ok = False
                break
        if not ok:
            continue
        while len(ins) < 4:
            p = ins[0][1]
            pp = p - 7
            if pp < 0:
                ok = False
                break
            c = text[pp:p]
            if c[:3] == LEA_RCX:
                ins.insert(0, ('rcx', pp))
            elif c[:3] == LEA_R8:
                ins.insert(0, ('r8', pp))
            elif c[:3] == LEA_R9:
                ins.insert(0, ('r9', pp))
            elif c[4:] == MOV_R9:
                ins.insert(0, ('r9m', pp + 4))
            else:
                ok = False
                break
        if not ok:
            continue
        mask = 0
        for k, p in ins:
            mask |= {'rcx': 1, 'r8': 2, 'r9': 4, 'r9m': 8}.get(k, 0)
        if mask == 7:
            r9 = [p for k, p in ins if k == 'r9'][0]
            yield ('derived', ins[0][1], r9 + 3)
        elif mask == 11:
            yield ('fd4', ins[0][1], None)


def cond_jump(text, pos):
    if pos >= 2 and text[pos - 2] == 0x75:
        return pos - 2
    if pos >= 6 and text[pos - 6:pos - 4] == b'\x0f\x85':
        return pos - 6
    return None


def find_static_load(text, jpos):
    """Before the jne at `jpos`: either `test r,r` + `mov r,[rip+X]` (find.rs) or
    `cmp qword [rip+X],0` (48 83 3D disp32 00).  Returns (text_pos_of_mov, disp_pos, kind)."""
    t = jpos - 3
    if t >= 0:
        test = text[t:t + 3]
        rex, modrm = test[0], test[2]
        if (rex & ~7) == 0x48 and (modrm & 0xc0) == 0xc0 and (modrm & 7) == ((modrm >> 3) & 7) and test[1] == 0x85:
            rexb = rex & 1
            reg1 = modrm & 7
            for pad in range(4):
                p = t - 7 - pad
                if p < 0:
                    break
                mov = text[p:p + 7]
                if (mov[0] & ~7) == 0x48 and mov[1] == 0x8b and (mov[2] & 0xc0) == 0 and (mov[2] & 7) == 5 \
                        and ((mov[0] >> 2) & 1) == rexb and ((mov[2] >> 3) & 7) == reg1:
                    return p, p + 3, 7, 'mov/test'
    c = jpos - 8
    if c >= 0 and text[c:c + 3] == b'\x48\x83\x3d' and text[c + 7] == 0:
        return c, c + 3, 8, 'cmp'
    return None


def derived_singletons(code):
    """{static_rva: name}"""
    text, tva = code.text, code.tva
    out = {}
    for kind, pos, cap2 in candidates_iter(text):
        if kind != 'derived':
            continue
        j = cond_jump(text, pos)
        if j is None:
            continue
        hit = find_static_load(text, j)
        if hit is None:
            continue
        p, dpos, ilen, how = hit
        addr = (tva + p + ilen + struct.unpack_from('<i', text, dpos)[0]) & 0xffffffff
        if not code.in_data(addr):
            continue
        name_rva = (tva + cap2 + 4 + struct.unpack_from('<i', text, cap2)[0]) & 0xffffffff
        nm = code.pe.cstr(name_rva)
        if nm:
            out.setdefault(addr, {'name': nm, 'sites': [], 'kind': how})['sites'].append(tva + pos)
    return out


def fd4_singletons(code):
    """{static_rva: {'keys': [key_rva...], 'sites': [...]}}, get_name_rva"""
    text, tva = code.text, code.tva
    out = {}
    get_name = Counter()
    for kind, pos, _ in candidates_iter(text):
        if kind != 'fd4':
            continue
        for pad in range(2):
            p = pos - 5 - pad
            if p < 0 or text[p] != CALL:
                continue
            fn = (tva + p + 5 + struct.unpack_from('<i', text, p + 1)[0]) & 0xffffffff
            p2 = p - 7
            if p2 < 0 or text[p2:p2 + 3] != LEA_RCX:
                continue
            key = (tva + p2 + 7 + struct.unpack_from('<i', text, p2 + 3)[0]) & 0xffffffff
            j = cond_jump(text, p2)
            if j is None:
                continue
            hit = find_static_load(text, j)
            if hit is None:
                continue
            mp, dpos, ilen, how = hit
            addr = (tva + mp + ilen + struct.unpack_from('<i', text, dpos)[0]) & 0xffffffff
            if not code.in_data(addr):
                continue
            e = out.setdefault(addr, {'keys': set(), 'sites': [], 'kinds': set()})
            e['keys'].add(key)
            e['sites'].append(tva + pos)
            e['kinds'].add(how)
            if code.in_text(fn):
                get_name[fn] += 1
            break
    return out, get_name


def runtime_class_registrations(code):
    """DLRuntimeClass lazy-registration getters:
       mov rax,[rip+X]; test rax,rax; jne +5; call alloc; lea rcx,[rip+"Name"]; mov [rax+38h],rcx; ...
       -> {slot_rva: name}"""
    pat = re.compile(rb'\x48\x8b\x05(....)\x48\x85\xc0\x75\x05\xe8(....)\x48\x8d\x0d(....)\x48\x89\x48\x38', re.S)
    reg = {}
    text, tva = code.text, code.tva
    for m in pat.finditer(text):
        i = m.start()
        X = (tva + i + 7 + struct.unpack('<i', m.group(1))[0]) & 0xffffffff
        n1 = (tva + m.start(3) + 4 + struct.unpack('<i', m.group(3))[0]) & 0xffffffff
        nm = code.pe.cstr(n1)
        if nm:
            reg[X] = {'name': nm, 'getter': tva + i}
    return reg


def resolve_fd4_names(code, rtti, fd4, reg):
    """Static name resolution for FD4Singleton keys (see module doc)."""
    text, tva = code.text, code.tva
    keyfn = defaultdict(list)
    # `lea rax,[rip+key]; ret`  -- Arxan also rewrites `ret` as `lea rsp,[rsp+8]; jmp [rsp-8]`
    for m in re.finditer(rb'\x48\x8d\x05(....)(?:\xc3|\x48\x8d\x64\x24\x08\xff\x64\x24\xf8)', text, re.S):
        i = m.start()
        t = (tva + i + 7 + struct.unpack('<i', m.group(1))[0]) & 0xffffffff
        keyfn[t].append(tva + i)
    # vftable slots may be Arxan `jmp rel32` trampolines: follow up to 4 jumps.
    def follow(rva):
        for _ in range(4):
            if not code.in_text(rva) or code.text[rva - tva] != 0xe9:
                return rva
            rva = (rva + 5 + struct.unpack_from('<i', text, rva - tva + 1)[0]) & 0xffffffff
        return rva
    fn2vft = defaultdict(set)
    for f, names in rtti.fn2vft.items():
        fn2vft[f] |= names
        ff = follow(f)
        if ff != f:
            fn2vft[ff] |= names
    result = {}
    for addr, e in fd4.items():
        names = set()
        via = None
        for k in e['keys']:
            for f in keyfn.get(k, []):
                for n in fn2vft.get(f, []):
                    m = re.search(r'FD4Singleton@V(\w+)@(\w+)@@', n)
                    if m:
                        names.add(m.group(1))
                        via = 'vftable-rtti'
        conf = 'CONFIRMED' if names else None
        if not names:
            near = sorted((abs(x - addr), x) for x in reg if abs(x - addr) <= 0x50)
            if near:
                names.add(reg[near[0][1]]['name'])
                via = 'proximity-to-runtime-class-slot(+%#x)' % (near[0][1] - addr)
                conf = 'LIKELY'
        result[addr] = {'names': sorted(names), 'via': via, 'confidence': conf or 'UNKNOWN',
                        'keys': sorted(e['keys']), 'n_sites': len(e['sites']), 'kinds': sorted(e['kinds'])}
    return result


# ----------------------------------------------------------- heuristics

STORE_PAT = re.compile(rb'(?:\x48|\x4c)\x89[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]', re.S)


def ctor_static_candidates(code, rtti, cls, ns='CS'):
    """vftable -> `lea rax,[rip+vft]` (ctor) -> callers of ctor root -> `mov [rip+X], r64` within 64B."""
    out = []
    key = '.?AV%s@%s@@' % (cls, ns)
    for v, off in rtti.vft.get(key, []):
        for a, op in code.xref.get(v, []):
            if op[-2:-1] != b'\x8d':
                continue
            ctor = code.root_rva(a)
            if ctor is None:
                continue
            for s in code.calls.get(ctor, []):
                w = code.bytes_at(s + 5, 72)
                for m in STORE_PAT.finditer(w):
                    e = m.end()
                    if e + 4 > len(w) or e > 64:
                        continue
                    disp = struct.unpack_from('<i', w, e)[0]
                    t = (s + 5 + e + 4 + disp) & 0xffffffff
                    if code.in_data(t):
                        out.append({'static': t, 'store_site': s + 5 + m.start(), 'ctor': ctor,
                                    'ctor_call_site': s, 'vftable': v})
    return out


def find_get_set_flag(code):
    """CSFD4VirtualMemoryFlag::GetFlag/SetFlag: `mov r32,[rcx+1Ch]` ... `div r32` within 24 bytes,
    then classify by `bts`/`btr` (set) vs `setne`/`test` (get)."""
    pat = re.compile(rb'(?:\x44|\x41|\x45)?\x8b[\x41\x49\x51\x59\x61\x69\x71\x79]\x1c.{0,24}?\xf7[\xf0-\xf7]', re.S)
    out = []
    seen = set()
    for m in pat.finditer(code.text):
        r = code.tva + m.start()
        f = code.func_of(r)
        start = f[0] if f else r
        if start in seen:
            continue
        seen.add(start)
        # function end: next pdata begin or ret-based guess
        if f:
            end = f[1]
        else:
            i = bisect.bisect_right(code.begins, r)
            end = min(code.begins[i], r + 0x200) if i < len(code.begins) else r + 0x200
        b = code.body(start, end)
        feats = {
            'size': len(b),
            'bts': b.count(b'\x0f\xab'), 'btr': b.count(b'\x0f\xb3'), 'bt': b.count(b'\x0f\xa3'),
            'setne': b.count(b'\x0f\x95'), 'and7': len(re.findall(rb'\x83[\xe0-\xe7]\x07', b)),
            'shr3': len(re.findall(rb'\x48?\xc1[\xe8-\xef]\x03', b)),
            'mov_edx_7': b.count(b'\xba\x07\x00\x00\x00'), 'mov_ecx_7': b.count(b'\xb9\x07\x00\x00\x00'),
            'load_0x38': len(re.findall(rb'\x8b[\x41\x49\x51\x59]\x38', b)),
            'load_0x28': len(re.findall(rb'\x03[\x41\x49\x51\x59]\x28|\x8b[\x41\x49\x51\x59]\x28', b)),
            'load_0x20': len(re.findall(rb'\xaf[\x41\x49\x51\x59]\x20|\x8b[\x41\x49\x51\x59]\x20', b)),
            'has_pdata': bool(f),
        }
        kind = None
        if feats['bts'] and feats['btr']:
            kind = 'SetFlag'
        elif feats['setne'] and (feats['bt'] or feats['and7']) and not feats['bts']:
            kind = 'GetFlag'
        out.append({'rva': start, 'div_site': r, 'kind': kind, 'features': feats,
                    'prologue': code.bytes_at(start, 24).hex()})
    return out


def wrapper_callers(code, target, want_static):
    """callers of `target` that also load the CSEventFlagMan static (=> CSEventFlagMan::Get/SetEventFlag)."""
    roots = Counter()
    for s in code.calls.get(target, []):
        r = code.root_rva(s)
        if r:
            roots[r] += 1
    return roots


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    outdir = '.'
    if '-o' in sys.argv:
        outdir = sys.argv[sys.argv.index('-o') + 1]
    os.makedirs(outdir, exist_ok=True)
    t0 = time.time()
    pe = PE(path)
    print('[+] %s: image base %#x, %d sections' % (path, pe.image_base, len(pe.sections)))
    for s in pe.sections:
        print('    %-8s va=%#x vsize=%#x raw=%#x rawsize=%#x' % s)
    vi = version_info(pe)
    print('[+] version:', json.dumps(vi))
    rtti = Rtti(pe)
    print('[+] RTTI: %d type descriptors, %d locators, %d vftable classes' % (len(rtti.td), len(rtti.locs), len(rtti.vft)))
    code = Code(pe)
    print('[+] code: %d pdata entries, %d roots, %d xref targets, %d call targets (%.1fs)' % (
        len(code.funcs), len(code.root_chunks), len(code.xref), len(code.calls), time.time() - t0))

    result = {'file': os.path.basename(path), 'image_base': pe.image_base,
              'sections': [{'name': n, 'va': va, 'vsize': vs, 'raw_off': ro, 'raw_size': rs} for n, va, vs, ro, rs in pe.sections],
              'version_info': vi}

    # ---- RTTI dump
    cs_names = sorted(n for n in rtti.td.values() if re.search(r'@CS@@', n))
    with open(os.path.join(outdir, 'rtti_cs_names.txt'), 'w') as f:
        for n in cs_names:
            vs = rtti.vft.get(n, [])
            f.write('%s\t%s\n' % (n, ','.join('%#x' % v for v, o in vs if o == 0)))
    print('[+] wrote rtti_cs_names.txt (%d names)' % len(cs_names))
    want = ['CSEventFlagMan', 'CSEventFlagManImp', 'CSFD4VirtualMemoryFlag', 'GameDataMan', 'GameMan', 'WorldChrMan',
            'WorldChrManImp', 'CSMenuMan', 'CSMenuManImp', 'MapItemMan', 'MapItemManImpl', 'SoloParamRepository',
            'SoloParamRepositoryImp', 'MsgRepository', 'MsgRepositoryImp', 'CSSystemProperties', 'CSSystemPropertiesImp',
            'CSNetMan', 'CSNetManImp', 'PlayerGameData', 'EquipInventoryData', 'EquipGameData', 'CSGaitemGameData',
            'CSFile', 'CSFileImp', 'CSRegulationManager', 'CSRegulationManagerImp', 'CSItemGetMenuManImpl',
            'CSGaitemImp', 'CSGaitemIns', 'ChrIns', 'PlayerIns', 'CSLuaEventManagerImp', 'CSEventFlagUsageParamManagerImp']
    vft_out = {}
    for w in want:
        v = rtti.vftable(w)
        if v is None:
            # any namespace
            for n, lst in rtti.vft.items():
                if n.startswith('.?AV%s@' % w):
                    v = [x for x, o in lst if o == 0][0] if any(o == 0 for x, o in lst) else lst[0][0]
                    break
        vft_out[w] = v
    result['rtti_vftables'] = {k: v for k, v in vft_out.items()}
    for k, v in vft_out.items():
        print('    vftable %-32s %s' % (k, '%#x' % v if v else '(no RTTI vftable)'))

    # ---- singletons
    derived = derived_singletons(code)
    print('[+] FD4DerivedSingleton: %d' % len(derived))
    for a, e in sorted(derived.items()):
        print('    %#x %s (%d sites, %s)' % (a, e['name'], len(e['sites']), e['kind']))
    fd4, get_name = fd4_singletons(code)
    reg = runtime_class_registrations(code)
    fd4_named = resolve_fd4_names(code, rtti, fd4, reg)
    print('[+] FD4Singleton: %d statics, get_name candidates %s, %d DLRuntimeClass registration slots' % (
        len(fd4), ['%#x(%d)' % kv for kv in get_name.most_common(3)], len(reg)))
    n_conf = sum(1 for e in fd4_named.values() if e['confidence'] == 'CONFIRMED')
    print('    names resolved: %d confirmed, %d by proximity, %d unknown' % (
        n_conf, sum(1 for e in fd4_named.values() if e['confidence'] == 'LIKELY'),
        sum(1 for e in fd4_named.values() if e['confidence'] == 'UNKNOWN')))
    result['derived_singletons'] = {'%#x' % a: {'name': e['name'], 'n_sites': len(e['sites']), 'kind': e['kind']} for a, e in sorted(derived.items())}
    result['fd4_get_name_rva'] = get_name.most_common(1)[0][0] if get_name else None
    result['fd4_singletons'] = {'%#x' % a: {**e, 'keys': ['%#x' % k for k in e['keys']]} for a, e in sorted(fd4_named.items())}
    result['runtime_class_slots'] = {'%#x' % a: e['name'] for a, e in sorted(reg.items())}
    by_name = {}
    for a, e in fd4_named.items():
        for n in e['names']:
            by_name[n] = a
    for a, e in derived.items():
        by_name[e['name']] = a
    statics = {a: (e['names'][0] if e['names'] else '?') for a, e in fd4_named.items()}
    statics.update({a: e['name'] for a, e in derived.items()})

    # ---- ER AOB templates
    er_aobs = {
        'GameDataManAoB': '48 8B 05 ? ? ? ? 48 85 C0 74 05 48 8B 40 58 C3 C3',
        'GameDataMan_mapper': '48 89 05 ? ? ? ? 48 83 C4 38 E9',
        'GameManAoB': '48 8B 05 ? ? ? ? 80 B8 ? ? ? ? 0D 0F 94 C0 C3',
        'SoloParamRepositoryAoB': '48 8B 0D ? ? ? ? 48 85 C9 0F 84 ? ? ? ? 45 33 C0 BA 8E 00 00 00',
        'WorldChrManAoB': '48 8B 05 ? ? ? ? 48 85 C0 74 0F 48 39 88',
        'CSFD4VirtualMemoryFlagAoB': '48 8B 3D ? ? ? ? 48 85 FF 74 ? 48 8B 49',
        'IsEventCallAoB': '48 83 EC 28 8B 12 85 D2',
        'SetEventCallAoB': '48 89 74 24 18 57 48 83 EC 30 48 8B DA 41 0F B6 F8 8B 12 48 8B F1 85 D2 0F 84 ? ? ? ? 45 84 C0',
        'ItemGiveAoB(8B 02 83 F8 0A)': '8B 02 83 F8 0A',
        'MapItemManAoB': '48 8B 0D ? ? ? ? C7 44 24 50 FF FF FF FF C7 45 A0 FF FF FF FF 48 85 C9 75 2E',
        'ItemGib_prologue_6C24': '40 55 56 57 41 54 41 55 41 56 41 57 48 8D 6C 24',
        'ItemGib_prologue_AC24': '40 55 56 57 41 54 41 55 41 56 41 57 48 8D AC 24',
        'RemoveItemAoB': '? 83 EC ? 8B F2 ? 8B E9 ? 85 C0 74',
        'CSLuaEventManagerAoB': '48 83 3D ? ? ? ? 00 48 8B F9 0F 84 ? ? ? ? 48',
        'MsgRepositoryImpAoB': '48 8B 3D ? ? ? ? 44 0F B6 30 48 85 FF 75',
        'ChrDebugFlagsAoB': '80 3D ? ? ? ? 00 0F 85 ? ? ? ? 32 C0 48',
        'cs_menu_man_imp_display_status_message': 'BA D0 07 00 00 48 83 C4 28 E9',
    }
    aob_res = {}
    for n, p in er_aobs.items():
        hits = code.aob(p)
        aob_res[n] = {'pattern': p, 'hits': hits[:16], 'n': len(hits)}
        print('    ER AOB %-42s %d hit(s) %s' % (n, len(hits), ['%#x' % h for h in hits[:6]]))
    result['er_aob_templates'] = aob_res
    game_man_static = None
    if aob_res['GameManAoB']['n'] == 1:
        h = aob_res['GameManAoB']['hits'][0]
        game_man_static = code.rip_target(h, 7)
        flag_off = struct.unpack_from('<i', code.text, h - code.tva + 9)[0]
        print('    GameManAoB -> static %#x (cmp byte [GameMan+%#x], 0Dh)' % (game_man_static, flag_off))

    # ---- GameDataMan (no DLRF, no RTTI): creation pattern  B9 <size> E8 alloc ... 48 89 05 <static> 48 83 C4 28 E9
    gdm = {}
    pat = re.compile(rb'\xb9(....)\xe8(....)\x48\x89\x44\x24\x38\x48\x85\xc0\x74\x09\x48\x8b\xc8\xe8(....)\x90\x48\x89\x05(....)\x48\x83\xc4\x28\xe9', re.S)
    gdm_hits = []
    for m in pat.finditer(code.text):
        i = m.start()
        size = struct.unpack('<I', m.group(1))[0]
        st = (code.tva + m.start(4) + 4 + struct.unpack('<i', m.group(4))[0]) & 0xffffffff
        ctor = (code.tva + m.start(3) + 4 + struct.unpack('<i', m.group(3))[0]) & 0xffffffff
        gdm_hits.append({'site': code.tva + i, 'alloc_size': size, 'static': st, 'ctor': ctor,
                         'n_refs': len(code.xref.get(st, []))})
    # rank: static most referenced from the region that references "CS::GameDataMan::*" strings
    gdm_strings = {}
    for s in ['CS::GameDataMan::OnGameClear', 'CS::GameDataMan::OnMoveMapInitialize', 'CS::GameDataMan::UpdatePlayPhase',
              'CS::GameDataMan::UpdateStatisticsData', 'CS::GameDataMan::Reset_forEnterLobby',
              'CS::GameDataMan::Reset_forEnterIngameTutorial']:
        sites = code.string_sites(s)
        gdm_strings[s] = sorted(set(code.root_rva(a) for a in sites if code.root_rva(a)))
    tu_roots = sorted(set(r for lst in gdm_strings.values() for r in lst))
    tu_lo, tu_hi = (min(tu_roots) - 0x8000, max(tu_roots) + 0x8000) if tu_roots else (0, 0)
    cnt = Counter()
    for t, l in code.xref.items():
        if code.in_data(t) and t not in statics:
            n = sum(1 for a, _ in l if tu_lo <= a < tu_hi)
            if n:
                cnt[t] = n
    gdm['creation_pattern_hits'] = gdm_hits
    gdm['method_name_strings'] = {k: ['%#x' % r for r in v] for k, v in gdm_strings.items()}
    gdm['tu_region'] = [tu_lo, tu_hi]
    gdm['top_data_refs_from_tu'] = [{'static': t, 'refs_from_tu': n, 'total_refs': len(code.xref[t]),
                                     'ops': dict(Counter(op.hex() for a, op in code.xref[t]).most_common(3))}
                                    for t, n in cnt.most_common(6)]
    gdm_static = None
    if gdm_hits:
        best = max(gdm_hits, key=lambda h: h['n_refs'])
        gdm_static = best['static']
        # confidence: creation pattern + top TU ref agree
        agree = cnt and cnt.most_common(1)[0][0] == gdm_static
        gdm['static'] = gdm_static
        gdm['confidence'] = 'CONFIRMED' if agree else 'LIKELY'
        gdm['evidence'] = ('object allocated with size %#x, constructed at %#x, stored to [rip+%#x] with `add rsp,28h; jmp` '
                           '(same shape as ER mapper pattern `48 89 05 $ 48 83 c4 38 e9`); static is referenced %d times '
                           '(%d of them from the CS::GameDataMan::* translation unit); readers do `mov rax,[rax+8]` '
                           '(main_player_game_data at +8 like ER)') % (best['alloc_size'], best['ctor'], gdm_static,
                                                                   best['n_refs'], cnt.get(gdm_static, 0))
        statics[gdm_static] = 'GameDataMan'
        # readers' most common follow-up bytes
        gdm['reader_followups'] = Counter(code.bytes_at(a + 7, 11).hex() for a, op in code.xref[gdm_static]).most_common(6)
        print('[+] GameDataMan static %#x (%s)' % (gdm_static, gdm['confidence']))
    result['game_data_man'] = gdm

    # ---- constructor -> static heuristic for RTTI classes
    ctor_stats = {}
    for cls in ['GameMan', 'PlayerGameData', 'CSMenuManImp', 'EquipGameData', 'CSFD4VirtualMemoryFlag', 'CSRegulationManagerImp',
                'SoloParamRepositoryImp', 'MsgRepositoryImp', 'CSNetManImp', 'CSSystemPropertiesImp', 'CSFileImp',
                'CSEventFlagManImp', 'WorldChrManImp', 'MapItemManImpl', 'CSItemGetMenuManImpl', 'CSGaitemImp', 'CSLuaEventManagerImp']:
        c = ctor_static_candidates(code, rtti, cls)
        for e in c:
            e['matches_dlrf'] = statics.get(e['static'])
            e['total_refs'] = len(code.xref.get(e['static'], []))
        ctor_stats[cls] = c
        if c:
            print('    ctor-static %-24s %s' % (cls, ['%#x(%s,refs=%d)' % (e['static'], e['matches_dlrf'], e['total_refs']) for e in c]))
    result['ctor_static_candidates'] = ctor_stats
    if game_man_static:
        statics[game_man_static] = 'GameMan'
    for e in ctor_stats.get('PlayerGameData', []):
        statics.setdefault(e['static'], 'PlayerGameData?')

    # ---- event flags
    ef = find_get_set_flag(code)
    ef_out = []
    for e in ef:
        callers = wrapper_callers(code, e['rva'], None)
        wr = []
        for r, n in callers.most_common(8):
            info = code.root_info(r, statics)
            wr.append({'root': r, 'n_calls': n, 'size': info['size'], 'statics': sorted(set(info['statics'])),
                       'prologue': code.bytes_at(r, 32).hex()})
        e['callers'] = wr
        ef_out.append(e)
        print('[+] flag fn %#x kind=%s size=%#x callers=%s' % (e['rva'], e['kind'], e['features']['size'],
                                                                ['%#x' % w['root'] for w in wr]))
    result['event_flag_functions'] = ef_out
    # CSEventFlagMan static & wrappers
    efm = by_name.get('CSEventFlagMan')
    result['cs_event_flag_man_static'] = efm

    # ---- ItemGib / item-give candidates
    item = {}
    named = {}
    for s in ['CS::EquipGameData::AddInventoryEquip', 'CS::EquipGameData::CheckAddItem_forDLC',
              'CS::MapItemManImpl::_RequestRegistGetItem', 'CS::MapItemManImpl::Limited_RequestRegistGetTalkItem',
              'CS::MapItemManImpl::_NotifyRemoveMapItem', 'CS::ItemLotUtil::_ResetCumulateNum',
              'CS::ItemLotParam::Util_CanExecByEventFlag', 'CS::MenuGaitemEnumerator::_Enumerate_ArchiveItems']:
        roots = sorted(set(code.root_rva(a) for a in code.string_sites(s) if code.root_rva(a)))
        for r in roots:
            info = code.root_info(r, statics)
            named[s] = {'root': r, 'size': info['size'], 'chunks': info['chunks'],
                        'statics': dict(Counter(info['statics'])), 'consts': dict(info['consts']),
                        'n_callers': len(code.calls.get(r, [])), 'n_jmp_thunks': len(code.jmps.get(r, [])),
                        'jmp_thunks': code.jmps.get(r, [])[:8],
                        'prologue': code.bytes_at(r, 32).hex(),
                        'calls': sorted(set(info['calls']))}
    item['named_functions'] = named
    # call path from MapItemMan request -> AddInventoryEquip
    add_inv = named.get('CS::EquipGameData::AddInventoryEquip', {}).get('root')
    req = named.get('CS::MapItemManImpl::_RequestRegistGetItem', {}).get('root')

    def reach(root, target, depth=4, seen=None):
        seen = seen if seen is not None else set()
        if root in seen or depth < 0:
            return None
        seen.add(root)
        info = code.root_info(root, statics)
        for c in set(info['calls']):
            if c == target:
                return [root, target]
            rr = code.root_rva(c)
            if rr:
                p = reach(rr, target, depth - 1, seen)
                if p:
                    return [root] + p
        return None
    if add_inv and req:
        path = reach(req, add_inv)
        item['path_RequestRegistGetItem_to_AddInventoryEquip'] = path
        if path:
            for r in path[1:-1]:
                info = code.root_info(r, statics)
                item.setdefault('intermediates', {})[r] = {
                    'size': info['size'], 'statics': dict(Counter(info['statics'])), 'consts': dict(info['consts']),
                    'n_callers': len(code.calls.get(r, [])), 'callers': sorted(set(code.root_rva(s) for s in code.calls.get(r, []) if code.root_rva(s))),
                    'prologue': code.bytes_at(r, 40).hex()}
    # prologue AOB hits with evidence
    pro = []
    for n in ('ItemGib_prologue_6C24', 'ItemGib_prologue_AC24'):
        for h in aob_res[n]['hits']:
            info = code.root_info(code.root_rva(h) or h, statics)
            pro.append({'rva': h, 'root': code.root_rva(h), 'size': info['size'], 'chunks': info['chunks'],
                        'statics': dict(Counter(info['statics'])), 'consts': dict(info['consts']), 'strings': info['strings'][:4]})
    item['prologue_aob_hits'] = pro
    # AddInventoryEquip callers (wrappers)
    if add_inv:
        cl = Counter(code.root_rva(s) for s in code.calls.get(add_inv, []) if code.root_rva(s))
        item['AddInventoryEquip_callers'] = [{'root': r, 'n': n, 'size': code.root_info(r, statics)['size'],
                                              'statics': sorted(set(code.root_info(r, statics)['statics']))} for r, n in cl.most_common(12)]
    # scored generic search: roots referencing MapItemMan/GameDataMan/CSItemGetMenuMan + category constants
    targets = {a for a, n in statics.items() if n in ('MapItemMan', 'CSItemGetMenuMan', 'GameDataMan')}
    cands = {}
    for t in targets:
        for a, op in code.xref[t]:
            r = code.root_rva(a)
            if r:
                cands.setdefault(r, set()).add(statics[t])
    rows = []
    for r, names in cands.items():
        info = code.root_info(r, statics)
        cs = info['consts']
        score = 2 * ('MapItemMan' in names) + ('GameDataMan' in names) + 2 * ('CSItemGetMenuMan' in names)
        score += 2 * bool(cs.get('0x40000000')) + 2 * bool(cs.get('0x80000000')) + bool(cs.get('0xF0000000')) + bool(cs.get('0x0FFFFFFF')) + 2 * bool(cs.get('cmp eax,0Ah')) + bool(cs.get('0xC0000000'))
        rows.append({'score': score, 'root': r, 'size': info['size'], 'statics': sorted(names), 'consts': dict(cs),
                     'strings': [s for s in info['strings'] if not s.startswith('W:')][:3]})
    rows.sort(key=lambda x: (-x['score'], x['root']))
    item['scored_candidates'] = rows[:20]
    result['item_give'] = item

    # ---- misc: CSLuaEventManager static from ER AOB (48 83 3D disp 00)
    misc = {}
    if aob_res['CSLuaEventManagerAoB']['n'] == 1:
        h = aob_res['CSLuaEventManagerAoB']['hits'][0]
        misc['cs_lua_event_manager_static_from_ER_AOB'] = code.rip_target(h, 8)
    result['misc'] = misc

    # ---- singleton name -> static
    key_classes = ['CSEventFlagMan', 'WorldChrMan', 'CSMenuMan', 'MapItemMan', 'SoloParamRepository', 'MsgRepository',
                   'CSSystemProperties', 'CSNetMan', 'CSFile', 'CSRegulationManager', 'CSGaitem', 'CSItemGetMenuMan',
                   'CSLuaEventMan', 'CSEventMan', 'CSSessionManager', 'CSTask', 'CSTaskGroup', 'CSFeMan', 'CSTrophy',
                   'CSEventFlagUsageParamManager', 'WorldAreaTime', 'CSFade', 'CSWindow', 'CSHavokMan', 'CSCamera']
    result['key_singletons'] = {k: by_name.get(k) for k in key_classes}

    # write json (hex-ify ints)
    COUNT_KEYS = {'size', 'n', 'n_refs', 'n_sites', 'n_calls', 'n_callers', 'n_jmp_thunks', 'chunks', 'total_refs',
                  'refs_from_tu', 'score', 'alloc_size', 'vsize', 'raw_size', 'lang', 'codepage', 'lang_id_of_resource'}

    def hexify(o, key=None):
        if isinstance(o, dict):
            return {(('%#x' % k) if isinstance(k, int) else k): hexify(v, k) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [hexify(x, key) for x in o]
        if isinstance(o, bool):
            return o
        if isinstance(o, int) and o > 0xfff and key not in COUNT_KEYS:
            return '%#x' % o
        return o
    with open(os.path.join(outdir, 'nightreign_rvas.json'), 'w') as f:
        json.dump(hexify(result), f, indent=1)
    print('[+] wrote nightreign_rvas.json (%.1fs)' % (time.time() - t0))
    return result


if __name__ == '__main__':
    main()
