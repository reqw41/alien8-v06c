import sys,zlib,struct
def conv(src,dst,scale=2):
    d=open(src,'rb').read()
    # P5\nW H\n255\n
    parts=d.split(b'\n',3); w,h=map(int,parts[1].split()); px=parts[3]
    raw=b''
    for y in range(h):
        for _ in range(scale):
            row=bytearray([0])
            for x in range(w):
                row += bytes([px[y*w+x]])*scale
            raw+=bytes(row)
    def chunk(t,data):
        c=struct.pack('>I',len(data))+t+data
        return c+struct.pack('>I',zlib.crc32(t+data)&0xffffffff)
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w*scale,h*scale,8,0,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
    open(dst,'wb').write(png)
conv(sys.argv[1],sys.argv[2])
