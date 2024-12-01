#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct  9 16:56:02 2024

@author: pourren
"""
import os
import argparse
import time

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate the disturbance matrices")
    parser.add_argument('tel', type=int, choices=range(5), help="Telescope index. 0 for all telescopes")
    parser.add_argument('mode', type=int , help="mode Noll index")
    parser.add_argument('repeat', type=int , help="number of modulation sequence repetitions")
    parser.add_argument('floop', type=int , help="AO loop frequency")
    parser.add_argument('inst', type=str , help="IRIS or GRAV")
    parser.add_argument('--background','-b', type=int,default=1 , help="Do we record a background or not. 0/1")
    parser.add_argument('--timepermode','-t',type=int,default=1.5, help='time permode (sec)')
    parser.add_argument('--get_matrices','-m',type=int, default=1, help="Do we fetch SPARTA matrices. O/1")
    args = parser.parse_args()
    
    if args.tel==0:
        utstr="1234"
    elif args.tel in [1,2,3,4]: #one UT measurement
        utstr =str(args.tel)
    else:
        print("WRONG TELESCOPE NUMBER")
    print("CORRECTING NOLL {0} on UT{1} with {2} repetitions for the modulation, {3} seconds per modulation element".format(args.mode,utstr,args.repeat,args.timepermode))
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
    if args.inst == "IRIS":
        duration_acq = (((args.timepermode+0.5) * args.repeat) + 2) / 1.5 + 20 # IRIS with DIT of 1 ms has a 1.5 ms frame rate
        os.system('python 2_iris_ncpa.py {0} {1} {2} -d {3} -b {4}'.format(args.tel, args.mode, args.floop, duration_acq, args.background ))
    elif args.inst == "GRAV":
        duration_acq = ((args.timepermode+1) * args.repeat) + 30
        os.system('python 2_modulation_acq.py {0} {1} {2} {4} -d {3} -b {5} -i 0.01'.format(args.tel, args.mode, args.repeat, duration_acq, args.floop ,args.background))
    else:
        print("WRONG INSTRUMENT NAME")
        raise ValueError('INST not known')
    
    print("################")
    print("Process IRIS/SC images to extract NCPA")
    print("################")
    time.sleep(25)
    if args.inst == "IRIS":
        os.system('python 3_process_ncpa.py {0} {1} {2} {3} {4} --t {5}'.format(args.tel, args.mode, args.repeat, args.floop, args.timepermode))
    elif args.inst == "GRAV":
        os.system('python 3_process_ncpa_grav.py {0} {1} {2} {3}'.format(args.mode, args.amplitude_slow, args.repeat, args.floop))
    else:
        print("WRONG INSTRUMENT NAME")
        raise ValueError('INST not known')    
        
    print("################")
    print("Apply NCPA")
    print("################")
    time.sleep(1)
    os.system('python 4_apply_ncpa.py {0} {1}'.format(args.tel, args.mode))
