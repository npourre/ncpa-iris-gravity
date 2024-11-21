import argparse
from datetime import datetime
import time
import ccs
import vlti

## LAUNCH FROM ISS

def prep_gpao(iTel, mode, floop, repeat):
    wgpNao = vlti.ssh("gpao{0}@wgp{0}ao".format(iTel))
    wgpNao.send("wgp{0}sgw".format(iTel), "spaccsServer", "SETUP", "\"HOAcqDisturb.FILENAME $INS_ROOT/SYSTEM/SPARTA/RTCDATA/NcpaModulation_noll{0}_tel{1}_f{2}.fits\"".format(mode,iTel,floop),verbose=True)
    wgpNao.send("wgp{0}sgw".format(iTel), "spaccsServer", "SETUP", "HOAcqDisturb.CYCLES\ {0}".format(repeat),verbose=True)
    wgpNao.send("wgp{0}sgw".format(iTel), "spaccsServer", "SETUP", "HOAcqDisturb.START_AT_FC\ 0",verbose=True)

def start_modul(iTel):
    wgpNao = vlti.ssh("gpao{0}@wgp{0}ao".format(iTel))
    wgpNao.send("wgp{0}sgw".format(iTel), "spaccsServer", "EXEC", "HOAcqDisturb.run",verbose=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Record IRIS data cube for NCPA")
    parser.add_argument('tel', type=int, choices=range(5), help="Telescope index; use 0 for all four at once.")
    parser.add_argument('mode', type=int , help="mode Noll index")
    parser.add_argument('repeat', type=int , help="number of repetition")
    parser.add_argument('floop', type=int , help="AO loop frequency")
    parser.add_argument('--duration', '-d', type=float, default=30.0)
    args = parser.parse_args()

    tStart = datetime.utcnow().isoformat()[:-7]

    ccs.CcsInit(name='iris_ncpa.py')
    minDit = ccs.DbRead("@waral:Appl_data:ARAL:IRIS:iracq:exposure.DIT")
    nDit = int(args.duration/minDit)
    
    # Take background
    waral = vlti.ssh("aral@waral")
    waral.send("''", "iracqServer", "FRAME", "-name\ DIT\ -gen\ T\ -store\ T",verbose=True)
    waral.send("''", "iracqServer", "FRAME", "-name\ INT\ -gen\ T\ -store\ T")
    waral.send("''", "iracqServer", "SETUP", ",,DET.NDIT\ {0}".format(100))
    waral.send("''", "iracqServer", "SETUP", ",,DET.FILE.CUBE.ST\ T")
    waral.send("''", "iracqServer", "SETUP", ",,DET.EXP.NAMING.TYPE\ Request-Naming",verbose=True)
    waral.send("''", "iracqServer", "SETUP", ",,DET.EXP.NAME\ IrisNcpa_{0}_bckg".format(tStart),verbose=True)

    # send STS offsets to take a dark
    if args.tel==0: #all UTs measurements
        for iTel in range(1,5):
            wopNsts = vlti.ssh("sts@wop{0}sts".format(iTel))
            wopNsts.send("''", "pscsifControl", "OFFGFSM", "0,-100,0,0")
    elif args.tel in [1,2,3,4]: #one UT measurement
        wopNsts = vlti.ssh("sts@wop{0}sts".format(args.tel))
        wopNsts.send("''", "pscsifControl", "OFFGFSM", "0,-100,0,0")
    else:
        print("WRONG TELESCOPE NUMBER")
    waral.send("''", "iracqServer", "START", "''",verbose=True)
    time.sleep(5)
    # remove STS offsets and center beacons
    if args.tel==0: #all UTs measurements
        for iTel in range(1,5):
            wopNsts = vlti.ssh("sts@wop{0}sts".format(iTel))
            wopNsts.send("''", "pscsifControl", "OFFGFSM", "0,100,0,0")
    elif args.tel in [1,2,3,4]: #one UT measurement
        wopNsts = vlti.ssh("sts@wop{0}sts".format(args.tel))
        wopNsts.send("''", "pscsifControl", "OFFGFSM", "0,100,0,0")
    else:
        print("WRONG TELESCOPE NUMBER")

    # Start Lab Guiding
    #ccs.SendCommand('', 'issifControl', 'STRTLAG', 'AS_SUCH')

    # Prepare IRIS
    waral = vlti.ssh("aral@waral")
    waral.send("''", "iracqServer", "FRAME", "-name\ DIT\ -gen\ T\ -store\ T",verbose=True)
    waral.send("''", "iracqServer", "FRAME", "-name\ INT\ -gen\ T\ -store\ T")
    waral.send("''", "iracqServer", "SETUP", ",,DET.NDIT\ {0}".format(nDit))
    waral.send("''", "iracqServer", "SETUP", ",,DET.FILE.CUBE.ST\ T")
    waral.send("''", "iracqServer", "SETUP", ",,DET.EXP.NAMING.TYPE\ Request-Naming",verbose=True)
    waral.send("''", "iracqServer", "SETUP", ",,DET.EXP.NAME\ IrisNcpa_{0}_noll{1}_UT{2}".format(tStart, args.mode, args.tel),verbose=True)

    # Prepare GPAO(s)
    if args.tel==0: #all UTs measurements
        for iTel in range(1,5):
            prep_gpao(iTel, args.mode, args.floop, args.repeat)
    elif args.tel in [1,2,3,4]: #one UT measurement
        prep_gpao(args.tel, args.mode, args.floop, args.repeat)
    else:
        print("WRONG TELESCOPE NUMBER")

    # Start recording on IRIS
    waral.send("''", "iracqServer", "START", "''",verbose=True)
    time.sleep(1)

    # Start modulation on GPAO(s)
    if args.tel==0: #all UTs measurements
        for iTel in range(1,5):
            start_modul(iTel)
    elif args.tel in [1,2,3,4]: #one UT measurement
        start_modul(args.tel)
    else:
        print("WRONG TELESCOPE NUMBER")

    # Wait for the duration of the measurement
    time.sleep(args.duration)


