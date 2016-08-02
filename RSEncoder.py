import PKCS7Encoder
import zfec
import operator

def encode(chunk, T, N):
    """
    Encrypt Chunk using Reed-Solomon Code
    """
    ''' T is number of shares. '''
    padder = PKCS7Encoder.Encoder(T)
    ''' pad the chunk, to multiple of # shares '''
    chunk = padder.encode(chunk)
    l = len(chunk)
    ''' m is size of each share '''
    m = l / T

    ''' T shares '''
    shares = [chunk[i*m:(i+1)*m] for i in range(T)]
    ''' T is # original data piece, N is total data piece '''
    e = zfec.Encoder(T, N)
    ''' d will contain N pieces '''
    d = e.encode(shares)
    ''' only keeping the N parity pieces '''
    return d

def decode(idx, shares, T, N):
    """
    Decrypt chunk using Reed-Solomon Code
    """
    d = zfec.Decoder(T, N)
    #idx = map(operator.add, idx, [T]*len(idx))
    chunk = "".join(d.decode(shares, idx))
    padder = PKCS7Encoder.Encoder(T)
    return padder.decode(chunk)


if __name__=='__main__':
    print '-----------------------'

    chunk = 'abcde00000'
    shares = encode(chunk, 2, 3)
    print shares, map(len, shares)
    chunk_dec = decode([1, 2], shares[1:3], 2, 3)
    print chunk_dec
    print '-----------------------'

    chunk = 'abcdeabcde'
    shares = encode(chunk, 2, 3)
    print shares, map(len, shares)
    chunk_dec = decode([1, 2], shares[1:3], 2, 3)
    print chunk_dec
