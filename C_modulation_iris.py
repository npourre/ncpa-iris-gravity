
import time
import ccs
import vlti

def C_modulation_iris(tel, mode_start, mode_end, repeat, sequence, floop, name_acquisition, duration, bck)
    if tel==0: #all UTs measurements
        telescopes = [1,2,3,4]
        ut_str = "1234"
    elif args.tel in [1,2,3,4]: #one UT measurement
        telescopes = [tel]
        ut_str = str(tel)
    else:
        print("WRONG TELESCOPE NUMBER")

    ccs.CcsInit(name='iris_ncpa.py')
    
    # Take background
    waral = vlti.ssh("aral@waral")
    waral.send("''", "iracqServer", "FRAME", "-name\ DIT\ -gen\ T\ -store\ T")
    waral.send("''", "iracqServer", "FRAME", "-name\ INT\ -gen\ T\ -store\ T")
    waral.send("''", "iracqServer", "SETUP", ",,DET.DIT\ 0") # set minimal DIT

    dit = ccs.DbRead("@waral:Appl_data:ARAL:IRIS:iracq:exposure.DIT")
    framedit = dit + 0.0006 #empirical readtime
    nDit = int(args.duration/framedit)

    iss_ssh = vlti.ssh("iss@wvgvlti")

    if bck:
        iss_ssh.send("''", 'issifControl', 'STOPLAG', "''")
        waral.send("''", "iracqServer", "SETUP", ",,DET.NDIT\ {0}".format(100))
        waral.send("''", "iracqServer", "SETUP", ",,DET.FILE.CUBE.ST\ T")
        waral.send("''", "iracqServer", "SETUP", ",,DET.EXP.NAMING.TYPE\ Request-Naming")
        tStart = args.name_acquisition.split('_')[1]
        waral.send("''", "iracqServer", "SETUP", ",,DET.EXP.NAME\ IrisNcpa_{0}_bckg".format(tStart))
        # send STS offsets to take a dark
        for iTel in telescopes:
            wopNsts = vlti.ssh("sts@wop{0}sts".format(iTel))
            wopNsts.send("''", "pscsifControl", "OFFGFSM", "0,-100,0,0")
        time.sleep(0.8)
        waral.send("''", "iracqServer", "START", "''")
        time.sleep(5)
        # remove STS offsets and center beacons
        for iTel in telescopes:
            wopNsts = vlti.ssh("sts@wop{0}sts".format(iTel))
            wopNsts.send("''", "pscsifControl", "OFFGFSM", "0,100,0,0")
            
    # Start Lab Guiding
    iss_ssh.send("''", 'issifControl', 'STRTLAG', 'AS_SUCH')

    # Prepare IRIS
    waral.send("''", "iracqServer", "SETUP", ",,DET.NDIT\ {0}".format(nDit))
    waral.send("''", "iracqServer", "SETUP", ",,DET.FILE.CUBE.ST\ T")
    waral.send("''", "iracqServer", "SETUP", ",,DET.EXP.NAMING.TYPE\ Request-Naming")
    waral.send("''", "iracqServer", "SETUP", ",,DET.EXP.NAME\ {0}".format(args.name_acquisition))

    # Prepare GPAO(s)
    if sequence == 'PAR':
        for iTel in telescopes:
            wgpNao = vlti.ssh("gpao{0}@wgp{0}ao".format(iTel))
            wgpNao.send("wgp{0}sgw".format(iTel), "spaccsServer", "SETUP", "\"HOAcqDisturb.FILENAME $INS_ROOT/SYSTEM/SPARTA/RTCDATA/NcpaModulation_noll{0}to{1}_tel{2}_f{3}.fits\"".format(mode_start, mode_end, iTel, floop))
            wgpNao.send("wgp{0}sgw".format(iTel), "spaccsServer", "SETUP", f"HOAcqDisturb.CYCLES\ {repeat}")
            wgpNao.send("wgp{0}sgw".format(iTel), "spaccsServer", "SETUP", "HOAcqDisturb.START_AT_FC\ 0")
    elif sequence == 'SEQ':
        for iTel in telescopes:
            wgpNao = vlti.ssh("gpao{0}@wgp{0}ao".format(iTel))
            wgpNao.send("wgp{0}sgw".format(iTel), "spaccsServer", "SETUP", "\"HOAcqDisturb.FILENAME $INS_ROOT/SYSTEM/SPARTA/RTCDATA/NcpaModulation_noll{0}_tel{1}_f{2}.fits\"".format(mode_start, iTel, floop))
            wgpNao.send("wgp{0}sgw".format(iTel), "spaccsServer", "SETUP", "HOAcqDisturb.CYCLES\ 1")
            wgpNao.send("wgp{0}sgw".format(iTel), "spaccsServer", "SETUP", "HOAcqDisturb.START_AT_FC\ 0")


    # Start recording on IRIS
    waral.send("''", "iracqServer", "START", "''")
    #time.sleep(1)

    # Start modulation on GPAO(s)
    for iTel in telescopes:
        wgpNao = vlti.ssh("gpao{0}@wgp{0}ao".format(iTel))
        wgpNao.send("wgp{0}sgw".format(iTel), "spaccsServer", "EXEC", "HOAcqDisturb.run")

    # Wait for the duration of the measurement
    #time.sleep(args.duration)


