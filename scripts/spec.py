"""Plot log spectrograms and print measures for a list of WAV files."""
import sys, numpy as np
from scipy.io import wavfile
from scipy import signal
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
fs = sys.argv[2:]; out = sys.argv[1]
n=len(fs); cols=3; rows=(n+2)//3
fig,ax=plt.subplots(rows,cols,figsize=(15,3.2*rows)); ax=np.atleast_1d(ax).ravel()
for a,p in zip(ax,fs):
    sr,x=wavfile.read(p); x=x/32768
    f,t,S=signal.spectrogram(x,sr,nperseg=8192,noverlap=6144,window='hann')
    a.pcolormesh(t,f,10*np.log10(S+1e-12),vmin=-110,vmax=-30,shading='auto',cmap='magma')
    a.set_yscale('log'); a.set_ylim(30,16000); a.set_title(p.split('/')[-1],fontsize=9)
    e=np.convolve(x**2,np.ones(4800)/4800,'same'); db=10*np.log10(e+1e-12)-10*np.log10(e.max()+1e-12)
    ipk=e.argmax(); idx=np.where(db[ipk:]<-30)[0]; t30=(idx[0]/sr) if len(idx) else None
    S2=S.mean(1); cen=(f*S2).sum()/S2.sum()
    print(f"{p.split('/')[-1]:14s} dur {len(x)/sr:5.1f} peak@{ipk/sr:5.2f}s -30dB after {t30} centroid {cen:6.0f} Hz rms {np.sqrt((x**2).mean()):.3f}")
for a in ax[n:]: a.axis('off')
plt.tight_layout(); plt.savefig(out,dpi=70)
