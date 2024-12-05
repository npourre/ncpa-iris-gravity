import argparse
import time
from astropy.io import fits
import argparse
import numpy as np
from scipy import signal as sig
from scipy import stats
from PySide2 import QtWidgets
from matplotlib import pyplot as plt
import matplotlib
import os
import glob

def cutIrisDet(img, telescope, verbose=False): #Florentin's function
    telescope = int(telescope)
    if verbose:
        print("Input image shape",np.shape(img))
        print("tel ",telescope)
    nframes, nx, ny = np.shape(img)
    if verbose:
        print("Nframes, nx, ny",nframes, nx, ny)
    onetel = nx/4;
    imout = img[:,int(onetel * (4-telescope)):int(onetel * (4-telescope+1)),:]
    if verbose:
        print("Shape of output image",np.shape(imout))
    return imout

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

def display_psf (tel, tStart, silent, temp_folder):
    # Transfer Iris acquisition to ISS
    server = "aral@waral"
    remote_dir = "/data/ARAL/INS_ROOT/SYSTEM/DETDATA" 
    download_latest_file(server, remote_dir, 'IrisAcq_beforecorr_{0}_DIT.fits'.format(tStart), temp_folder)
    download_latest_file(server, remote_dir, 'IrisAcq_aftercorr_{0}_DIT.fits'.format(tStart), temp_folder)
    
    #Check existence of fits files on ISS
    timeout_time = 120
    start_time = time.time()
    while not (os.path.exists('{0}IrisAcq_beforecorr_{1}_DIT.fits'.format(temp_folder, tStart)) and os.path.exists('{0}IrisAcq_aftercorr_{1}_DIT.fits'.format(temp_folder, tStart)) ):
        time.sleep(1)
        if (time.time()-start_time) > timeout_time:
            raise RuntimeError('Maximal waiting time reached')
    bckgname = sorted(glob.glob(temp_folder+'IrisNcpa_*bckg*.fits'))[-1]
    print('Bckgname : '+bckgname)
    
    iris_before = fits.getdata( temp_folder+'IrisAcq_beforecorr_{0}_DIT.fits'.format(tStart), 0 )
    iris_after = fits.getdata( temp_folder+'IrisAcq_aftercorr_{0}_DIT.fits'.format(tStart), 0 )
    bckg = fits.getdata(bckgname, 0).mean(0)

    iris_before -= bckg
    iris_after -= bckg
    iris_before[iris_before<=0]=1e-7
    iris_after[iris_after<=0]=1e-7
    
    pixshape = iris_before.shape[2]
    extenti = (-(pixshape//2)*31 , (pixshape//2)*31, -(pixshape//2)*31 , (pixshape//2)*31)
    
    if tel==0: #4 UTs at once
        fig, axarr = plt.subplots(4, 2, figsize=(8,12))
        for indTel in range(4): 
            iris_before_mean = cutIrisDet(iris_before,indTel+1)[10:20].mean(0)
            iris_after_mean = cutIrisDet(iris_after,indTel+1)[10:20].mean(0)
            vmax = np.max(iris_after_mean)
            norm = matplotlib.colors.LogNorm(vmax=vmax,vmin=vmax*1e-4)
            im = axarr[indTel][0].imshow(iris_before_mean,extent=extenti,norm=norm,cmap='gist_heat')
            axarr[indTel][0].set_xlabel('[mas]')
            axarr[indTel][0].set_title('UT{0} before last NCPA correction'.format(indTel+1))
            fig.colorbar(im, ax=axarr[indTel][0],fraction=0.046, pad=0.04,label="[ADU]")
    
            im=axarr[indTel][1].imshow(iris_after_mean,extent=extenti,norm=norm,cmap='gist_heat')
            axarr[indTel][1].set_xlabel('[mas]')
            axarr[indTel][1].set_title('UT{0} after last NCPA correction'.format(indTel+1))
            fig.colorbar(im, ax=axarr[indTel][1],fraction=0.046, pad=0.04,label="[ADU]")
        plt.tight_layout()
        if silent==1:
            plt.savefig('IrisAcq_PSFs_{0}.png'.format(tStart))
        else:
            plt.show()
    elif tel in [1,2,3,4]: #one UT measurement
        iris_before_mean = cutIrisDet(iris_before, tel)[10:20].mean(0)
        iris_after_mean = cutIrisDet(iris_after, tel)[10:20].mean(0)
        vmax = np.max(iris_after_mean)
        norm = matplotlib.colors.LogNorm(vmax=vmax,vmin=vmax*1e-4)
        fig, axarr = plt.subplots(1, 2, figsize=(8,6))
        im = axarr.ravel()[0].imshow(iris_before_mean,extent=extenti,norm=norm,cmap='gist_heat')
        axarr.ravel()[0].set_xlabel('[mas]')
        axarr.ravel()[0].set_title('UT{0} before last NCPA correction'.format(tel))
        fig.colorbar(im, ax=axarr.ravel()[0],fraction=0.046, pad=0.04,label="[ADU]")

        im=axarr.ravel()[1].imshow(iris_after_mean,extent=extenti,norm=norm,cmap='gist_heat')
        axarr.ravel()[1].set_xlabel('[mas]')
        axarr.ravel()[1].set_title('UT{0} after last NCPA correction'.format(tel))
        fig.colorbar(im, ax=axarr.ravel()[1],fraction=0.046, pad=0.04,label="[ADU]")
        plt.tight_layout()
        if silent==1:
            plt.savefig('IrisAcq_PSFs_{0}.png'.format(tStart))
        else:
            plt.show()
    else:
       print("WRONG TELESCOPE NUMBER")
