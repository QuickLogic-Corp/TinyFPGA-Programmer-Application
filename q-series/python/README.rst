Programming Quickfeather boards
===============================

Installation
------------

To install, clone the repository and install the tinyfpgab dependancy

.. code:: sh

   git clone --recursive https://github.com/QuickLogic-Corp/TinyFPGA-Programmer-Application.git
   pip3 install tinyfpgab

On native Ubuntu the lsusb command should display something similar to
the following:

.. code:: sh

   lsusb
   Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
   Bus 002 Device 029: ID 1d50:6140 OpenMoko, Inc.

If the OpenMoko device is not present (it could also have ID 1d50:6130)
then run the following commands.

.. code:: sh

   pip3 install apio
   apio drivers --serial-enable
   Serial drivers enabled
   Unplug and reconnect your board

Recommend setting up an alias to simplify programming using the editor
of your choice to edit ~/.bashrc:

alias qfprog="python3
~/TinyFPGA-Programmer-Application/tinyfpga-programmer-gui.py"

.. code:: sh

   source ~/.bashrc

Programming
-----------

This version of tinyfpga-programmer-gui.py is restricted to CLI mode.
CLI mode allows you to specify which port to use, and thus works even
when the system does not report USB VID and PID. This document focuses
on CLI mode.

Help is available by running with the --help parameter:

.. code:: sh

   python3 tinyfpga-programmer-gui --help

This will result in:

::

   usage: tinyfpga-programmer-gui.py [-h] [--m4app app.bin]
                                     [--bootloader boot.bin]
                                     [--bootfpga fpga.bin] [--reset]
                                     [--port /dev/ttySx] [--crc] [--checkrev]
                                     [--update] [--mfgpkg qf_mfgpkg/]

   optional arguments:
     -h, --help            show this help message and exit
     --m4app app.bin       m4 application program
     --bootloader boot.bin, --bl boot.bin
                           m4 bootloader program WARNING: do you really need to
                           do this? It is not common, and getting it wrong can
                           make you device non-functional
     --bootfpga fpga.bin   FPGA image to be used during programming WARNING: do
                           you really need to do this? It is not common, and
                           getting it wrong can make you device non-functional
     --reset               reset attached device
     --port /dev/ttySx     use this port
     --crc                 print CRCs
     --checkrev            check if CRC matches (flash is up-to-date)
     --update              program flash only if CRC mismatch (not up-to-date)
     --mfgpkg qf_mfgpkg/   directory containing all necessary binaries

The programmer allows you to specify various options:

-  The *--port port-name* option is used to tell the programmer which
   serial port the QuickFeather board is connected to. The form of
   *port-name* varies depending on the system:

   -  COM## on PC/Windows
   -  /dev/ttyS## on PC/wsl1/Ubuntu18 (where the ## is the same as the
      COM## shown by device manager under Windows)
   -  /dev/ttyACM# on PC/Ubuntu18

-  The *--m4app app.bin* tells the programmer to program the file
   *app.bin* as the m4 application -- this is the common case
-  The *--reset* option tells the programm to reset the board, which
   will result in the bootloader being restarted, and if the user button
   is not pressed, the bootloader will then laod and start the most
   recent m4app.
-  Example: *qfprog --port /dev/ttyS8 --m4app
   output/bin/qf_helloworldsw.bin --reset* will program the m4app with
   qf_helloworldsw and then run it
-  The *--crc* option simples prints the crc values for each of binaries
   that are programmed into the flash memory
-  The *--checkrev* option compares the crc for a binary specified as an
   option to the binary file progammed into the flash
-  Example: *qfprog --port /dev/ttyS8 --m4app
   output/bin/qf_helloworldsw.bin --checkrev* will compare the crc for
   file output/bin/qf_helloworldsw.bin with the crc for the binary
   programmed into the m4app location of the flash memory
-  The *--update* option causes the progammer to check the crc of any
   specified binary against the crc of the binary progammed into the
   flash, and only programmer the specified binary if it the crc is
   different

**Danger Zone**

-  The *--bootloader boot.bin* option tells the programmer to program
   the file *boot.bin* as the bootloader application. **If the
   programming fails for any reason, or the boot.bin file doesn't work
   as expected the QuickFeather will become non-functional and only
   recoverable by using J-LINK**
-  The *--bootfpga fpga.bin* option tells the programmer to program the
   file *fpga.bin* as the fpga image for the bootloader. **If the
   programming fails for any reason, or the fpga.bin file doesn't work
   as expected the QuickFeather will become non-functional and only
   recoverable by using J-LINK**
-  the *--mfgpkg mfgpkg/* option can be used to update all of the
   QuickFeather firmware or restore it to the factory delivered state.
   The programmer expects the *mfgpkg/* directory will contain
   qf_bootloader.bin, qf_bootfpga.bin and qf_helloworldsw.bin. The
   recommended update method is to use the --update option with the
   --mfgpkg option

Flash memory map
----------------

The TinyFPGA programmer has a flash memory map for 5 bin files, and
corresponding CRC for each of them. The 5 bin files are:

-  bootloader
-  bootfpga
-  m4app
-  appfpga (for future use)
-  appffe (for future use)

The bootloader is loaded by a reset. It handles either communicating
with the TinyFPGA-Programmer to load new bin files into the flash, or it
loads m4 app binary and transfers control to it. The bootfpga area
contains the binary for the fpga image that the bootlaoder uses. The m4
app image is expected to contain and load any fpga image that it
requires.

The flash memory map defined for q-series devices is:

+-------+-------+-------+-------+-------+-------+-------+-------+
| Item  | S     | Start | Size  | End   | Start | Size  | End   |
|       | tatus |       |       |       |       |       |       |
+=======+=======+=======+=======+=======+=======+=======+=======+
| bootl | Used  | 0     | 0     | 0     | -     | 6     | 6     |
| oader |       | x0000 | x0001 | x0000 |       | 5,536 | 5,536 |
|       |       | _0000 | _0000 | _FFFF |       |       |       |
+-------+-------+-------+-------+-------+-------+-------+-------+
| boo   | Used  | 0     | 8     | 0     | 6     | 8     | 6     |
| tfpga |       | x0001 |       | x0001 | 5,536 |       | 5,544 |
| CRC   |       | _0000 |       | _0007 |       |       |       |
+-------+-------+-------+-------+-------+-------+-------+-------+
| ap    | F     | 0     | 8     | 0     | 6     | 8     | 6     |
| pfpga | uture | x0001 |       | x0001 | 9,632 |       | 9,640 |
| CRC   |       | _1000 |       | _1007 |       |       |       |
+-------+-------+-------+-------+-------+-------+-------+-------+
| a     | F     | 0     | 8     | 0     | 7     | 8     | 7     |
| ppffe | uture | x0001 |       | x0001 | 3,728 |       | 3,736 |
| CRC   |       | _2000 |       | _2007 |       |       |       |
+-------+-------+-------+-------+-------+-------+-------+-------+
| M4app | Used  | 0     | 8     | 0     | 7     | 8     | 7     |
| CRC   |       | x0001 |       | x0001 | 7,824 |       | 7,832 |
|       |       | _3000 |       | _3007 |       |       |       |
+-------+-------+-------+-------+-------+-------+-------+-------+
| bootl | Used  | 0     | 8     | 0     | 8     | 8     | 8     |
| oader |       | x0001 |       | x0001 | 1,920 |       | 1,928 |
| CRC   |       | _4000 |       | _4007 |       |       |       |
+-------+-------+-------+-------+-------+-------+-------+-------+
| boo   | Used  | 0     | 0     | 0     | 13    | 13    | 26    |
| tfpga |       | x0002 | x0002 | x0003 | 1,072 | 1,072 | 2,144 |
|       |       | _0000 | _0000 | _FFFF |       |       |       |
+-------+-------+-------+-------+-------+-------+-------+-------+
| ap    | F     | 0     | 0     | 0     | 26    | 13    | 39    |
| pfpga | uture | x0004 | x0002 | x0005 | 2,144 | 1,072 | 3,216 |
|       |       | _0000 | _0000 | _FFFF |       |       |       |
+-------+-------+-------+-------+-------+-------+-------+-------+
| a     | F     | 0     | 0     | 0     | 39    | 13    | 52    |
| ppffe | uture | x0006 | x0002 | x0007 | 3,216 | 1,072 | 4,288 |
|       |       | _0000 | _0000 | _FFFF |       |       |       |
+-------+-------+-------+-------+-------+-------+-------+-------+
| M4app | Used  | 0     | 0     | 0     | 52    | 45    | 97    |
|       |       | x0008 | x0006 | x000E | 4,288 | 0,560 | 4,848 |
|       |       | _0000 | _E000 | _DFFF |       |       |       |
+-------+-------+-------+-------+-------+-------+-------+-------+
