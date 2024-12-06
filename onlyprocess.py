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
import shlex
from astropy.io import fits
import numpy as np

from D_process_ncpa_iris import D_process_ncpa_iris
from D_process_ncpa_grav import D_process_ncpa_grav
from E_apply_ncpa import E_apply_ncpa
from iris_acq_function import iris_acquisition
from display_psf_function import display_psf

def exists_remote(host, path):
    """Test if a file exists at path on a host accessible with SSH."""
    status = subprocess.call(
        ['ssh', host, 'test -f {}'.format(shlex.quote(path))])
    if status == 0:
        return True
    if status == 1:
        return False
    raise Exception('SSH failed')

def iris_file_exists(name_acquisition,timeout_time,temp_folder):
    start_time = time.time()
    terminated = False
    while not exists_remote('aral@waral', '/data/ARAL/INS_ROOT/SYSTEM/DETDATA/{0}_DIT.fits'.format(name_acquisition)):
        time.sleep(1)
        if (time.time()-start_time) > timeout_time:
            raise RuntimeError('Maximal waiting time reached')
    print("File found!")
    while not terminated:
        download_latest_file('aral@waral','/data/ARAL/INS_ROOT/SYSTEM/DETDATA/' , '{0}_DIT.fits'.format(name_acquisition), temp_folder)
        try:
            fits.getdata(os.path.join(temp_folder,'{0}_DIT.fits'.format(name_acquisition)),0)
        except:
            time.sleep(0.1)
        else:
            terminated = True
    return True

def grav_file_exists(name_acquisition,timeout_time,temp_folder):
    start_time = time.time()
    terminated = False  
    while not exists_remote('grav@wgv', '/data/GRAVITY/INS_ROOT/SYSTEM/DETDATA/{0}_DIT.fits'.format(name_acquisition)):
        time.sleep(1)
        if (time.time()-start_time) > timeout_time:
            raise RuntimeError('Maximal waiting time reached')
    print("File found!")
    while not terminated:
        download_latest_file('grav@wgv','/data/GRAVITY/INS_ROOT/SYSTEM/DETDATA/' , '{0}_DIT.fits'.format(name_acquisition), temp_folder)
        try:
            fits.getdata(os.path.join(temp_folder,'{0}_DIT.fits'.format(name_acquisition)),0)
        except:
            time.sleep(0.1)
        else:
            terminated = True
    return True

def download_latest_file(server, remote_dir, name, local_dir):
    # Construct the command to find the latest file with the given name
    find_command = (
        f"""FILE=$(ssh {server} "ls -tp {remote_dir}/{name} 2>/dev/null | head -n 1"); """
        f"""if [ -n "$FILE" ]; then scp {server}:$FILE {local_dir}; """
        f"""else echo 'No files found with the name {name}'; fi"""
    )
    
    # Execute the command
    result = os.system(find_command)
    
    if result == 0:
        print("File downloaded successfully.")
    else:
        print("An error occurred during the download.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Measure one NCPA mode on IRIS or in GRAVITY SC")
    parser.add_argument('tel', type=int, choices=range(5), help="Telescope index. 0 for all telescopes")
    parser.add_argument('mode_start', type=int , help="start mode Noll index")
    parser.add_argument('mode_end', type=int , help="end mode Noll index")
    parser.add_argument('repeat', type=int , help="number of repetitions")
    parser.add_argument('sequence', type=str , help="SEQ/PAR. SEQ = sequential = one mode corrected after another. PAR = parallel = measure all modes, correct all modes")
    parser.add_argument('floop', type=int , help="AO loop frequency")
    parser.add_argument('inst', type=str , help="IRIS or GRAV")
    parser.add_argument('--timepermode','-t',type=float,default=1.5, help='time permode (sec)')
    parser.add_argument('--user_input','-u', type=int,default=1 , help="Ask for user validation to apply ncpa. 0/1")
    parser.add_argument('--psf_display','-p', type=int,default=0 , help="Show IRIS PSF before and after correction. 0/1")
    parser.add_argument('--silent','-s', type=int,default=0 , help="Prevent popups. 0/1")
    args = parser.parse_args()
    
    temp_folder = '/vltuser/iss/temp_ncpa/'
    timeout_time = 300 #s limit for checking when file exists
    iZs = np.arange(args.mode_start, args.mode_end+1)

##################
###    IRIS    ###
################## 
    recorded_names = np.load(os.path.join(temp_folder,'names_acqs.npy'))
    for i_n, nam in enumerate(recorded_names):
        print(f'{i_n} : {nam}')
    choice = input('Which file to process?')
    choice = int(choice)
    tStart = recorded_names[choice].split('_')[1]
    if args.inst == "IRIS":
        if args.sequence=="PAR": #one acquisition with "repeat" of all the modes
            name_acquisition = recorded_names[choice]
            if iris_file_exists(name_acquisition,timeout_time,temp_folder):
                print("################")
                print("Process IRIS images to extract NCPA")
                print("################")
                D_process_ncpa_iris(args.tel, args.mode_start, args.mode_end, args.repeat, args.floop, name_acquisition, args.timepermode, args.silent, temp_folder, args.sequence)
            else:
                raise OSError('Cannot find IRIS file')
            print("################")
            print("Apply NCPA")
            print("################")
            if args.psf_display==1:
                iris_acquisition(3,'IrisAcq_beforecorr_{0}'.format(tStart))
            #Check existence of NCPA file
            start_time = time.time()
            while not os.path.exists(os.path.join(temp_folder,'NCPA_{0}.npy'.format(name_acquisition))):
                time.sleep(1)
                if (time.time()-start_time) > timeout_time:
                    raise RuntimeError('Maximal waiting time reached')
            ### APPLY NCPA ###
            E_apply_ncpas(args.tel, args.mode_start, args.mode_end, name_acquisition, args.sequence, args.user_input, temp_folder)
            time.sleep(1)
            if args.psf_display==1:
                iris_acquisition(3,'IrisAcq_aftercorr_{0}'.format(tStart))
                while not exists_remote('aral@waral', '/data/ARAL/INS_ROOT/SYSTEM/DETDATA/IrisAcq_aftercorr_{0}_DIT.fits'.format(tStart)):
                    time.sleep(1)
                    if (time.time()-start_time) > timeout_time:
                        raise RuntimeError('Maximal waiting time reached')
                display_psf (args.tel, tStart, args.silent, temp_folder)

        elif args.sequence=="SEQ": #one acquisition with "repeat" of all the modes
            name_acquisition = recorded_names[choice]
            mode = int(name_acquisition.split('noll')[-1].split('_')[0])
            if iris_file_exists(name_acquisition,timeout_time,temp_folder):
                print("################")
                print(f"Process IRIS images to extract NCPA mode noll {mode}")
                print("################")
                D_process_ncpa_iris(args.tel, mode, 0, args.repeat, args.floop, name_acquisition, args.timepermode, args.silent, temp_folder, args.sequence)
            else:
                raise OSError('Cannot find IRIS file')
            print("################")
            print("Apply NCPA")
            print("################")
            if args.psf_display==1:
                iris_acquisition(3,'IrisAcq_beforecorr_{0}'.format(tStart))
            #Check existence of NCPA file
            start_time = time.time()
            while not os.path.exists(os.path.join(temp_folder,'NCPA_{0}.npy'.format(name_acquisition))):
                time.sleep(1)
                if (time.time()-start_time) > timeout_time:
                    raise RuntimeError('Maximal waiting time reached')
            ### APPLY NCPA ###
            E_apply_ncpas(args.tel, mode, 0, name_acquisition, args.sequence, args.user_input, temp_folder)
            time.sleep(1)
            if args.psf_display==1:
                iris_acquisition(3,'IrisAcq_aftercorr_{0}'.format(tStart))
                while not exists_remote('aral@waral', '/data/ARAL/INS_ROOT/SYSTEM/DETDATA/IrisAcq_aftercorr_{0}_DIT.fits'.format(tStart)):
                    time.sleep(1)
                    if (time.time()-start_time) > timeout_time:
                        raise RuntimeError('Maximal waiting time reached')
                display_psf (args.tel, tStart, args.silent, temp_folder)
        else:
            raise ValueError('Sequence argument is not SEQ and not PAR.')

##################
### GRAVITY SC ###
##################

    elif args.inst == "GRAV":
        if args.sequence=="PAR": #one acquisition with "repeat" of all the modes
            name_acquisition = recorded_names[choice]
            if grav_file_exists(name_acquisition,timeout_time,temp_folder):
                print("################")
                print("Process GRAVITY SC images to extract NCPA")
                print("################")
                D_process_ncpa_grav(args.mode_start, args.mode_end, args.repeat, args.floop, name_acquisition,  args.timepermode, args.silent, temp_folder, args.sequence)
            else:
                raise OSError('Cannot find GRAVITY SC file')
            print("################")
            print("Apply NCPA")
            print("################")
            #Check existence of NCPA file
            start_time = time.time()
            while not os.path.exists(os.path.join(temp_folder,'NCPA_{0}.npy'.format(name_acquisition))):
                time.sleep(1)
                if (time.time()-start_time) > timeout_time:
                    raise RuntimeError('Maximal waiting time reached')
            ### APPLY NCPA ###
            E_apply_ncpas(args.tel, args.mode_start, args.mode_end, name_acquisition, args.sequence, args.user_input, temp_folder)
            time.sleep(1)

        elif args.sequence=="SEQ": #one acquisition with "repeat" of all the modes
            name_acquisition = recorded_names[choice]
            mode = int(name_acquisition.split('noll')[-1].split('_')[0])
            if grav_file_exists(name_acquisition,timeout_time,temp_folder):
                print("################")
                print(f"Process GRAVITY SC images to extract NCPA mode noll {mode}")
                print("################")
                D_process_ncpa_grav(mode, 0, args.repeat, args.floop, name_acquisition,  args.timepermode, args.silent, temp_folder, args.sequence)
            else:
                raise OSError('Cannot find GRAVITY SC file')
            print("################")
            print("Apply NCPA")
            print("################")
            #Check existence of NCPA file
            start_time = time.time()
            while not os.path.exists(os.path.join(temp_folder,'NCPA_{0}.npy'.format(name_acquisition))):
                time.sleep(1)
                if (time.time()-start_time) > timeout_time:
                    raise RuntimeError('Maximal waiting time reached')
            ### APPLY NCPA ###
            E_apply_ncpas(args.tel, mode, 0, name_acquisition, args.sequence, args.user_input, temp_folder)
        else:
            raise ValueError('Sequence argument is not SEQ and not PAR.')

    else:
        print("WRONG INSTRUMENT NAME")
        raise ValueError('INST not known')

