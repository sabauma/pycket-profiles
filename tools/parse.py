
import json
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas
import seaborn as sns
import urllib
import sys

try:
    # For Python 3.0 and later
    from urllib.request import urlopen
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen

CODESPEED_URL = 'http://localhost:8000/'

def add(data):
    response = "None"
    try:
        encoded = urllib.parse.urlencode(data).encode('utf-8')
        f = urlopen(CODESPEED_URL + 'result/add/json/', encoded)
    except urllib.request.URLError as e:
        print(str(e))
        print(e.read())
        return
    response = f.read()
    f.close()
    print("Server ({}) response: {}\n".format(CODESPEED_URL, response))

names = ("timestamp" , "value" , "unit" , "criterion" , "benchmark" , "vm" , "suite" , "extra_args" , "warmup" , "cores" , "input_size" , "variable_values")
types = (str         , float   , str    , str         , str         , str  , str     , str          , str      , int     , str          , str              )
dtype = dict(zip(names, types))

def fname_to_shas(fname):
    fname = os.path.basename(fname)
    fname = os.path.splitext(fname)[0]
    fname = fname.split('_')
    return fname

class Converter(object):

    def __init__(self, debug=False):
        self.debug = debug
        self.data = []

    def add_file(self, fname):

        data = pandas.read_csv(fname, delimiter="\t", comment="#", names=names, dtype=dtype)
        data = data[data.criterion == 'cpu']
        data['value'] = data['value'].apply(lambda x: x / 1000.0)

        means = data.groupby(['benchmark', 'vm']).mean().reset_index()
        vars  = data.groupby(['benchmark', 'vm']).std().reset_index()

        pycket_sha, pypy_sha = fname_to_shas(fname)

        for (i, mean), (j, std) in zip(means.iterrows(), vars.iterrows()):
            vm = mean.vm
            d = { 'commitid'     : pycket_sha
                , 'project'      : 'Pycket'
                , 'branch'       : 'default'
                , 'executable'   : mean.vm
                , 'benchmark'    : mean.benchmark
                , 'environment'  : 'Cutter'
                , 'result_value' : mean.value
                , 'std_dev'      : std.value }
            self.data.append(d)

    def send(self):
        if self.debug:
            for val in self.data:
                print(val)

        add({'json': json.dumps(self.data)})
        self.data = []

if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        sys.exit(0)

    if args[0] == "--debug":
        debug = True
        args = args[1:]
    else:
        debug = False

    converter = Converter(debug)
    for fname in sys.argv[1:]:
        converter.add_file(fname)
    converter.send()

