#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 30 16:16:17 2023

@author: pourren
"""
# =============================================================================
# Essentially spectro_ncpa
#
# Launch on ISS
# =============================================================================

import argparse
from datetime import datetime
import time
import ccs
import vlti

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Record GRAVITY SC data cube for NCPA, process it to get ncpa")
    parser.add_argument('tel', type=int, choices=range(5), help="Telescope index")
    parser.add_argument('mode', type=int, help="noll index of the modulation")
    parser.add_argument('repeat', type=int , help="number of repetition")
    parser.add_argument('floop', type=int , help="AO loop frequency")
    parser.add_argument('name_acquisition', type=str, help="name of the GRAV acquisition")
    parser.add_argument('--duration', '-d', type=float, default=30.)
    parser.add_argument('--dit', '-i', type=float, default=0.01)
    parser.add_argument('--bck', '-b', type=int, default=1, help="Do we record a background or not. O/1")
    args = parser.parse_args()


    print(args.duration)
    ips = [4,1,2,1]
    ip_num = ips[args.tel-1]
    wgv = vlti.ssh("grav@wgv")

    # Prepare SPECTRO
    #wgv.send("''", "ngcircon_NGCIR2", "FRAME", "-function DET.ACQ1.EXTNAME IMAGING_DATA_SC")
    wgv.send("''", "ngcircon_NGCIR2", "SETUP","\",,DET.READ.CURNAME Uncorr_6slices_10MHz\"",verbose=True) 
    wgv.send("''", "ngcircon_NGCIR2", "SETUP", "\",,DET.SEQ.DIT {0}\"".format(args.dit),verbose=True)
    nDit = int(args.duration/(args.dit*1.2))
    wgv.send("''", "ngcircon_NGCIR2", "SETUP","\",,DET2.FRAM.FORMAT cube-ext\"",verbose=True)
    wgv.send("''", "ngcircon_NGCIR2", "SETUP","\",,DET.FRAM.NAMING Request\"",verbose=True)
    
    # Prepare  GPAO
    if (args.tel>=1) and (args.tel<=4):
        wgpNao = vlti.ssh("gpao{0}@wgp{0}ao".format(args.tel))
        wgpNao.send("wgp{0}sgw".format(args.tel), "spaccsServer", "SETUP", "\"HOAcqDisturb.FILENAME $INS_ROOT/SYSTEM/SPARTA/RTCDATA/NcpaModulation_noll{0}_f{1}.fits\"".format(args.mode,args.floop),verbose=True)
        wgpNao.send("wgp{0}sgw".format(args.tel), "spaccsServer", "SETUP", "HOAcqDisturb.CYCLES\ {0}".format(args.repeat),verbose=True)
        wgpNao.send("wgp{0}sgw".format(args.tel), "spaccsServer", "SETUP", "HOAcqDisturb.START_AT_FC\ 0",verbose=True)
    else:
        print('Wrong telescope number')


    if args.bck:
        # Take background 
        tStart = args.name_acquisition.split('_')[1]
        wgv.send("''", "gviControl", "SETUP", "\",,INS.SHUT11.ST F INS.SHUT12.ST F INS.SHUT13.ST F INS.SHUT14.ST F \"",verbose=True) # Close shutters
        #time.sleep(10)
        wgv.send("''", "ngcircon_NGCIR2", "SETUP", "\",,DET.NDIT {0}\"".format(1000))
        wgv.send("''", "ngcircon_NGCIR2", "SETUP", "\",,DET.FRAM.FILENAME GravNcpa_{0}_bckg\"".format(tStart),verbose=True)
        wgv.send("''", "ngcircon_NGCIR2", "START", "\"\"")
        time.sleep(1000*args.dit+5)
        #wgv.send("''", "gviControl", "SETUP", "\",,INS.SHUT1.ST T INS.SHUT2.ST T INS.SHUT13.ST T INS.SHUT14.ST T \"") # Open shutters

    wgv.send("''", "gviControl", "SETUP", "\",,INS.SHUT11.ST F INS.SHUT12.ST F INS.SHUT13.ST F INS.SHUT14.ST F \"",verbose=True) # Close shutters
    wgv.send("''", "gviControl", "SETUP", "\",,INS.SHUT1{0}.ST T \"".format(ip_num),verbose=True)
    # Start Field Guiding 
    time.sleep(2)
    wgv.send("''", "gvttpControl", "STRTLP", "FIELD_IMAGER",verbose=True)
    time.sleep(5)
    # Start recording on SC
    wgv.send("''", "ngcircon_NGCIR2", "SETUP", "\",,DET.NDIT {0}\"".format(nDit),verbose=True)

    nols = str(args.mode)
    if len(nols)==1:
        nols = '0'+nols
    wgv.send("''", "ngcircon_NGCIR2", "SETUP", "\",,DET.FRAM.FILENAME {0}\"".format(args.name_acquisition),verbose=True)
    wgv.send("''", "ngcircon_NGCIR2", "START", "\"\"",verbose=True)
    time.sleep(1)

    # Start modulation on GPAO
    if (args.tel>=1) and (args.tel<=4):
        wgpNao.send("wgp{0}sgw".format(args.tel), "spaccsServer", "EXEC", "HOAcqDisturb.run",verbose=True)
    else:
        print('Wrong telescope number')

    # Wait for the duration of the measurement
    time.sleep(args.duration)
