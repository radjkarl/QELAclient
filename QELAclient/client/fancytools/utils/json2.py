'''
extends json.dumps to also save 
'''
from json import *
from json import dumps as _dumps
import numpy as np


class NumpyEncoder(JSONEncoder):

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        return  JSONEncoder.default(self, obj)


def dumps(*args, **kwargs):
    return _dumps(*args, **kwargs, cls=NumpyEncoder)


if __name__ == '__main__':
    import re

    a = np.array([1, 2, 3])
    b = {'aa': [2, (2, 3, 4), a], 'bb': [2]}
    
    out = dumps(b)
    assert str(out) == '''{"aa": [2, [2, 3, 4], [1, 2, 3]], "bb": [2]}'''

    a = np.arange(100).reshape(10, 10)
    s = dumps(a, indent=4)
    print(s)  # TODO: more compact representation
    
__name__ = 'json'
