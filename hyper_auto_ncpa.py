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
import numpy as np

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Measure and correct several NCPA modes on IRIS or GRAVITY")
    parser.add_argument('--tel', type=int, choices=range(5), help="Telescope index. 0 for all telescopes", required=True)
    parser.add_argument("--modes", metavar=('MIN', 'MAX'), type=int, nargs=2, default=None,
                    help="specify the range of Zernike modes to test (Noll index min and max). Ex: --modes 4 12", required=True) 
    parser.add_argument('--floop', type=int , help="AO loop frequency", required=True)
    parser.add_argument('--inst', type=str , help="IRIS or GRAV", required=True)
    parser.add_argument('--repeat', type=int, default=10, help="number of modulation sequence repetitions")
    args = parser.parse_args()
    
    modes_list = np.arange(args.modes[0],args.modes[1]+1)

    if args.tel==0:
        ut_str="1234"
    elif args.tel in [1,2,3,4]: #one UT measurement
        ut_str =str(args.tel)

    time_start = time.time()
    for i_m, mode in enumerate(modes_list):
        if i_m==0: #record a PSF for the first mode, and load matrices
            os.system(f'python auto_ncpa.py {args.tel} {mode} {args.repeat} {args.floop} {args.inst} -u 0 -p 1 -s 1')
        elif i_m==(len(modes_list)-1): #record a PSF for the last mode
            os.system(f'python auto_ncpa.py {args.tel} {mode} {args.repeat} {args.floop} {args.inst} -u 0 -m 0 -p 1 -s 1')
        else: #save time by not recording another background and not fetching sparta matrices
            os.system(f'python auto_ncpa.py {args.tel} {mode} {args.repeat} {args.floop} {args.inst} -b 0 -m 0 -u 0 -p 0 -s 1')
    time_stop = time.time()
    print(f'Measurements and correction from Zernike Noll#{args.modes[0]} to #{args.modes[1]} from UT{ut_str} to {args.inst} finished \n')
    print('Lasted {0:.2f} minutes'.format( (time_stop-time_start)/60))
