#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 30 16:15:28 2023

@author: pourren
"""
# =============================================================================
# Fusion of get_matrices and generate_ncpa_ciao_disturbance
#
# Launch on GPAO AO
# =============================================================================

import argparse
from datetime import datetime
import time
import os
import ccs
import vlti
from astropy.io import fits
import numpy as np
from scipy import linalg as la

def generate_disturb(tel, period,amplitude_fast, amplitude_slow, f, f_fast, margin, mode_noll_start, mode_noll_end, repeat, sequence):
    # Load M2S matrix
    M2S_filename = 'data/MODE2SLOPE{0}.fits'.format(tel)
    with fits.open(M2S_filename) as hdulist:
        unscrambled_M2S = hdulist[0].data

    rotmat_filename = 'data/ROTATION_MATRIX{0}.fits'.format(tel)
    with fits.open(rotmat_filename) as hdulist:
        rotmat = hdulist[0].data
    rot_uns_M2S = unscrambled_M2S@(rotmat)

    unsc_map_filename = 'data/WFS_SLP_UNSCR_MAP{0}.fits'.format(tel)
    with fits.open(unsc_map_filename) as hdulist:
        unscramble = (hdulist[0].data).flatten().astype(int)
    scr_M2S = rot_uns_M2S[unscramble]

    # Create fundamental modulation
    modulation = amplitude_slow*np.sin(2.0*np.pi*np.arange(period)/(period/2)) + amplitude_fast*np.sin(2.0*np.pi*np.arange(period)/f*f_fast)
    
    focus_flash_length = margin
    focus_flash = 0.2*np.sin(2.0*np.pi*np.arange(focus_flash_length)/f*f_fast)
    amp_focus_flash =0.2
    
    iZs = np.arange(mode_noll_start,mode_noll_end+1)
    if sequence == 'PAR':

        n_mod = iZs.shape[0]
        # Create sequence
        Z = np.zeros((int(focus_flash_length+(margin+period)*n_mod+margin+focus_flash_length), scr_M2S.shape[1]))
        Z[:focus_flash_length,2]= focus_flash+amp_focus_flash
        Z[-focus_flash_length:,2]= focus_flash+amp_focus_flash
        for iZ,Znoll in enumerate(iZs):
            Z[focus_flash_length+int(margin)+int(margin+period)*iZ:focus_flash_length+int(margin+period)*(iZ+1), Znoll-2] = modulation
        S = (scr_M2S @ Z.T).T
        
        hdulist = fits.HDUList([fits.PrimaryHDU(S.astype(np.float32))])
        hdulist.writeto('data/modulations/NcpaModulation_noll{0}to{1}_tel{2}_f{3}.fits'.format(mode_noll_start,mode_noll_end,tel,f), overwrite=True)
        # Send to wgpXsgw
        os.system('scp data/modulations/NcpaModulation_noll{0}to{1}_tel{2}_f{3}.fits gpao{2}@wgp{2}sgw:/data/GPAO{2}/INS_ROOT/SYSTEM/SPARTA/RTCDATA/'.format(mode_noll_start, mode_noll_end, tel, f))
    elif sequence == 'SEQ':
        # Create sequence
        for mode_noll in iZs:
            Z = np.zeros((int(focus_flash_length+(margin+period)*repeat+margin+focus_flash_length), scr_M2S.shape[1]))
            Z[:focus_flash_length,2]= focus_flash+amp_focus_flash
            Z[-focus_flash_length:,2]= focus_flash+amp_focus_flash
            for i in range(repeat):
                Z[focus_flash_length+int(margin)+int(margin+period)*i:focus_flash_length+int(margin+period)*(i+1), mode_noll-2] = modulation
            S = (scr_M2S @ Z.T).T

            hdulist = fits.HDUList([fits.PrimaryHDU(S.astype(np.float32))])
            hdulist.writeto('data/modulations/NcpaModulation_noll{0}_tel{1}_f{2}.fits'.format(mode_noll,tel,f), overwrite=True)
            # Send to wgpXsgw
            os.system('scp data/modulations/NcpaModulation_noll{0}_tel{1}_f{2}.fits gpao{1}@wgp{1}sgw:/data/GPAO{1}/INS_ROOT/SYSTEM/SPARTA/RTCDATA/'.format(mode_noll,tel,f))
    else:
        raise OSError('Sequence argument is not SEQ and not PAR.')
    return 0


def B_generate_disturbance_files(tel, mode_start, mode_end, floop, timepermode, sequence, repeat):
    # Disturbances parameters
    f_fast = 25  # [Hz]
    margin_t = 0.5 # in sec
    amplitude_fast = 0.2
    amplitude_slow = 0.2
    margin = int(margin_t * floop) #in loop cycle
    period = timepermode * floop

    if tel==0: #all UTs measurements
        for iTel in range(1,5):
            state = generate_disturb(iTel, period, amplitude_fast, amplitude_slow, floop, f_fast, margin, mode_start, mode_end, repeat, sequence)
    elif tel in [1,2,3,4]: #one UT measurement
        state = generate_disturb(tel, period, amplitude_fast, amplitude_slow, floop, f_fast, margin, mode_start, mode_end, repeat, sequence)
    else:
        print("WRONG TELESCOPE NUMBER")
    if state==0:
        print('Disturbance generated.')
    else:
        raise OSError('Error in generate_disturb subfunction')

