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

def generate_disturb(iTel, period, repeat,amplitude_fast, amplitude_slow, f, f_fast, margin, mode_noll):
	# Load M2S matrix
	M2S_filename = 'data/MODE2SLOPE{0}.fits'.format(iTel)
	with fits.open(M2S_filename) as hdulist:
		unscrambled_M2S = hdulist[0].data

	rotmat_filename = 'data/ROTATION_MATRIX{0}.fits'.format(iTel)
	with fits.open(rotmat_filename) as hdulist:
		rotmat = hdulist[0].data
	rot_uns_M2S = unscrambled_M2S@(rotmat)

	unsc_map_filename = 'data/WFS_SLP_UNSCR_MAP{0}.fits'.format(iTel)
	with fits.open(unsc_map_filename) as hdulist:
		unscramble = (hdulist[0].data).flatten().astype(int)
	scr_M2S = rot_uns_M2S[unscramble]

	# Create fundamental modulation
	modulation = amplitude_slow*np.sin(2.0*np.pi*np.arange(period)/(period/2)) + amplitude_fast*np.sin(2.0*np.pi*np.arange(period)/f*f_fast)
	
	focus_flash_length = margin
	focus_flash = 0.2*np.sin(2.0*np.pi*np.arange(focus_flash_length)/f*f_fast)
	amp_focus_flash =0.2
	
	# Create sequence
	Z = np.zeros((int(focus_flash_length+(margin+period)*repeat+margin+focus_flash_length), scr_M2S.shape[1]))
	Z[:focus_flash_length,2]= focus_flash+amp_focus_flash
	Z[-focus_flash_length:,2]= focus_flash+amp_focus_flash
	for i in range(repeat):
		Z[focus_flash_length+int(margin)+int(margin+period)*i:focus_flash_length+int(margin+period)*(i+1), mode_noll-2] = modulation
	S = (scr_M2S @ Z.T).T

	hdulist = fits.HDUList([fits.PrimaryHDU(S.astype(np.float32))])
	hdulist.writeto('data/modulations/NcpaModulation_noll{0}_tel{1}_f{2}.fits'.format(mode_noll,iTel,f), overwrite=True)
	# Send to wgpXsgw
	os.system('scp data/modulations/NcpaModulation_noll{0}_tel{1}_f{2}.fits gpao{1}@wgp{1}sgw:/data/GPAO{1}/INS_ROOT/SYSTEM/SPARTA/RTCDATA/'.format(mode_noll,iTel,f))

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description="Generate the disturbance matrices")
	parser.add_argument('tel', type=int, choices=range(5), help="Telescope index. 0 for all telescopes")
	parser.add_argument('mode', type=int , help="mode Noll index")
	parser.add_argument('repeat', type=int , help="number of repetition for the measurement")
	parser.add_argument('floop', type=int , help="AO loop frequency")
	parser.add_argument('--timepermode','-t',type=float,default=1.5, help='time permode (sec)')
	parser.add_argument('--amplitude_fast','-a',type=float,default=0.2, help='Amplitude of fast modulation [µm]')
	parser.add_argument('--amplitude_slow','-s',type=float,default=0.2, help='Amplitude of slow modulation [µm]')
	args = parser.parse_args()

	# Disturbances parameters
	f = args.floop # loop rate in Hz
	f_fast = 25  # [Hz]
	margin_t = 0.5 # in sec
	margin = int(margin_t * f) #in loop cycle
	period = args.timepermode * f
	amplitude_fast = args.amplitude_fast
	amplitude_slow = args.amplitude_slow
	mode_noll = args.mode

	if args.tel==0: #all UTs measurements
		for iTel in range(1,5):
			generate_disturb(iTel, period,args.repeat, amplitude_fast, amplitude_slow, f, f_fast, margin, mode_noll)
	elif args.tel in [1,2,3,4]: #one UT measurement
		generate_disturb(args.tel, period,args.repeat, amplitude_fast, amplitude_slow, f, f_fast, margin, mode_noll)
	else:
		print("WRONG TELESCOPE NUMBER")

	print("Modulation will last {0} s".format(((period+margin)*args.repeat+3*margin)/f))



