from typing import List
import argparse
import re
import math
import sys

def vol_dB_to_linear(dB):
    """
    Convert a volume level from decibels (dB) to a linear scale.
    """
    return math.pow(10.0, dB / 20.0)

def vol_linear_to_dB(linear):
    """
    Convert a volume level from a linear scale to decibels (dB).
    """
    return 20.0 * math.log10(linear)

MAX_FILTERS=32
FREQ_MIN=0
FREQ_MAX=24000

# eq_filter_t
EQF_OFF=0
EQF_BELL=1
EQF_HIPASS=2
EQF_HISHELF=3
EQF_LOPASS=4
EQF_LOSHELF=5
EQF_NOTCH=6
EQF_RESONANCE=7
EQF_ALLPASS=8
EQF_BANDPASS=9
EQF_LADDERPASS=10
EQF_LADDERREJ=11

# eq_filter_mode_t
EFM_RLC_BT=0
EFM_RLC_MT=1
EFM_BWC_BT=2
EFM_BWC_MT=3
EFM_LRX_BT=4
EFM_LRX_MT=5
EFM_APO_DR=6

# eq_mode_t
EQ_MODE_TO_NR = {
    "PEM_IIR": 0,
    "PEM_FIR": 1,
    "PEM_FFT": 2,
    "PEM_SPM": 3
}

# Mapping of RoomEq filter types to LSP plugin filter types
PEQ_TO_LSP_FILTER = {
    "LP": EQF_LOPASS,           # Low-Pass
    "LPQ": EQF_LOPASS,          # Low-Pass with Q
    "HP": EQF_HIPASS,           # High-Pass
    "HPQ": EQF_HIPASS,          # High-Pass with Q
    "LSC": EQF_LOSHELF,         # Low-Shelf
    "LS": EQF_LOSHELF,          # Low-Shelf (same as LSC)
    "HSC": EQF_HISHELF,         # High-Shelf
    "HS": EQF_HISHELF,          # High-Shelf (same as HSC)
    "PK": EQF_BELL,             # Bell
    "MODAL": EQF_BELL,          # Bell
    "PEQ": EQF_BELL,            # Bell
    "BP": EQF_BANDPASS,         # Band-Pass
    "LS 6DB": EQF_LOSHELF,      # Low-Shelf filter (6 dB per octave with corner freq.)
    "HS 6DB": EQF_LOSHELF,      # High-Shelf filter (6 dB per octave with corner freq.)
    "LS 12DB": EQF_LOSHELF,     # Low-Shelf filter (12 dB per octave with corner freq.)
    "HS 12DB": EQF_LOSHELF,     # High-Shelf filter (12 dB per octave with corner freq.)
    "NO": EQF_NOTCH,            # Notch
    "AP": EQF_ALLPASS           # All-Pass
}

# for parameter translations, see
# lsp-plugins-para-equalizer/src/main/ui/para_equalizer.cpp:para_equalizer_ui::import_rew_file()
"""
"Input gain (G)" input, control, 0 to 10, default 1, logarithmic
"Output gain (G)" input, control, 0 to 10, default 1, logarithmic
"Equalizer mode" input, control, 0 to 3, default 0, integer
"FFT reactivity (ms)" input, control, 0 to 1, default 0, logarithmic
"Shift gain (G)" input, control, 0 to 100, default 1, logarithmic
"Graph zoom (G)" input, control, 0.00794328 to 1, default 0.0266072, logarithmic
"Filter select" input, control, 0 to 7, default 0, integer
...
"Filter type Left 0" input, control, 0 to 11, default 0, integer
"Filter mode Left 0" input, control, 0 to 6, default 0, integer
"Filter slope Left 0" input, control, 0 to 3, default 0, integer
"Frequency Left 0 (Hz)" input, control, 10 to 24000, default 69.9927, logarithmic
"Filter Width Left 0 (oct)" input, control, 0 to 12, default 6
"Gain Left 0 (G)" input, control, 0.01585 to 63.0957, default 1, logarithmic
"Quality factor Left 0" input, control, 0 to 100, default 0
"Hue Left 0" input, control, 0 to 1, default 0
"""

def debug_write(line: str):
    if not verbose:
        return
    sys.stderr.write(line + '\n')

def nodes_to_string(nodes: List) -> str:
    formatted = ""
    for d in nodes:
        formatted += "".join(f'\n                            "{key}" {value}' for key, value in d.items())
    return formatted

def parse_peq_file(peq_file_path: str, Left_or_Right: str, verbose: bool) -> List:
    nodes = []
    # Open and read the PEQ file
    with open(peq_file_path, 'r') as f:
        peq_data = f.read()

    if Left_or_Right.lower() == 'left':
        which = 'Left'
    elif Left_or_Right.lower() == 'right':
        which = 'Right'
    else:
        debug_write("Left or Right?")
        exit(1)

    #debug_write(repr(peq_data))
    # Regular expression to match filter blocks in the PEQ file
    filter_pattern = re.compile(r"Filter \d+:\s*(ON|OFF)\s*([A-Za-z0-9\- ]+)\s*Fc\s*([0-9.]+)\s*Hz\s*Gain\s*([0-9.-]+)\s*dB\s*Q\s*([0-9.]+)")
    preamp_pattern = re.compile(r"Preamp:\s*(-?[0-9.-]+)\s*dB")
    # Check for Preamp line
    preamp_match = preamp_pattern.search(peq_data)
    if preamp_match:
        if len(nodes) == MAX_FILTERS:
            debug_write(f'Reached maximum filter amount {MAX_FILTERS}')
            return nodes

        gain = float(preamp_match.group(1))
        gain_linear = vol_dB_to_linear(gain)
        # Create a High-Shelf node for preamp with Frequency 0 Hz and the preamp gain
        preamp_node = {
                f"Filter type {which} {len(nodes)}": EQF_HISHELF,
                f"Filter mode {which} {len(nodes)}": 0,  # RLC (BT)
                f"Filter slope {which} {len(nodes)}": 0,  # x1
                f"Frequency {which} {len(nodes)} (Hz)": 0,  # 0 Hz for preamp
                f"Filter Width {which} {len(nodes)} (oct)": 6,
                f"Gain {which} {len(nodes)} (G)": gain_linear,
                f"Quality factor {which} {len(nodes)}": 1,
                f"Hue {which} {len(nodes)}": 0
        }
        debug_write(f'Preamp {gain} dB (linear {gain_linear})')
        nodes.append(preamp_node)

    # Parse each filter block, skipping comments and lines after '#'
    for match in filter_pattern.finditer(peq_data):
        if len(nodes) == MAX_FILTERS:
            debug_write(f'Reached maximum filter amount {MAX_FILTERS}')
            return nodes

        status = match.group(1)
        filter_type_str = match.group(2).strip()
        frequency = float(match.group(3))
        gain = float(match.group(4))
        q_value = float(match.group(5))

        # Skip filter if it is OFF
        if status == "OFF":
            continue

        # Map the filter type to LSP plugin
        if filter_type_str in PEQ_TO_LSP_FILTER:
            filter_type_nr = PEQ_TO_LSP_FILTER[filter_type_str]
        else:
            raise ValueError(f"Invalid PEQ filter '{filter_type_str}', not in: {list(PEQ_TO_LSP_FILTER.keys())}")

        if frequency > FREQ_MAX or frequency < FREQ_MIN:
            raise ValueError(f"Invalid frequency {frequency}, should be {FREQ_MIN}–{FREQ_MAX}")

        debug_write(f'status={status} filter={filter_type_str}({filter_type_nr}) f={frequency} gain={gain} q={q_value}')

        # Round the frequency to nearest integer
        rounded_frequency = round(frequency)

        # Construct the filter node configuration
        node = {
            f"Filter type {which} {len(nodes)}": filter_type_nr,
            f"Filter mode {which} {len(nodes)}": 0,  # RLC (BT)
            f"Filter slope {which} {len(nodes)}": 0,  # x1
            f"Frequency {which} {len(nodes)} (Hz)": rounded_frequency,
            f"Filter Width {which} {len(nodes)} (oct)": 6,
            f"Gain {which} {len(nodes)} (G)": vol_dB_to_linear(gain),
            f"Quality factor {which} {len(nodes)}": q_value,
            f"Hue {which} {len(nodes)}": 0
        }
        nodes.append(node)

    return nodes

parser = argparse.ArgumentParser(description='Parse PEQ file (AutoEq / EasyEffects format) and output pipewire ladspa plugin configuration for para_equalizer_x32_lr')
parser.add_argument('--peq_left', required=True, type=str, help='Path to the left channel peq')
parser.add_argument('--peq_right', required=True, type=str, help='Path to the right channel peq')
parser.add_argument('--targetdev', required=True, type=str, help='Target sink device')
parser.add_argument('--verbose', action='store_true', help='Show verbose information about the audio file')
args = parser.parse_args()
peq_left = args.peq_left
peq_right = args.peq_right
targetdev = args.targetdev
verbose: bool = args.verbose

context_string = f"""context.modules = [
    {{ name = libpipewire-module-filter-chain
        args = {{
            node.description = "LSP para_equalizer_x32_lr"
            media.name       = "LSP para_equalizer_x32_lr"
            audio.rate = 48000
            audio.channels = 2
            audio.position = [FL FR]
            capture.props = {{
                node.name = "effect_input.PEQx32"
                media.class = "Audio/Sink"
                target.object = \"{targetdev}\"
            }}
            playback.props = {{
                node.name = "effect_output.PEQx32"
                node.passive = true
            }}
            filter.graph = {{
                nodes = [
                    {{
                        type = ladspa
                        name = "LSP PEQx32"
                        plugin = /usr/lib64/ladspa/lsp-plugins-ladspa.so
                        label = "http://lsp-plug.in/plugins/ladspa/para_equalizer_x32_lr"
                        control = {{
                            \"Equalizer mode\" {EQ_MODE_TO_NR["PEM_FIR"]}"""
print(context_string)

left_nodes = parse_peq_file(peq_left, 'Left', verbose)
print(nodes_to_string(left_nodes))
right_nodes = parse_peq_file(peq_right, 'Right', verbose)
print(nodes_to_string(right_nodes))
print("\n                        }\n                    }\n                ]\n            }\n        }\n    }\n]")

