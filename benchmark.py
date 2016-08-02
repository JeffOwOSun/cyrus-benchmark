import os
import sys
from hashlib import sha1

from munkres import Munkres, make_cost_matrix

import RSEncoder

'''
{
    'fdjsfksfjskdfl': {
        'bucket 0', 'bucket 1', ...},
    ...
}
'''
database = dict()

def get_files(dirname):
    ret = []
    for dirname, dirs, files in os.walk(dirname):
        for fname in files:
            ret.append(os.path.join(dirname, fname))
    return ret

'''
1. solve the given similarity matrix
'''
def solve(matrix):
    m = Munkres()
    indices = m.compute(make_cost_matrix(matrix, lambda x: sys.maxint-x))
    assignments = [0]*len(matrix)
    total = 0
    for share, bucket in indices:
        assignments[share] = bucket
        total += matrix[share][bucket]
    #print('assignments', assignments)
    return assignments, total

def get_fingerprint(f, T=2, N=3, piece_length=1024):
    ''' encode the original file into shares '''
    shares = RSEncoder.encode(f, T, N)
    retval = []
    size = 0
    for share in shares:
        size += len(share)
        offset = 0
        fingerprint = [] #fingerprint for each share
        while offset < len(share):
            piece = share[offset:offset+piece_length]
            fingerprint.append(sha1(piece).hexdigest())
            offset += piece_length
        retval.append(fingerprint)
    return retval, size

'''
1. calculate the similarity score
K is the total number of buckets
'''
def compare(fingerprint, K=3):
    matrix = []
    for share in fingerprint:
        row = [0]*K
        for piece in share:
            if not piece in database:
                continue
            for bucket in database[piece]:
                row[bucket] += 1
        matrix.append(row)
    #matrix = [[1,2,3],[4,5,6],[7,8,9]]
    return matrix

'''
update the database with given fingerprint and assignment
'''
def update(assignment, fingerprint):
    for idx, bucket in enumerate(assignment):
        for piece in fingerprint[idx]:
            if piece in database:
                database[piece].add(bucket)
            else:
                database[piece] = {bucket}

def main(dirname, T=2, N=3, K=3):
    '''
    1. get a file list
    2. open every file
    3. for each file, calculate the fingerprint
    4. compare fingerprint with database and figure out the score matrix
    5. solve score matrix to get assignment
    '''
    database.clear() #clear database
    files = get_files(dirname)
    count = 0
    totalsize = 0
    for idx, fname in enumerate(files):
        #print('\r{}/{} {}'.format(idx, len(files), fname)),
        with open(fname, 'r') as f:
            fingerprint, size = get_fingerprint(f.read(), T=T, N=N)
            totalsize += size
            matrix = compare(fingerprint, K=K)
            assignment, score = solve(matrix)
            update(assignment, fingerprint)
            count += score
    rate = count/(totalsize/1024.0)
    #print('T={} N={} K={}, deduplicates {} KB out of {} KB, {}%'.format(T, N, K,
    #    count, totalsize/1024, rate*100))
    return rate, count, totalsize/1024

if __name__ == '__main__':
    path = '/Users/jowos/OneDrive'
    for N in xrange(3, 9):
        for T in xrange(2, N+1):
            print('T={} N={} {}'.format(T,N,main(path, T, N, N)))
