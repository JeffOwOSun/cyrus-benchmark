import os
import sys
from hashlib import sha1
import random
import time
from multiprocessing import Pool, TimeoutError

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
file_cache={}
def get_files(dirname):
    if dirname not in file_cache:
        ret = []
        for dirname, dirs, files in os.walk(dirname):
            for fname in files:
                ret.append(os.path.join(dirname, fname))
        file_cache[dirname] = ret
    return file_cache[dirname]

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
fingerprint_cache={}
def get_fingerprint(fname, piece_length=1024):
    if fname not in fingerprint_cache:
        with open(fname, 'r') as f:
            buf = f.read()
            offset = 0
            fingerprint = []
            length = len(buf)
            while offset < length:
                piece = buf[offset:offset+piece_length]
                fingerprint.append(sha1(piece).hexdigest())
                '''remember the size of fingerprint for deduplication rate calculation'''
                fingerprint_sizes[fingerprint[-1]] = len(piece)
                offset += piece_length
            fingerprint_cache[fname] = (fingerprint, length)
    return fingerprint_cache[fname]

'''
1. calculate the similarity score
K is the total number of buckets
prepare for more fingerprint than K, rectify this case by augmenting the matrix
'''
def compare(fingerprints, K=3):
    matrix = []
    ratio = 1
    for fp in fingerprints:
        row = [0 for x in xrange(K)]
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
        matrix.extend([[0 for x in xrange(ratio*K)] for y in xrange(ratio*K-len(fingerprints))])
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

def main(dirname, K=3, rand_range=[3, 6], mode='hungarian', piece_length=1024,
        seed=None):
    '''
    1. get a file list
    2. open every file
    3. for each file, calculate the fingerprint
    4. compare fingerprint with database and figure out the score matrix
    5. solve score matrix to get assignment
    '''
    print("running main with {} {} {} {}".format(dirname, K, rand_range, seed))
    start = time.clock()
    random.seed(seed)
    database.clear() #clear database
    files = get_files(dirname) #get list of filenames
    count = 0
    totalsize = 0
    idx = 0
    while idx < len(files):
        buf = files[idx:idx+random.randint(*rand_range)]
        idx += len(buf)
        '''get fingerprint of the file s'''
        fingerprints, sizes = zip(*[get_fingerprint(fname, piece_length=piece_length) for fname in buf])
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
    elapse = time.clock() - start
    return rate, count/1024.0, totalsize/1024.0, elapse

def wrapped_main(args):
    return main(*args)+args

if __name__ == '__main__':
    #path = '/Users/jowos/Dropbox/SAP Data'
    #if len(sys.argv) > 1:
    #    path = sys.argv[1]
    #print('running on path {}'.format(path))
    #root_path='/Users/jowos/Dropbox/SAP Data'
    root_path='/Volumes/RAM Disk'
    paths = [
            #'/Users/jowos/Dropbox/SAP Data',
            root_path+'/book',
            root_path+'/CNN',
            root_path+'/mp3',
            #'/Users/jowos/Dropbox/SAP Data/UbuntuImage',
            #root_path+'/UbuntuImage/uec-images.ubuntu.com/releases/10.04',
            root_path+'/10.04',
            ]
    num_repetition = 10
    '''warm up'''
    print('warming up...')
    for path in paths:
        main(path, 1, [1,1], 'hungarian', 512)
    '''
    use single processing to calculate the fixed window size situation, so
    that the caches are filled
    '''
    for K in [1, 3]:
        '''rand range 1'''
        rand_range=[1,1]
        with open('sapbenchmark_output_K={}_rand_range={}.csv'.format(K, rand_range), 'w') as f:
            f.write('path,dedup rate,dedup size,total size,elapse time (s)\n')
            for path in paths:
                rate, dedup, total, elapse = main(path, K, rand_range, 'hungarian', 512)
                print('rate={} dedup={}K total={}K elapse={}s'.format(rate,dedup,total,elapse))
                f.write('{},{},{},{},{}\n'.format(path, rate, dedup, total, elapse))

    '''now use multiprocess magic'''
    job_list = []
    for K in [1, 3]:
        rand_range=[3, 6]
        for seed in xrange(num_repetition):
            for path in paths:
                job = (path, K, rand_range, 'hungarian', 512, seed)
                job_list.append(job)
    print(job_list)
    pool = Pool(processes=4)
    ret = pool.map(wrapped_main, job_list, 10)
    '''collect the results under paths'''
    results = { K:{path:[] for path in paths} for K in [1, 3]}
    for record in ret:
        (rate, dedup, total, elapse, path, K, rand_range, alg_type, chunk_size,
        seed) = record
        results[K][path].append((rate, dedup, total, elapse))
    for K in [1,3]:
        '''average them out'''
        averaged_results = { path:(sum(x)/float(num_repetition) for x in zip(*results[K][path])) for path in paths}
        '''write to file'''
        with open('sapbenchmark_output_K={}_rand_range={}.csv'.format(K, [3,6]), 'w') as f:
            f.write('path,dedup rate,dedup size,total size,elapse time (s)\n')
            for path in paths:
                rate, dedup, total, elapse = averaged_results[path]
                print('rate={} dedup={}K total={}K elapse={}s'.format(rate,dedup,total,elapse))
                f.write('{},{},{},{},{}\n'.format(path, rate, dedup, total, elapse))


    """
    for K in [1, 3]:
        '''rand range 3,6'''
        rand_range=[3,6]
        results = { path:[] for path in paths}
        for i in xrange(num_repetition):
            print('repeating for the {} of {} time'.format(i, num_repetition))
            ''' run and record the results '''
            for path in paths:
                rate, dedup, total, elapse = main(path, K, rand_range, 'hungarian', 512)
                results[path].append((rate, dedup, total, elapse))
        averaged_results = { path:(sum(x)/float(num_repetition) for x in zip(*results[path])) for path in paths}
        with open('sapbenchmark_output_K={}_rand_range={}.csv'.format(K, rand_range), 'w') as f:
            f.write('path,dedup rate,dedup size,total size,elapse time (s)\n')
            for path in paths:
                rate, dedup, total, elapse = averaged_results[path]
                print('rate={} dedup={}K total={}K elapse={}s'.format(rate,dedup,total,elapse))
                f.write('{},{},{},{},{}\n'.format(path, rate, dedup, total, elapse))
    """
