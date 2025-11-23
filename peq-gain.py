import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import sys
import re

def peaking_eq(fc, gain_db, Q, fs):
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

def low_shelf_eq(fc, gain_db, Q, fs):
    A = 10**(gain_db/40.0)
    w0 = 2 * np.pi * fc / fs
    sn = np.sin(w0)
    cs = np.cos(w0)
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

def high_shelf_eq(fc, gain_db, Q, fs):
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

def parse_peq_file(filename):
    """
    Parse PEQ file format.
    Returns: (preamp_db, bands_list, postamp_db)

    bands_list format: [(type, fc, gain_db, Q), ...]
    where type is 'low_shelf', 'high_shelf', or 'peaking'
    """
    bands = []
    preamp_db = 0.0
    postamp_db = 0.0

    filter_type_map = {
        'LSC': 'low_shelf',
        'LS': 'low_shelf',
        'HSC': 'high_shelf',
        'HS': 'high_shelf',
        'PK': 'peaking'
    }

    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()

                # Parse Preamp
                if line.startswith('Preamp:'):
                    match = re.search(r'Preamp:\s*([-+]?\d+\.?\d*)\s*dB\s*', line)
                    if match:
                        preamp_db = float(match.group(1))

                # Parse Postamp
                elif line.startswith('Postamp:'):
                    match = re.search(r'Postamp:\s*([-+]?\d+\.?\d*)\s*dB\s*', line)
                    if match:
                        postamp_db = float(match.group(1))

                # Parse Filter lines
                elif line.startswith('Filter'):
                    # Example: Filter 1: ON LSC Fc 40 Hz Gain 5.0 dB Q 1.0
                    status_match = re.search(r'Filter\s+\d+:\s+(ON|OFF)', line)
                    if not status_match or status_match.group(1) != 'ON':
                        continue

                    parts = line.split()

                    # Find filter type (LSC, HSC, PK)
                    ftype = None
                    for part in parts:
                        if part in filter_type_map:
                            ftype = filter_type_map[part]
                            break

                    if not ftype:
                        continue

                    # Extract Fc (frequency)
                    fc_match = re.search(r'Fc\s+([-+]?\d+\.?\d*)\s*Hz', line)
                    if not fc_match:
                        continue
                    fc = float(fc_match.group(1))

                    # Extract Gain
                    gain_match = re.search(r'Gain\s+([-+]?\d+\.?\d*)\s*dB', line)
                    if not gain_match:
                        continue
                    gain_db = float(gain_match.group(1))

                    # Extract Q
                    q_match = re.search(r'Q\s+([-+]?\d+\.?\d*)', line)
                    if q_match:
                        Q = float(q_match.group(1))
                    else:
                        # If Q is missing:
                        # PK filters usually require Q, but shelves (LS/HS) might not.
                        # Default for LS/HS is 0.707 (Butterworth)
                        if raw_type in ['LS', 'HS', 'LSC', 'HSC']:
                            Q = 0.707
                        else:
                            # If it's a Peak filter without Q, we skip or default (skipping is safer)
                            print(f"Warning: Skipping Filter (PK without Q): {line}")
                            continue

                    # Add to bands: (type, fc, gain_db, Q)
                    bands.append((ftype, fc, gain_db, Q))

    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing file: {e}")
        sys.exit(1)

    return preamp_db, bands, postamp_db

# Main script
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python peq-gain.py <peq_file>")
        print("\nExample PEQ file format:")
        print("Preamp: -5.5 dB")
        print("Filter 1: ON LSC Fc 40 Hz Gain 5.0 dB Q 1.0")
        print("Filter 2: ON PK Fc 7600 Hz Gain 4.0 dB Q 3.0")
        print("Postamp: 10.5 dB")
        sys.exit(1)

    peq_file = sys.argv[1]

    # Parse PEQ file
    preamp_db, bands, postamp_db = parse_peq_file(peq_file)

    if not bands:
        print("Error: No enabled filters found in PEQ file.")
        sys.exit(1)

    print(f"Loaded {len(bands)} filter(s) from '{peq_file}'")
    if preamp_db != 0.0:
        print(f"Preamp: {preamp_db:.1f} dB")
    if postamp_db != 0.0:
        print(f"Postamp: {postamp_db:.1f} dB")
    print("\nFilters:")
    for i, (ftype, fc, gain_db, Q) in enumerate(bands, 1):
        print(f"  {i}. {ftype:11s} Fc={fc:7.1f} Hz  Gain={gain_db:+6.1f} dB  Q={Q:.2f}")
    print()

    # Audio parameters
    fs = 48000
    freqstart = 20
    freqend = fs//2

    # Choose spacing method
    USE_LOG_SPACING = True

    # Generate frequency array
    if USE_LOG_SPACING:
        freqs = np.logspace(np.log10(freqstart), np.log10(freqend), 10000)
    else:
        freqs = np.linspace(freqstart, freqend, 10000)

    w = 2 * np.pi * freqs / fs

    # Calculate combined frequency response
    H_total = np.ones_like(w, dtype=complex)

    for ftype, fc, gain_db, Q in bands:
        if ftype == 'peaking':
            b, a = peaking_eq(fc, gain_db, Q, fs)
        elif ftype == 'low_shelf':
            b, a = low_shelf_eq(fc, gain_db, Q, fs)
        elif ftype == 'high_shelf':
            b, a = high_shelf_eq(fc, gain_db, Q, fs)
        else:
            continue

        _, h = signal.freqz(b, a, worN=w)
        H_total *= h

    G_total_db = 20 * np.log10(np.abs(H_total))
    max_gain_db = np.max(G_total_db)
    min_gain_db = np.min(G_total_db)

    # Calculate pre-attenuation (from EQ analysis)
    calculated_pre_atten_db = max_gain_db + 0.1

    # Use Preamp from file if specified, otherwise use calculated
    if preamp_db != 0.0:
        # Preamp in file is typically negative (attenuation)
        pre_atten_db = abs(preamp_db)
        print(f"Using Preamp from file: {preamp_db:.1f} dB")
    else:
        pre_atten_db = calculated_pre_atten_db
        print(f"Calculated Preamp: {-pre_atten_db:.1f} dB")

    # Calculate safe post-gain
    safe_post_gain_db = max_gain_db - min_gain_db

    # Use Postamp from file if specified
    if postamp_db != 0.0:
        print(f"Using Postamp from file: {postamp_db:.1f} dB")
        actual_post_gain = postamp_db
    else:
        actual_post_gain = safe_post_gain_db

    result = f'Combined EQ Frequency Response {freqstart}–{freqend} Hz\nPre-attenuation: {pre_atten_db:.2f} dB\nSafe post-gain: {safe_post_gain_db:.2f} dB'

    if postamp_db != 0.0:
        result += f' (File: {postamp_db:.1f} dB)'

    print(f"\nAnalysis Results:")
    print(f"  Max boost in EQ: {max_gain_db:.2f} dB")
    print(f"  Max cut in EQ: {min_gain_db:.2f} dB")
    print(f"  Required pre-attenuation: {calculated_pre_atten_db:.2f} dB")
    print(f"  Safe post-EQ amplification: {safe_post_gain_db:.2f} dB")

    # Plot
    plt.rcParams.update({'font.size': 10})
    plt.rcParams['figure.dpi'] = 300

    plt.figure()
    plt.semilogx(freqs, G_total_db)
    plt.title(result)
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Gain (dB)')
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.axhline(y=0, color='k', linestyle='-', alpha=0.3)
    if preamp_db != 0:
        plt.axhline(y=-preamp_db, color='r', linestyle='--', label='Current Preamp Limit')
    plt.tight_layout()
    plt.show()
