import numpy as np
from PyQt5 import QtGui

#
# https://kogs-www.informatik.uni-hamburg.de/~meine/software/vigraqt/qimage2ndarray.py


def qImageToArray(qimage, dtype='array'):
    """Convert QImage to numpy.ndarray.  The dtype defaults to uint8
    for QImage.Format_Indexed8 or `bgra_dtype` (i.e. a record array)
    for 32bit color images.  You can pass a different dtype to use, or
    'array' to get a 3D uint8 array for color images."""

    result_shape = (qimage.height(), qimage.width())
    temp_shape = (qimage.height(),
                  qimage.bytesPerLine() * 8 // qimage.depth())

    buf = qimage.bits().asstring(qimage.byteCount())
    
    if qimage.format() in (QtGui.QImage.Format_ARGB32_Premultiplied,
                           QtGui.QImage.Format_ARGB32,
                           QtGui.QImage.Format_RGB32):
        if dtype == 'rec':
            dtype = np.dtype({'b': (np.uint8, 0),
                              'g': (np.uint8, 1),
                              'r': (np.uint8, 2),
                              'a': (np.uint8, 3)})
        elif dtype == 'array':
            dtype = np.uint8
            result_shape += (4,)
            temp_shape += (4,)
    elif qimage.format() in (QtGui.QImage.Format_Indexed8, QtGui.QImage.Format_Grayscale8):
        dtype = np.uint8
    elif  qimage.format() == 1:  # boolean(1bit) image
        dtype = np.uint8
        temp_shape2 = (qimage.height(), qimage.bytesPerLine() // qimage.depth())
        result = np.frombuffer(buf, dtype).reshape(temp_shape2)
        return np.unpackbits(result).reshape(temp_shape)
    else:
        raise ValueError("qimage2numpy only supports 32bit, 8bit and 1bit images")
    
    # FIXME: raise error if alignment does not match
    result = np.frombuffer(buf, dtype).reshape(temp_shape)
    if result_shape != temp_shape:
        result = result[:, :result_shape[1]]
    if qimage.format() == QtGui.QImage.Format_RGB32 and dtype == np.uint8:
        # case byteorder == 'little'
        result = result[..., :3]
        # byteorder == 'big' -> get ARGB
        result = result[..., ::-1]
    return result
