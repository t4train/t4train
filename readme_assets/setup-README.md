# T4Train Setup

## Contents

- [Requirements](#Requirements)
	- [Windows](#Windows_Req)
	- [MacOS & Linux](#Mac_Linux_Req)
- [Setup](#Setup)
	- [Setting up a virtual environment](#Virtual_Env)
		- [Windows](#Windows_Env)
		- [MacOS & Linux](#Mac_Linux_Env)
	- [Installing dependencies]((#Dependencies)
- [Troubleshooting](#Troubleshooting)


## Requirements

T4Train requires Python 3. [Anaconda](https://www.anaconda.com/distribution/)is strongly recommended 
as your Python environment for environment and package management to make setup easier.
It includes several of the packages needed for T4Train.

If you do not install Anaconda for Python, T4Train may still work, but package installation
could be more difficult.

#### Windows Users

Once installed, verify Anaconda is your Python interpreter by opening Anaconda Prompt from the Start 
Menu and entering:
    

    where python

It should respond with something like:

    C:\Users\[user]\AppData\Local\Continuum\anaconda3\python.exe


#### Mac/Linux Users

Once installed, verify that your terminal is using Anaconda by entering:
    

    which python

It should respond with something like:

    /home/[user]/anaconda3/bin/python

After you've verified that Anaconda is being used as your python environment,
set up your [virtual environment](#Virtual_Env).

## Setup

### Setting Up a Virtual Environment

We strongly recommend setting up a virtual environment to avoid clashing with your current
environment and making setup easier. The following instructions are for Anaconda users, so if
you are not using Anaconda, try making a virtual environment in [Windows](#Windows_Env) or
[MacOS & Linux](#Mac_Linux_Env).

If using Anaconda, update your environment before installing dependencies with:

    $ conda update conda
    $ conda update --all

Check your version of Python by typing the following in terminal for MacOS & Linux and
Anaconda Prompt (in the Windows Start Menu) for Windows:

	$ python --version

Navigate to the T4Train directory in Terminal or Anaconda Prompt and create an environment 
(called env) and activate it:

	$ conda create -n env python=x.x anaconda
	$ conda activate env

Replace x.x with your Python version number.

Press y to proceed.

To leave the environment after you no longer need it:

	$ conda deactivate

After you have created your virtual environment, install the [dependencies](#Dependencies).

#### Windows Users

Without Anaconda, you can get up a virtual environment in the T4Train directory in Command 
Prompt or Powershell like this:

    $ py -m pip install --upgrade pip
    $ py -m pip install --user virtualenv
    $ py -m venv env

To activate the virtual environment:

    $ .\env\Scripts\activate

To confirm you're in the virtual environment, check the location of your Python interpreter.

    $ where python
    .../env/bin/python.exe

To leave the environment after you no longer need it:

	$ deactivate

#### Mac/Linux Users

Without Anaconda, you can get up a virtual environment in the T4Train directory in terminal 
like this:

    $ python3 -m pip install --user --upgrade pip
    $ python3 -m pip install --user virtualenv
    $ python3 -m venv env

To activate the virtual environment:

    $ source env/bin/activate

To confirm you're in the virtual environment, check the location of your Python interpreter.

    $ which python
    .../env/bin/python

To leave the environment after you no longer need it:

	$ deactivate

## Dependencies

All of the dependencies are listed in `requirements.txt`. To reduce the likelihood of environment
errors, install the dependencies inside a virtual environment with the following steps.

Navigate to the T4Train directory and activate the virtual environment in your terminal.
Run the following commands in terminal:

	$ python setup.py
	$ pip install -r requirements.txt

All of the T4Train dependencies should now be installed.

## Troubleshooting

### Pyaudio did not install properly

#### Windows Users

Run  `python --version` in terminal to find the Python version and bit number (e.g. 3.7.3 and 64bit (AMD64))

Find the corresponding `.whl` file: [lfd.uci.edu/~gohlke/pythonlibs/#pyaudio](lfd.uci.edu/~gohlke/pythonlibs/#pyaudio)

The number after `cp` is the version number and the number after `win` is the bit information

`cd` to the folder the file is saved in and run the following command with the name of your `.whl` file:

    $ pip install <file-name>

#### Linux Users

Run the follow command in terminal:

    $ sudo apt-get install libasound-dev

Download the portaudio archive from: [portaudio.com/download.html](portaudio.com/download.html)
    
`cd` to the directory with the tarball, unzip it, and configure:  

    $ tar -zxvf <portaudio file-name>
    $ ./configure && make

Then install Pyaudio:


    $ sudo make install
    $ sudo pip install pyaudio
