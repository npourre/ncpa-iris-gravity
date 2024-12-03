import argparse
from datetime import datetime
import time
import ccs
import vlti

## LAUNCH FROM ISS

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Record IRIS data cube for NCPA")
    parser.add_argument('tel', type=int, choices=range(5), help="Telescope index; use 0 for all four at once.")
    parser.add_argument('mode_start', type=int , help="start mode Noll index")
    parser.add_argument('mode_end', type=int , help="end mode Noll index")
    parser.add_argument('floop', type=int , help="AO loop frequency")
    parser.add_argument('name_acquisition', type=str, help="name of the IRIS acquisition")
    parser.add_argument('--duration', '-d', type=float, default=30.0)
    parser.add_argument('--bck', '-b', type=int, default=1, help="Do we record a background or not. O/1")
    args = parser.parse_args()

    if args.tel==0: #all UTs measurements
        telescopes = [1,2,3,4]
        ut_str = "1234"
    elif args.tel in [1,2,3,4]: #one UT measurement
        telescopes = [args.tel]
        ut_str = str(args.tel)
    else:
        print("WRONG TELESCOPE NUMBER")

    ccs.CcsInit(name='iris_ncpa.py')
    
    # Take background
    waral = vlti.ssh("aral@waral")
    waral.send("''", "iracqServer", "FRAME", "-name\ DIT\ -gen\ T\ -store\ T",verbose=True)
    waral.send("''", "iracqServer", "FRAME", "-name\ INT\ -gen\ T\ -store\ T")
    waral.send("''", "iracqServer", "SETUP", ",,DET.DIT\ 0") # set minimal DIT

    dit = ccs.DbRead("@waral:Appl_data:ARAL:IRIS:iracq:exposure.DIT")
    framedit = dit + 0.0006 #empirical readtime
    nDit = int(args.duration/framedit)

    if args.bck:
        waral.send("''", "iracqServer", "SETUP", ",,DET.NDIT\ {0}".format(100))
        waral.send("''", "iracqServer", "SETUP", ",,DET.FILE.CUBE.ST\ T")
        waral.send("''", "iracqServer", "SETUP", ",,DET.EXP.NAMING.TYPE\ Request-Naming",verbose=True)
        tStart = args.name_acquisition.split('_')[1]
        waral.send("''", "iracqServer", "SETUP", ",,DET.EXP.NAME\ IrisNcpa_{0}_bckg".format(tStart),verbose=True)
        # send STS offsets to take a dark
        for iTel in telescopes:
            wopNsts = vlti.ssh("sts@wop{0}sts".format(iTel))
            wopNsts.send("''", "pscsifControl", "OFFGFSM", "0,-100,0,0")
        waral.send("''", "iracqServer", "START", "''",verbose=True)
        time.sleep(5)
        # remove STS offsets and center beacons
        for iTel in telescopes:
            wopNsts = vlti.ssh("sts@wop{0}sts".format(iTel))
            wopNsts.send("''", "pscsifControl", "OFFGFSM", "0,100,0,0")

    # Start Lab Guiding
    #ccs.SendCommand('', 'issifControl', 'STRTLAG', 'AS_SUCH')

    # Prepare IRIS
    waral.send("''", "iracqServer", "SETUP", ",,DET.NDIT\ {0}".format(nDit))
    waral.send("''", "iracqServer", "SETUP", ",,DET.FILE.CUBE.ST\ T")
    waral.send("''", "iracqServer", "SETUP", ",,DET.EXP.NAMING.TYPE\ Request-Naming",verbose=True)
    waral.send("''", "iracqServer", "SETUP", ",,DET.EXP.NAME\ {0}".format(args.name_acquisition),verbose=True)

    # Prepare GPAO(s)
    for iTel in telescopes:
        wgpNao = vlti.ssh("gpao{0}@wgp{0}ao".format(iTel))
        wgpNao.send("wgp{0}sgw".format(iTel), "spaccsServer", "SETUP", "\"HOAcqDisturb.FILENAME $INS_ROOT/SYSTEM/SPARTA/RTCDATA/NcpaModulation_noll{0}to{1}_tel{2}_f{3}.fits\"".format(args.mode_start,args.mode_end,iTel,args.floop),verbose=True)
        wgpNao.send("wgp{0}sgw".format(iTel), "spaccsServer", "SETUP", "HOAcqDisturb.CYCLES\ 1",verbose=True)
        wgpNao.send("wgp{0}sgw".format(iTel), "spaccsServer", "SETUP", "HOAcqDisturb.START_AT_FC\ 0",verbose=True)


    # Start recording on IRIS
    waral.send("''", "iracqServer", "START", "''",verbose=True)
    #time.sleep(1)

    # Start modulation on GPAO(s)
    for iTel in telescopes:
        wgpNao = vlti.ssh("gpao{0}@wgp{0}ao".format(iTel))
        wgpNao.send("wgp{0}sgw".format(iTel), "spaccsServer", "EXEC", "HOAcqDisturb.run",verbose=True)

    # Wait for the duration of the measurement
    #time.sleep(args.duration)


