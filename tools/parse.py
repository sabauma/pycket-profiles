
import json
import os
import pandas
import urllib
import sys

CODESPEED_URL = 'http://localhost:8000/'

def add(data):
    response = "None"
    try:
        encoded = urllib.parse.urlencode(data).encode('utf-8')
        f = urllib.request.urlopen(CODESPEED_URL + 'result/add/json/', encoded)
    except urllib.request.URLError as e:
        print(str(e))
        print(e.read())
        return
    response = f.read().decode('utf-8')
    f.close()
    print("Server ({}) response: {}".format(CODESPEED_URL, response))

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

        info = fname_to_shas(fname)
        pycket_sha, pypy_sha, *info = info
        if info:
            branch, *info = info
            if branch == 'master':
                branch = 'default'
        else:
            branch = 'default'

        for (_, mean), (_, std) in zip(means.iterrows(), vars.iterrows()):
            d = { 'commitid'     : pycket_sha
                , 'project'      : 'Pycket'
                , 'branch'       : branch
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
            return

        add({'json': json.dumps(self.data)})
        self.data = []

def main(go, args):
    if not go:
        return
    if args[0] == "--debug":
        debug = True
        args = args[1:]
    else:
        debug = False

    infile = None
    try:
        infile = open('finished', 'r')
    except OSError:
        already_added = set()
    else:
        already_added = set(f.strip() for f in infile.readlines())
    finally:
        if infile is not None:
            infile.close()

    converter = Converter(debug)
    for fname in args:
        if fname not in already_added:
            converter.add_file(fname)
    converter.send()

    with open('finished', 'a') as outfile:
        for fname in args:
            if fname not in already_added:
                print(fname, file=outfile)


main(__name__ == '__main__', sys.argv[1:])

