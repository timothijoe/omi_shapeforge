"""Local framed JSON/NumPy RPC; no pickle or network listening socket."""
import io,json,struct
import numpy as np

LIMIT=32*1024*1024

def receive_exact(sock,size):
    parts=[]
    while size:
        part=sock.recv(size)
        if not part:raise EOFError('Isaac worker disconnected')
        parts.append(part);size-=len(part)
    return b''.join(parts)

def send(sock,metadata,arrays=None):
    stream=io.BytesIO();np.savez(stream,__metadata__=np.frombuffer(json.dumps(metadata,allow_nan=False).encode(),dtype=np.uint8),**(arrays or {}))
    data=stream.getvalue()
    if len(data)>LIMIT:raise ValueError('RPC payload too large')
    sock.sendall(struct.pack('!I',len(data))+data)

def receive(sock):
    size=struct.unpack('!I',receive_exact(sock,4))[0]
    if not 0<size<=LIMIT:raise ValueError('invalid RPC message size')
    with np.load(io.BytesIO(receive_exact(sock,size)),allow_pickle=False) as archive:
        metadata=json.loads(archive['__metadata__'].tobytes())
        arrays={k:archive[k].copy() for k in archive.files if k!='__metadata__'}
    return metadata,arrays
