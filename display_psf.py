import argparse
import time
from astropy.io import fits
import argparse
import numpy as np
from scipy import signal as sig
from scipy import stats
from PySide2 import QtWidgets
from matplotlib import pyplot as plt
import os

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

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description="Record IRIS data cube")
	parser.add_argument('tel', type=int, choices=range(5), help="Telescope index. 0 for all telescopes")
	parser.add_argument('tstart', type=str, help="time of the measurement") 
	parser.add_argument('--silent','-s', type=int,default=0 , help="Silent=no pop-up, 0 = Not silent, 1=Silent. 0/1")
	args = parser.parse_args()
	
	temp_folder = "/vltuser/iss/temp_ncpa/" # for temporary storage of IRIS data on ISS


	# Transfer Iris acquisitions to ISS
	os.system("""FILE=$(ssh aral@waral "ls -tp /data/ARAL/INS_ROOT/SYSTEM/DETDATA/IrisAcq_beforecorr_{0}_DIT.fits | grep -m1 \"\""); scp aral@waral:$FILE {1} """.format(tstart, temp_folder))
	os.system("""FILE=$(ssh aral@waral "ls -tp /data/ARAL/INS_ROOT/SYSTEM/DETDATA/IrisAcq_aftercorr_{0}_DIT.fits | grep -m1 \"\""); scp aral@waral:$FILE {1} """.format(tstart, temp_folder))
	
	#Check existence of fits files on ISS
	timeout_time = 120
	start_time = time.time()
	while not (os.path.exists('{0}IrisAcq_beforecorr_{1}_DIT.fits'.format(temp_folder, tstart)) and os.path.exists('{0}IrisAcq_aftercorr_{1}_DIT.fits'.format(temp_folder, tstart)) ):
		time.sleep(1)
		if (time.time()-start_time) > timeout_time:
			raise RuntimeError('Maximal waiting time reached')
	bckgname = sorted(glob.glob(temp_folder+'IrisNcpa_*bckg*.fits'))[-1]
	print('Bckgname : '+bckgname)
	
	iris_before = fits.getdata( temp_folder+'IrisAcq_beforecorr_{0}_DIT.fits'.format(tstart), 0 )
	iris_after = fits.getdata( temp_folder+'IrisAcq_aftercorr_{0}_DIT.fits'.format(tstart), 0 )
	bckg = fits.getdata(bckgname, 0).mean(0)

	iris_before -= bckg
	iris_after -= bckg
	iris_before[iris_before<=0]=1e-7
	iris_after[iris_after<=0]=1e-7
	
	pixshape = iris_before.shape[2]
	extenti = (-(pixshape//2)*31 , (pixshape//2)*31, -(pixshape//2)*31 , (pixshape//2)*31)
	
	if args.tel==0: #4 UTs at once
		fig, axarr = plt.subplots(4, 2, figsize=(8,12))
		for indTel in range(4): 
			iris_before_mean = cutIrisDet(iris_before,indTel+1).mean(0)
			iris_after_mean = cutIrisDet(iris_after,indTel+1).mean(0)
			vmax = np.max(iris_after_mean)
			im = axarr[indTel][0].imshow(iris_before_mean,vmax=vmax,vmin=vmax*1e-4,extent=extenti,norm='log',cmap='gist_heat')
			axarr[indTel][0].set_xlabel('[mas]')
			axarr[indTel][0].set_title('UT{0} before last NCPA correction'.format(indTel+1))
			fig.colorbar(im, ax=axarr[indTel][0],fraction=0.046, pad=0.04,label="[ADU]")
	
			im=axarr[indTel][1].imshow(iris_after_mean,vmax=vmax,vmin=vmax*1e-4,extent=extenti,norm='log',cmap='gist_heat')
			axarr[indTel][1].set_xlabel('[mas]')
			axarr[indTel][1].set_title('UT{0} after last NCPA correction'.format(indTel+1))
			fig.colorbar(im, ax=axarr[indTel][1],fraction=0.046, pad=0.04,label="[ADU]")
		plt.tight_layout()
		if args.silent=='1':
			plt.savefig('IrisAcq_PSFs_{0}.png')
		else:
			plt.show()
	elif args.tel in [1,2,3,4]: #one UT measurement
		iris_before_mean = cutIrisDet(iris_before,args.tel).mean(0)
		iris_after_mean = cutIrisDet(iris_after,args.tel).mean(0)
		vmax = np.max(iris_after_mean)
		fig, axarr = plt.subplots(1, 2, figsize=(8,6))
		im = axarr.ravel()[0].imshow(iris_before_mean,vmax=vmax,vmin=vmax*1e-4,extent=extenti,norm='log',cmap='gist_heat')
		axarr.ravel()[0].set_xlabel('[mas]')
		axarr.ravel()[0].set_title('UT{0} before last NCPA correction'.format(args.tel))
		fig.colorbar(im, ax=axarr.ravel()[0],fraction=0.046, pad=0.04,label="[ADU]")

		im=axarr.ravel()[1].imshow(iris_after_mean,vmax=vmax,vmin=vmax*1e-4,extent=extenti,norm='log',cmap='gist_heat')
		axarr.ravel()[1].set_xlabel('[mas]')
		axarr.ravel()[1].set_title('UT{0} after last NCPA correction'.format(args.tel))
		fig.colorbar(im, ax=axarr.ravel()[1],fraction=0.046, pad=0.04,label="[ADU]")
		plt.tight_layout()
		if args.silent=='1':
			plt.savefig('IrisAcq_PSFs_{0}.png')
		else:
			plt.show()
	else:
	   print("WRONG TELESCOPE NUMBER")
