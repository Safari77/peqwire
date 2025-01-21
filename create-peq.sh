#!/bin/sh

# pactl list short sinks
# direct to ~/.config/pipewire/pipewire.conf.d/11-peqx32.conf or something
# get some configs from https://autoeq.app/ (select EasyEffects, and Download)
# or https://www.audiosciencereview.com/forum/index.php?threads/list-of-amirs-headphone-peq-filters.18590/
python peqwire.py --targetdev "alsa_output.usb-Topping_E30-00.HiFi__Headphones__sink" --peq_left senn-hd650.txt --peq_right senn-hd650.txt
