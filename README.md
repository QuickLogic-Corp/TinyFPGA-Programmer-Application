# TinyFPGA-Programmer-Application
Desktop application for programming TinyFPGA boards. Updated to python3 and to support QuickLogic's QuickFeather.  

# Programming Quickfeather boards

## Installation

1. clone the repository and install the tinyfpgab dependancy
```sh
git clone --recursive https://github.com/QuickLogic-Corp/TinyFPGA-Programmer-Application.git
pip3 install tinyfpgab
```

2. Connect the QuickFeather board, and set it to flash mode.  
   To put it into flash mode, press the `RST` button, and the LED should turn blue and start flashing.  
   Press the `USR` button within 5 seconds of pressing the `RST` button. The LED will turn green and go into breathing mode.  
   At this point, run `lsusb` on the terminal.  
   `lsusb` should display something similar to the following:

   ```sh
   lsusb
   ...
   Bus 002 Device 029: ID 1d50:6140 OpenMoko, Inc.
   ...
   ```
   or
   ```sh
   lsusb
   ...
   Bus 002 Device 029: ID 1d50:6130 OpenMoko, Inc.
   ...
   ```

   If the OpenMoko device is not present, then run the following commands.

   ```sh
   pip3 install apio
   apio drivers --serial-enable
   Serial drivers enabled
   Unplug and reconnect your board
   ```
   and then check the output of `lsusb` contains an entry as shown above.

3. Recommend setting up an alias to simplify programming using the editor of your choice to edit `~/.bashrc`:
   Change `/PATH/TO/BASE/DIR/` to wherever you cloned this git repo.
   ```
   alias qfprog="python3 /PATH/TO/BASE/DIR/TinyFPGA-Programmer-Application/tinyfpga-programmer-gui.py"
   ```

   ```sh
   source ~/.bashrc
   ```

## Programming
This version of tinyfpga-programmer-gui.py is restricted to CLI mode.  
CLI mode allows you to specify which port to use, and thus works even when the system does not report USB VID and PID.  
This document focuses on CLI mode.

Help is available by running with the --help parameter:

```sh
python3 tinyfpga-programmer-gui --help
```
or, if you have already setup the alias
```sh
qfprog --help
```
This will result in:
```
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
  ```
The programmer allows you to specify various options:
* The *--port port-name* option is used to tell the programmer which serial port the QuickFeather board is connected to. The form of *port-name* varies depending on the system: 
   * COM## on PC/Windows
   * /dev/ttyS## on PC/wsl1/Ubuntu18 (where the ## is the same as the COM## shown by device manager under Windows)
   * /dev/ttyACM# on PC/Ubuntu18
 * The *--m4app app.bin* tells the programmer to program the file *app.bin* as the m4 application -- this is the common case
 * The *--reset* option tells the programm to reset the board, which will result in the bootloader being restarted, and if the user button is not pressed, the bootloader will then laod and start the most recent m4app.
  * Example: *qfprog --port /dev/ttyS8 --m4app output/bin/qf_helloworldsw.bin --reset* will program the m4app with qf_helloworldsw and then run it
 * The *--crc* option simples prints the crc values for each of binaries that are programmed into the flash memory
 * The *--checkrev* option compares the crc for a binary specified as an option to the binary file progammed into the flash
  * Example: *qfprog --port /dev/ttyS8 --m4app output/bin/qf_helloworldsw.bin --checkrev* will compare the crc for file output/bin/qf_helloworldsw.bin with the crc for the binary programmed into the m4app location of the flash memory
* The *--update* option causes the progammer to check the crc of any specified binary against the crc of the binary progammed into the flash, and only programmer the specified binary if it the crc is different

**Danger Zone**
* The *--bootloader boot.bin* option tells the programmer to program the file *boot.bin* as the bootloader application. **If the programming fails for any reason, or the boot.bin file doesn't work as expected the QuickFeather will become non-functional and only recoverable by using J-LINK**
* The *--bootfpga fpga.bin* option tells the programmer to program the file *fpga.bin* as the fpga image for the bootloader. **If the programming fails for any reason, or the fpga.bin file doesn't work as expected the QuickFeather will become non-functional and only recoverable by using J-LINK**
* the *--mfgpkg mfgpkg/* option can be used to update all of the QuickFeather firmware or restore it to the factory delivered state.  The programmer expects the *mfgpkg/* directory will contain qf_bootloader.bin, qf_bootfpga.bin and qf_helloworldsw.bin.  The recommended update method is to use the --update option with the --mfgpkg option


## Flash memory map
The TinyFPGA programmer has a flash memory map for 5 bin files, and corresponding CRC for each of them.
The 5 bin files are:
  * bootloader
  * bootfpga
  * m4app
  * appfpga (for future use)
  * appffe (for future use)
  
The bootloader is loaded by a reset.  It handles either communicating with the TinyFPGA-Programmer to load new bin files into the flash,
or it loads m4 app binary and transfers control to it.  The bootfpga area contains the binary for the fpga image that the bootlaoder uses.
The m4 app image is expected to contain and load any fpga image that it requires.

The flash memory map defined for q-series devices is:

|Item	        |Status	|Start	    |Size	    |End		        |Start	    |Size	    |End|
|-----          |-------|----------:|----------:|------------------:|----------:|----------:|--:|
|bootloader	    |Used	|0x0000_0000|0x0001_0000|0x0000_FFFF		|-   	     |65,536 	|65,536 |
|bootfpga CRC	|Used	|0x0001_0000|          8|	0x0001_0007		|65,536 	 |8 	  |65,544| 
|appfpga CRC	|Future	|0x0001_1000|	          8|	0x0001_1007	|	 69,632 |	      8 |	  69,640 
appffe CRC	    |Future	|0x0001_2000|	          8|	0x0001_2007	|	 73,728 |	      8 |	  73,736 
M4app CRC	    |Used	|0x0001_3000|	          8|	0x0001_3007	|	 77,824 |	      8 |	  77,832 
bootloader CRC	|Used	|0x0001_4000|	          8|	0x0001_4007	|	 81,920 |	      8 |	  81,928 
bootfpga	    |Used	|0x0002_0000|	0x0002_0000|	0x0003_FFFF	|	 131,072 |	 131,072 |	 262,144 
appfpga	        |Future	|0x0004_0000|	0x0002_0000|	0x0005_FFFF	|	 262,144 |	 131,072 |	 393,216 
appffe	        |Future	|0x0006_0000|	0x0002_0000|	0x0007_FFFF	|	 393,216 |	 131,072 |	 524,288 
M4app	        |Used	|0x0008_0000|	0x0006_E000|	0x000E_DFFF	|	 524,288 |	 450,560 |	 974,848 



