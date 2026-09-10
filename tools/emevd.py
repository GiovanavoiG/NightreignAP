"""Minimal Elden Ring / Nightreign EMEVD reader (64-bit). Returns events with (bank, id, args bytes)."""
import struct, sys
def read(path):
    d=open(path,"rb").read(); assert d[:4]==b"EVD\0"
    q=lambda o: struct.unpack_from("<q", d, o)[0]
    version=struct.unpack_from("<i", d, 8)[0]
    ev_count, ev_off = q(0x10), q(0x18)
    ins_count, ins_off = q(0x20), q(0x28)
    # 0x30 unk count/off, 0x40 layers, 0x50 params, 0x60 linked files, 0x70 args, 0x80 strings
    args_len, args_off = q(0x70), q(0x78)
    events=[]
    for i in range(ev_count):
        o=ev_off+i*0x30
        eid, icount, ioff = q(o), q(o+8), q(o+0x10)
        ins=[]
        for j in range(icount):
            io=ins_off+ioff*0x20 if ioff < ins_count else ioff+j*0x20
            io=io if ioff>=ins_count else ins_off+(ioff+j)*0x20
            bank, iid = struct.unpack_from("<ii", d, io); alen, aoff = q(io+8), q(io+0x10)
            ins.append((bank, iid, d[args_off+aoff:args_off+aoff+alen]))
        events.append((eid, ins))
    return version, events
if __name__=="__main__":
    v,ev=read(sys.argv[1]); print("version",v,"events",len(ev), "instructions", sum(len(i) for _,i in ev))
