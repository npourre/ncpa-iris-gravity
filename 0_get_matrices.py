#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 30 16:15:28 2023

@author: pourren
"""
# =============================================================================
# Launch on ISS
# Create folders and get matrices from sparta
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

def get_matrices_data(iTel):
	wgpNsgw = vlti.ssh("gpao{0}@wgp{0}sgw".format(iTel))
	# save MODE2SLOPES from sparta
	wgpNsgw.send("wgp{0}sgw".format(iTel), "spaccsServer", "SAVE", "\"-object HOAcq.DET1.MODETOSLOPE  -filename MODE2SLOPE{0}.fits \"".format(iTel),verbose=True)
	# send to ISS directory
	os.system('scp gpao{0}@wgp{0}sgw:/data/GPAO{0}/INS_ROOT/SYSTEM/SPARTA/RTCDATA/MODE2SLOPE{0}.fits data '.format(iTel))

	# save rotmap from sparta
	wgpNsgw.send("wgp{0}sgw".format(iTel), "spaccsServer", "SAVE", "\"-object HOAcq.DET1.ROTATION_MATRIX  -filename ROTATION_MATRIX{0}.fits \"".format(iTel),verbose=True)
	# send to ISS directory
	os.system('scp gpao{0}@wgp{0}sgw:/data/GPAO{0}/INS_ROOT/SYSTEM/SPARTA/RTCDATA/ROTATION_MATRIX{0}.fits data '.format(iTel))

	# save scramble matrix from sparta
	wgpNsgw.send("wgp{0}sgw".format(iTel), "spaccsServer", "SAVE", "\"-object HORecn.WFS_SLP_UNSCR_MAP  -filename WFS_SLP_UNSCR_MAP{0}.fits \"".format(iTel),verbose=True)
	# send to ISS directory
	os.system('scp gpao{0}@wgp{0}sgw:/data/GPAO{0}/INS_ROOT/SYSTEM/SPARTA/RTCDATA/WFS_SLP_UNSCR_MAP{0}.fits data '.format(iTel))

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description="Get necessary matrices from SPARTA")
	parser.add_argument('tel', type=int, choices=range(5), help="Telescope index, 0 for all UTs, 1 for UT1, 2 for UT2, ...")
	args = parser.parse_args()

	if not os.path.isdir('data'):
		os.system('mkdir data')
	if not os.path.isdir('data/default_refslopes'):
		os.system('mkdir data/default_refslopes')
	if not os.path.isdir('data/modified_refslopes'):
		os.system('mkdir data/modified_refslopes')
	if not os.path.isdir('data/modulations'):
		os.system('mkdir data/modulations')
	if not os.path.isdir('data/outputs'):
		os.system('mkdir data/outputs')

	if args.tel==0: #all UTs measurements
		for iTel in range(1,5):
			get_matrices_data(iTel)
	elif args.tel in [1,2,3,4]: #one UT measurement
		get_matrices_data(args.tel)
	else:
		print("WRONG TELESCOPE NUMBER")


