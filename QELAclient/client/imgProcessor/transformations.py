# coding=utf-8
'''
various image transformation functions
'''

import numpy as np


def uintMaxVal(dtype):
    '''returns largest possible value of given type'''
    return 2 ** (np.dtype(dtype).itemsize * 8) - 1


def _prepRange(range, img, dtype, b):
    mn, mx = range
    if b is None:
        b = uintMaxVal(dtype)
    img = np.array(img, dtype=float)
    return mn, mx, img, b


def applyRange(img, range, dtype, b=None):
    mn, mx, img, b = _prepRange(range, img, dtype, b)
    if mx != mn:
        img -= mn
        img *= b / (mx - mn)
    elif mx != 0:
        img *= b / mx
    return np.clip(img, 0, b)


def reverseRange(img, range, dtype=None, b=None):
    '''
    a = np.array([1, 4, 8])
    b = applyRange(a, (-1, 8), np.uint8)
    c = reverseRange(b, (-1, 8), np.uint8)
    assert np.allclose(a , c)
    '''
    if dtype is None:
        dtype = img.dtype
    mn, mx, img, b = _prepRange(range, img, dtype, b)
    img *= (mx - mn) / b  # scale 0...1
    img += mn
    return img


def toUIntArray(img, dtype=None, cutNegative=True, cutHigh=True,
                range=None, copy=True):
    '''
    transform a float to an unsigned integer array of a fitting dtype
    adds an offset, to get rid of negative values

    range = (min, max) - scale values between given range

    cutNegative - all values <0 will be set to 0
    cutHigh - set to False to rather scale values to fit
    '''
    mn, mx = None, None
    if range is not None:
        mn, mx = range

    if dtype is None:
        if mx is None:
            mx = np.nanmax(img)
        dtype = np.uint16 if mx > 255 else np.uint8

    dtype = np.dtype(dtype)
    
    if dtype == img.dtype and range is None:
        return img

    assert dtype.kind == 'u', 'dtype has to be uint#'

    b = uintMaxVal(dtype)

    if copy:
        img = img.copy()

    if range is not None:
        img = applyRange(img, (mn, mx), dtype, b)
    else:
        if cutNegative:
            with np.errstate(invalid='ignore'):
                img[img < 0] = 0
        else:
            # add an offset to all values:
            mn = np.nanmin(img)
            if mn < 0:
                img -= mn  # set minimum to 0

        if cutHigh:
            # ind = img > b
            with np.errstate(invalid='ignore'):
                img[img > b] = b
        else:
            # scale values
            mx = np.nanmax(img)
            img = np.asfarray(img) * (float(b) / mx)

    img = img.astype(dtype)

#     if range is not None and cutHigh:
#         img[ind] = b
    return img


def toFloatArray(img):
    '''
    transform an unsigned integer array into a
    float array of the right size
    '''
    _D = {1: np.float32,  # (u)int8
          2: np.float32,  # (u)int16
          4: np.float64,  # (u)int32
          8: np.float64}  # (u)int64
    return img.astype(_D[img.itemsize])


def toNoUintArray(arr):
    '''
    cast array to the next higher integer array
    if dtype=unsigned integer
    '''
    d = arr.dtype
    if d.kind == 'u':
        arr = arr.astype({1: np.int16,
                          2: np.int32,
                          4: np.int64}[d.itemsize])
    return arr


def isImage(img):
    return (img.ndim == 2 or (img.ndim == 3 
                              and img.shape[2] in (3, 4))  # RGB or RGBa
            and img.shape[0] > 0 and img.shape[1] > 0 
            )


def isColor(img):
    return img.ndim in (3, 4) and img.shape[-1] in (3, 4)


def toColor(img):
    # color order is assumed to be RGB (red,  green, blue)
    s = img.shape
    if len(s) == 2:  # one gray scale img
        out = np.empty((s[0], s[1], 3), dtype=img.dtype)
        out[:, :, 0] = img  # *(1/3.0)#0.114
        out[:, :, 1] = img  # *(1/3.0)#0.587
        out[:, :, 2] = img  # *(1/3.0)#0.299
    elif len(s) == 3:  # mutliple gray scale images
        out = np.empty((s[0], s[1], s[2], 3), dtype=img.dtype)
        out[:, :, :, 0] = img  # *(1/3.0)#0.114
        out[:, :, :, 1] = img  # *(1/3.0)#0.587
        out[:, :, :, 2] = img  # *(1/3.0)#0.299
    else:
        # assume is already multilayer color img
        return img
    return out


def toGray(img):
    '''
    weights see
    https://en.wikipedia.org/wiki/Grayscale#Colorimetric_.28luminance-prese
    http://docs.opencv.org/2.4/modules/imgproc/doc/miscellaneous_transformations.html#cvtcolor
    '''
    if not isColor(img):
        return img
    w = [0.299,  # red
             0.587,  # green
             0.114]  # blue
    if img.shape[2] == 4:
        w.append(1)  # alpha
    return np.average(img, axis=-1, weights=w).astype(img.dtype)


def rgChromaticity(img):
    '''
    returns the normalized RGB space (RGB/intensity)
    see https://en.wikipedia.org/wiki/Rg_chromaticity
    '''
    out = _calc(img)
    if img.dtype == np.uint8:
        out = (255 * out).astype(np.uint8)
    return out


def _calc(img):
    out = np.empty_like(img, dtype=float)
    f = img.sum(axis=2)
    for n in range(3):
        out[..., n] = img[..., n] / f
    return out


def monochromaticWavelength(img):
    '''
    TODO##########
    '''
    # peak wave lengths: https://en.wikipedia.org/wiki/RGB_color_model
    out = _calc(img)

    peakWavelengths = (570, 540, 440)  # (r,g,b)
#     s = sum(peakWavelengths)
    for n, p in enumerate(peakWavelengths):
        out[..., n] *= p
    return out.sum(axis=2)


def transpose(img):
    if type(img) in (tuple, list) or img.ndim == 3:
        if img.shape[2] == 3:  # is color
            return np.transpose(img, axes=(1, 0, 2))
        return np.transpose(img, axes=(0, 2, 1))
    else:
        return img.transpose()


def isRot90(shape1, shape2):
    s00, s01 = shape1[:2]
    s10, s11 = shape2[:2]
    return s00 == s11 and s01 == s10


def rot90(img):
    '''
    rotate one or multiple grayscale or color images 90 degrees
    '''
    s = img.shape
    if len(s) == 3:
        if s[2] in (3, 4):  # color image
            return np.rot90(img, axes=(1, 2))
#             out = np.empty((s[1], s[0], s[2]), dtype=img.dtype)
#             for i in range(s[2]):
#                 out[:, :, i] = np.rot90(img[:, :, i])
        else:  # mutliple grayscale
            out = np.empty((s[0], s[2], s[1]), dtype=img.dtype)
            for i in range(s[0]):
                out[i] = np.rot90(img[i])
    elif len(s) == 2:  # one grayscale
        out = np.rot90(img)
    elif len(s) == 4 and s[3] in (3, 4):  # multiple color
        out = np.empty((s[0], s[2], s[1], s[3]), dtype=img.dtype)
        for i in range(s[0]):  # for each img
            for j in range(s[3]):  # for each channel
                out[i, :, :, j] = np.rot90(img[i, :, :, j])
    else:
        NotImplemented
    return out

