#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct  9 16:56:02 2024

@author: pourren
"""
import os
import argparse
import time
from datetime import datetime
import subprocess

def exists_remote(host, path):
    """Test if a file exists at path on a host accessible with SSH."""
    status = subprocess.call(
        ['ssh', host, 'test -f {}'.format(shlex.quote(path))])
    if status == 0:
        return True
    if status == 1:
        return False
    raise Exception('SSH failed')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate the disturbance matrices")
    parser.add_argument('tel', type=int, choices=range(5), help="Telescope index. 0 for all telescopes")
    parser.add_argument('mode', type=int , help="mode Noll index")
    parser.add_argument('repeat', type=int , help="number of modulation sequence repetitions")
    parser.add_argument('floop', type=int , help="AO loop frequency")
    parser.add_argument('inst', type=str , help="IRIS or GRAV")
    parser.add_argument('--background','-b', type=int,default=1 , help="Do we record a background or not. 0/1")
    parser.add_argument('--timepermode','-t',type=float,default=1.5, help='time permode (sec)')
    parser.add_argument('--get_matrices','-m',type=int, default=1, help="Do we fetch SPARTA matrices. O/1")
    args = parser.parse_args()
    
    if args.tel==0:
        ut_str="1234"
    elif args.tel in [1,2,3,4]: #one UT measurement
        ut_str =str(args.tel)
    else:
        print("WRONG TELESCOPE NUMBER")
    print("CORRECTING NOLL {0} on UT{1} with {2} repetitions for the modulation, {3} seconds per modulation element".format(args.mode,ut_str,args.repeat,args.timepermode))
    if args.get_matrices==1:
        print("################")
        print("Get matrices")
        print("################")
        os.system('python 0_get_matrices.py {0}'.format(args.tel))
    else:
        print('Skipped get_matrices')
    
    print("################")
    print("Generate perturbation element")
    print("################")
    os.system('python 1_generate_disturbance_files.py {0} {1} {2} {3} -t {4}'.format(args.tel, args.mode, args.repeat, args.floop, args.timepermode))
    
    print("################")
    print("Launch IRIS/SC acquisition and GPAO disturbance")
    print("################")
    tStart = datetime.utcnow().isoformat()[:-7]
    if args.inst == "IRIS":
        name_acquisition = "IrisNcpa_{0}_noll{1}_UT{2}".format(tStart, args.mode, ut_str)
        duration_acq = (((args.timepermode+0.5) * args.repeat) + 1.5) + 10 
        os.system('python 2_iris_ncpa.py {0} {1} {2} {3} -d {4} -b {5}'.format(args.tel, args.mode, args.floop, name_acquisition, duration_acq, args.background ))
    elif args.inst == "GRAV":
        name_acquisition = "GravNcpa_{0}_noll{1}_UT{2}".format(tStart, args.mode, ut_str)
        duration_acq = (((args.timepermode+0.5) * args.repeat) +1.5) + 10
        os.system('python 2_modulation_acq.py {0} {1} {2} {3} -d {4} -b {5} -i 0.01'.format(args.tel, args.mode, args.repeat, args.floop, name_acquisition, duration_acq, args.background))
    else:
        print("WRONG INSTRUMENT NAME")
        raise ValueError('INST not known')
    
    print("################")
    print("Process IRIS/SC images to extract NCPA")
    print("################")
    timeout_time = 300 #s
    if args.inst == "IRIS":
        #Wait for file on the remote server
        start_time = time.time()
        while not exists_remote('aral@waral', '$INS_ROOT/SYSTEM/DETDATA/{0}_DIT.fits'.format(name_acquisition)):
            time.sleep(1)
            if (time.time()-start_time) > timeout_time:
                raise RuntimeError('Maximal waiting time reached')
        print("File found!")
        os.system('python 3_process_ncpa_iris.py {0} {1} {2} {3} {4} -t {5}'.format(args.tel, args.mode, args.repeat, args.floop, name_acquisition, args.timepermode))
    elif args.inst == "GRAV":
        #Wait for file on the remote server
        start_time = time.time()
        while not exists_remote('grav@wgv', "$INS_ROOT/SYSTEM/DETDATA/{0}_DIT.fits".format(name_acquisition)):
            time.sleep(1)
            if (time.time()-start_time) > timeout_time:
                raise RuntimeError('Maximal waiting time reached')
        print("File found!")
        os.system('python 3_process_ncpa_grav.py {0} {1} {2} {3} -t {4}'.format(args.mode, args.repeat, args.floop, name_acquisition, args.timepermode))
    else:
        print("WRONG INSTRUMENT NAME")
        raise ValueError('INST not known')    
        
    print("################")
    print("Apply NCPA")
    print("################")
    time.sleep(1)
    os.system('python 4_apply_ncpa.py {0} {1} {2}'.format(args.tel, args.mode, name_acquisition))
