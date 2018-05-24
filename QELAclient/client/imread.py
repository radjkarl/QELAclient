from PyQt5 import QtGui
from imgProcessor.reader.qImageToArray import qImageToArray
from tifffile import imread as tiffimread


def imread(path):
    if path.endswith('tif') or path.endswith('tiff'):
        return tiffimread(path)
    # cv2 dll are huge - rather only use PyQt5
    qimage = QtGui.QImageReader(path).read()
    return qImageToArray(qimage)
