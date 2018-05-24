# origin: https://stackoverflow.com/a/3431835/2422655

import hashlib


def _hashBytestrIter(bytesiter, hasher):  # , ashexstr=True):
    for block in bytesiter:
        hasher.update(block)
    return hasher.hexdigest()  # (hasher.hexdigest() if ashexstr else hasher.digest())


def _fileAsBlockiter(path, blocksize=65536):
    with open(path, 'rb') as f:
        block = f.read(blocksize)
        while len(block) > 0:
            yield block
            block = f.read(blocksize)


def fileCheckSum(path):
    '''
    returns the files sha256 checksum e.g.
        '9a5b5701c1ab9150e0cf5effa9aead60a483832b559d8e32377ce1aa6aad7597'
    '''
    _iter = _fileAsBlockiter(path)
    return _hashBytestrIter(_iter, hashlib.sha256())


if __name__ == '__main__':
    from time import time
    t0 = time()
    p = __file__
    print(fileCheckSum(p))
    print('time: ', time() - t0)
