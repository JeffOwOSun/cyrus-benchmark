import os
import sys
from hashlib import sha1
import random
import time

from munkres import Munkres, make_cost_matrix

'''
{
    'fdjsfksfjskdfl': {
        'bucket 0', 'bucket 1', ...},
    ...
}
'''
database = dict()
'''
{
    'fjskdfsjkflssf': 1024,
}
'''
fingerprint_sizes = dict()

'''
retrieve list of all files in the dir whose name given
'''
def get_files(dirname):
    ret = []
    for dirname, dirs, files in os.walk(dirname):
        for fname in files:
            ret.append(os.path.join(dirname, fname))
    return ret

'''
1. solve the given similarity matrix
modes:
    hungarian: hungarian assignment
    canonical: sequential assignment
    random: random assignment
'''
def solve(matrix, mode='hungarian'):
    assignments = [i for i in xrange(len(matrix))]
    if mode == 'hungarian':
        m = Munkres()
        indices = m.compute(make_cost_matrix(matrix, lambda x: sys.maxint-x))
        for fileno, bucket in indices:
            assignments[fileno] = bucket
        #print('assignments', assignments)
    elif mode == 'random':
        random.shuffle(assignments)
    else : #canonical
        pass
    return assignments
'''
get the fingerprint of the given file
'''
def get_fingerprint(f, piece_length=1024):
    offset = 0
    fingerprint = []
    while offset < len(f):
        piece = f[offset:offset+piece_length]
        fingerprint.append(sha1(piece).hexdigest())
        '''remember the size of fingerprint for deduplication rate calculation'''
        fingerprint_sizes[fingerprint[-1]] = len(piece)
        offset += piece_length
    return fingerprint, len(f)

'''
1. calculate the similarity score
K is the total number of buckets
prepare for more fingerprint than K, rectify this case by augmenting the matrix
'''
def compare(fingerprints, K=3):
    matrix = []
    ratio = 1
    for fp in fingerprints:
        row = [0]*K
        for piece in fp:
            if not piece in database:
                continue
            for bucket in database[piece]:
                row[bucket] += fingerprint_sizes[piece]
        matrix.append(row)
    #augment the matrix when necessary
    if len(fingerprints) > K:
        '''augment K'''
        ratio = len(fingerprints) / K + 1
        matrix = [row * ratio for row in matrix]
    if len(fingerprints) < ratio * K:
        matrix.extend([[0]*ratio*K]*(ratio*K-len(fingerprints)))
    return matrix

'''
get the score of the assignment
'''
def get_score(matrix, assignment):
    total = 0
    for fileno, bucket in enumerate(assignment):
        total += matrix[fileno][bucket]
    return total

'''
update the database with given fingerprint and assignment
'''
def update(assignment, fingerprints, K=3):
    for idx, bucket in enumerate(assignment):
        #omit the dummy files
        if idx >= len(fingerprints): continue
        for piece in fingerprints[idx]:
            if piece in database:
                database[piece].add(bucket % K)
            else:
                database[piece] = {bucket % K}

def main(dirname, K=3, rand_range=[3, 6], mode='hungarian', piece_length=1024):
    '''
    1. get a file list
    2. open every file
    3. for each file, calculate the fingerprint
    4. compare fingerprint with database and figure out the score matrix
    5. solve score matrix to get assignment
    '''
    database.clear() #clear database
    files = get_files(dirname) #get list of filenames
    count = 0
    totalsize = 0
    idx = 0
    while idx < len(files):
        buf = files[idx:idx+random.randint(*rand_range)]
        idx += len(buf)
        buf = [open(fname, 'r') for fname in buf]
        '''get fingerprint of the file s'''
        fingerprints, sizes = zip(*[get_fingerprint(f.read(), piece_length=piece_length) for f in buf])
        '''total size of the files. statistic for benchmark'''
        totalsize += sum(sizes)
        '''generate the matrix. Augmentation takes place here'''
        matrix = compare(fingerprints, K=K)
        '''solve the matrix to get the assignment'''
        assignment = solve(matrix, mode)
        '''calculate the score of this assignment'''
        score = get_score(matrix, assignment)
        '''update the database'''
        update(assignment, fingerprints, K=K)
        '''count the file size after compression'''
        count += score
    rate = count/float(totalsize)
    #print('T={} N={} K={}, deduplicates {} KB out of {} KB, {}%'.format(T, N, K,
    #    count, totalsize/1024, rate*100))
    return rate, count/1024.0, totalsize/1024.0

if __name__ == '__main__':
    #random.seed(42)
    path = '/Users/jowos/OneDrive'
    if len(sys.argv) > 1:
        path = sys.argv[1]
    print('running on path {}'.format(path))
    K = 3
    rand_range=[3,6]
    start = time.clock()
    rate, dedup, total = main(path, K, rand_range, 'hungarian', 1024)
    elapse = time.clock() - start
    print('rate={} dedup={}K total={}K elapse={}s'.format(rate,dedup,total,elapse))
