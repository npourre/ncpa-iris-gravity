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

def exists_remote(host, path):
    """Test if a file exists at path on a host accessible with SSH."""
    status = subprocess.call(
        ['ssh', host, 'test -f {}'.format(shlex.quote(path))])
    if status == 0:
        return True
    if status == 1:
        return False
    raise Exception('SSH failed')

def download_latest_file(server, remote_dir, name, local_dir):
    # Construct the command to find the latest file with the given prefix
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
    parser.add_argument('floop', type=int , help="AO loop frequency")
    parser.add_argument('inst', type=str , help="IRIS or GRAV")
    parser.add_argument('--background','-b', type=int,default=1 , help="Do we record a background or not. 0/1")
    parser.add_argument('--timepermode','-t',type=float,default=1.5, help='time permode (sec)')
    parser.add_argument('--get_matrices','-m',type=int, default=1, help="Do we fetch SPARTA matrices. 0/1")
    parser.add_argument('--user_input','-u', type=int,default=1 , help="Ask for user validation to apply ncpa. 0/1")
    parser.add_argument('--psf_display','-p', type=int,default=0 , help="Show IRIS PSF before and after correction. 0/1")
    parser.add_argument('--silent','-s', type=int,default=0 , help="Prevent popup. 0/1")
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
    os.system('python 1_generate_disturbance_files_multiplemodes.py {0} {1} {2} {3} -t {4}'.format(args.tel, args.mode_start, args.mode_end, args.floop, args.timepermode))
    
    print("################")
    print("Launch IRIS/SC acquisition and GPAO disturbance")
    print("################")
    tStart = datetime.utcnow().isoformat()[:-7]
    if args.inst == "IRIS":
        name_acquisition = "IrisNcpa_{0}_noll{1}to{2}_UT{3}".format(tStart, args.mode_start, args.mode_end, ut_str)
        duration_acq = (((args.timepermode+0.5) * (args.mode_end-args.mode_start+1)) + 1.5) + 18 
        os.system('python 2_iris_ncpa_multiplemodes.py {0} {1} {2} {3} -d {4} -b {5}'.format(args.tel, args.mode_start, args.mode_end, args.floop, name_acquisition, duration_acq, args.background ))
    elif args.inst == "GRAV":
        name_acquisition = "GravNcpa_{0}_noll{1}_UT{2}".format(tStart, args.mode, ut_str)
        duration_acq = (((args.timepermode+0.5) * args.repeat) +1.5) + 10
        os.system('python 2_modulation_acq.py {0} {1} {2} {3} -d {4} -b {5} -i 0.01'.format(args.tel, args.mode, args.repeat, args.floop, name_acquisition, duration_acq, args.background))
    else:
        print("WRONG INSTRUMENT NAME")
        raise ValueError('INST not known')
    timeout_time = 300 #s
    if args.inst == "IRIS":
        #Wait for file on the remote server
        time.sleep(duration_acq)
        start_time = time.time()
        terminated = False
        while not exists_remote('aral@waral', '/data/ARAL/INS_ROOT/SYSTEM/DETDATA/{0}_DIT.fits'.format(name_acquisition)):
            time.sleep(1)
            if (time.time()-start_time) > timeout_time:
                raise RuntimeError('Maximal waiting time reached')
        print("File found!")
        while not terminated:
            download_latest_file('aral@waral','/data/ARAL/INS_ROOT/SYSTEM/DETDATA/' , '{0}_DIT.fits'.format(name_acquisition), '/vltuser/iss/temp_ncpa/')
            try:
                fits.getdata('/vltuser/iss/temp_ncpa/{0}_DIT.fits'.format(name_acquisition),0)
            except:
                time.sleep(2)
            else:
                terminated = True
        print("################")
        print("Process IRIS/SC images to extract NCPA")
        print("################")          
        os.system('python 3_process_ncpa_iris_multiplemodes.py {0} {1} {2} {3} {4} -t {5} -s {6}'.format(args.tel, args.mode_start, args.mode_end, args.floop, name_acquisition, args.timepermode, args.silent))
    elif args.inst == "GRAV":
        #Wait for file on the remote server
        start_time = time.time()
        while not exists_remote('grav@wgv', "/data/GRAVITY/INS_ROOT/SYSTEM/DETDATA/{0}_DIT.fits".format(name_acquisition)):
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
    if args.psf_display==1:
        os.system('python iris_acq.py -d 3 -n IrisAcq_beforecorr_{0}'.format(tStart))
    #Check existence of NCPA file
    start_time = time.time()
    while not os.path.exists('/vltuser/iss/temp_ncpa/NCPA_{0}.npy'.format(name_acquisition)):
        time.sleep(1)
        if (time.time()-start_time) > timeout_time:
            raise RuntimeError('Maximal waiting time reached')

    os.system('python 4_apply_ncpa_multiplemodes.py {0} {1} {2} {3} -u {4}'.format(args.tel, args.mode_start, args.mode_end, name_acquisition, args.user_input))
    time.sleep(1)
    if args.psf_display==1:
        os.system('python iris_acq.py -d 3 -n IrisAcq_aftercorr_{0}'.format(tStart))
        while not exists_remote('aral@waral', '/data/ARAL/INS_ROOT/SYSTEM/DETDATA/IrisAcq_aftercorr_{0}_DIT.fits'.format(tStart)):
            time.sleep(1)
            if (time.time()-start_time) > timeout_time:
                raise RuntimeError('Maximal waiting time reached')
        os.system('python display_psf.py {0} {1} -s {2}'.format(args.tel, tStart, args.silent))
