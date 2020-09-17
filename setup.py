#!/usr/bin/env python3
# ============================================================================
""" 
setup.py is a file for the first set of setting up T4Train and is dependencies.
It upgrades pip and then installs PyAudio for Windows. PyAudio is installed in
requirements.txt for MacOS & Linux.
"""
# ============================================================================


import os
from sys import platform


# upgrading pip
os.system("python -m pip install --upgrade pip")


# installing pipwin to install pyaudio for Windows
if platform == "win32":

    os.system("python -m pip install pipwin")
    os.system("pipwin install pyaudio")