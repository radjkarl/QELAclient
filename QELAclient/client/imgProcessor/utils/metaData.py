'''
Created on 9 Feb 2018

@author: serkgb
'''
import exifread
from fractions import Fraction


def metaData(path):
    '''
    returns images meta data (date, expTime, iso, fnumber)
       e.g. '2016/08/16 13:56:36', 5.0, 1600, 1.8
    '''
    # Open image file for reading (binary mode)
    with open(path, 'rb') as f:
        # Return Exif tags
        tags = exifread.process_file(f)
        # e.g. '2016:08:16 13:56:36'
        date = str(tags.get('EXIF DateTimeOriginal', ''))
        try:
            i = date.index(' ')
        except ValueError:
            return '', '', '', ''
        date = date[:i].replace(':', '/') + date[i:]
        expTime = str(tags.get('EXIF ExposureTime', ''))  # e.g. '5'
        iso = str(tags.get('EXIF ISOSpeedRatings', ''))  # e.g. '1600'
        fnumber = str(tags.get('EXIF FNumber', ''))
        if fnumber:
            fnumber = str(float(Fraction(fnumber)))  # '9/5' --> '1.8'

        return date, expTime, iso, fnumber
