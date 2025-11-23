import numpy as np
from scipy import signal
import matplotlib.pyplot as plt

def peaking_eq(fc, Q, gain_db, fs):
    A = 10**(gain_db/40.0)
    w0 = 2 * np.pi * fc / fs
    alpha = np.sin(w0)/(2*Q)

    b0 = 1 + alpha*A
    b1 = -2*np.cos(w0)
    b2 = 1 - alpha*A
    a0 = 1 + alpha/A
    a1 = -2*np.cos(w0)
    a2 = 1 - alpha/A

    b = [b0/a0, b1/a0, b2/a0]
    a = [1, a1/a0, a2/a0]
    return b, a

def low_shelf_eq(fc, Q, gain_db, fs):
    # Q here serves as shelf slope parameter (S). For simplicity, use Q=1 for standard slope.
    A = 10**(gain_db/40.0)
    w0 = 2 * np.pi * fc / fs
    sn = np.sin(w0)
    cs = np.cos(w0)
    # Using Q as slope parameter with assumption Q=1 for standard behavior
    alpha = sn/2 * np.sqrt((A + 1/A)*(1/Q - 1) + 2)
    beta = 2*np.sqrt(A)*alpha

    b0 =    A*((A+1) - (A-1)*cs + beta)
    b1 =  2*A*((A-1) - (A+1)*cs)
    b2 =    A*((A+1) - (A-1)*cs - beta)
    a0 =        (A+1) + (A-1)*cs + beta
    a1 =   -2*((A-1) + (A+1)*cs)
    a2 =        (A+1) + (A-1)*cs - beta

    b = [b0/a0, b1/a0, b2/a0]
    a = [1, a1/a0, a2/a0]
    return b, a

def high_shelf_eq(fc, Q, gain_db, fs):
    # Q serves as shelf slope parameter (S). For simplicity, use Q=1 for standard slope.
    A = 10**(gain_db/40.0)
    w0 = 2 * np.pi * fc / fs
    sn = np.sin(w0)
    cs = np.cos(w0)
    alpha = sn/2 * np.sqrt((A + 1/A)*(1/Q - 1) + 2)
    beta = 2*np.sqrt(A)*alpha

    b0 =    A*((A+1) + (A-1)*cs + beta)
    b1 = -2*A*((A-1) + (A+1)*cs)
    b2 =    A*((A+1) + (A-1)*cs - beta)
    a0 =        (A+1) - (A-1)*cs + beta
    a1 =    2*((A-1) - (A+1)*cs)
    a2 =        (A+1) - (A-1)*cs - beta

    b = [b0/a0, b1/a0, b2/a0]
    a = [1, a1/a0, a2/a0]
    return b, a

fs = 48000 # sample rate
freqstart = 20
freqend = fs//2
freqs = np.linspace(freqstart, freqend, 10000)
w = 2 * np.pi * freqs / fs

# Define bands as tuples: (type, fc, Q, gain_db)
bands = [
    ('low_shelf', 65, 0.7, 8.5),
    ('peaking', 210, 1.1, -2.3),
    ('peaking', 2150, 2.2, 1.5),
    ('peaking', 3000, 3.0, -2.2),
    ('peaking', 16000, 1.0, -5.0),
    ('high_shelf', 3000, 0.7, 3.0)
]

H_total = np.ones_like(w, dtype=complex)

for ftype, fc, Q, gain_db in bands:
    if ftype == 'peaking':
        b, a = peaking_eq(fc, Q, gain_db, fs)
    elif ftype == 'low_shelf':
        b, a = low_shelf_eq(fc, Q, gain_db, fs)
    elif ftype == 'high_shelf':
        b, a = high_shelf_eq(fc, Q, gain_db, fs)
    else:
        continue

    _, h = signal.freqz(b, a, worN=w)
    H_total *= h

G_total_db = 20 * np.log10(np.abs(H_total))
max_gain_db = np.max(G_total_db)
min_gain_db = np.min(G_total_db)

# Pre-attenuation needed to prevent clipping from EQ boost
pre_atten_db = max_gain_db + 0.1  # Adding 0.1 dB safety margin

# After pre-attenuation and EQ, how much can we safely amplify?
# The range after pre-atten becomes: [min_gain - max_gain, 0]
# So we can amplify by up to: max_gain - min_gain
safe_post_gain_db = max_gain_db - min_gain_db

combined_db = f"{pre_atten_db:.2f}"
result = f'Combined EQ Frequency Response {freqstart}–{freqend} Hz\nPre-atten: {combined_db} dB\nSafe post-gain: {safe_post_gain_db:.2f} dB'
print(result)
print(f"\nSummary:")
print(f"  Max boost in EQ: {max_gain_db:.2f} dB")
print(f"  Max cut in EQ: {min_gain_db:.2f} dB")
print(f"  Required pre-attenuation: {pre_atten_db:.2f} dB")
print(f"  Safe post-EQ amplification: {safe_post_gain_db:.2f} dB")

plt.rcParams.update({'font.size': 10})
plt.rcParams['figure.dpi'] = 300

plt.semilogx(freqs, G_total_db)
plt.title(result)
plt.xlabel('Frequency (Hz)')
plt.ylabel('Gain (dB)')
plt.grid(True, which='both', ls='--')
plt.tight_layout()
plt.show()
