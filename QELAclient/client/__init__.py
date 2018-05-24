'''
Quantitative ElectroLuminescence Analysis
'''
from fancytools.os.PathStr import PathStr

name = 'QELA'
__version__ = '-'  # time stamp, set by server during packaging
__author__ = 'Karl Bedrich'
__email__ = 'karl.bedrich@nus.edu.sg'
__license__ = 'GPLv3'


# MEDIA_PATH = PathStr.getcwd().join('client', 'media') #only works if
# executed from main dir
MEDIA_PATH = PathStr(__file__).dirname().join(
    'media')  # TODO: works in FROZEN?

ICON = MEDIA_PATH.join('logo.svg')
PATH = PathStr.home().mkdir(".%s" % name)
