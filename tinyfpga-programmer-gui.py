#!python3.7
import sys
import os

# need to find the correct location for bundled packages
script_path = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(script_path, 'pkgs'))
sys.path.insert(0, os.path.join(script_path, 'a-series-programmer', 'python'))
sys.path.insert(0, os.path.join(script_path, 'q-series', 'python'))

import serial
import array
import time
#from intelhex import IntelHex
import binascii
from qlcrc import *

import threading
import os
import os.path
import traceback
from serial.tools.list_ports import comports

import argparse

from tinyfpgab import TinyFPGAB
import tinyfpgaa
from tinyfpgaq import TinyFPGAQ
########################################
## Programmer Hardware Adapters
########################################
class ProgrammerHardwareAdapter(object):
    def __init__(self, port):
        self.port = port
        #self.bus, self.portnum = [int(x) for x in self.port[2].split('=')[-1].split('-')]

    @staticmethod
    def canProgram(port):
        pass

    def displayName(self):
        pass

    def checkPortStatus(self):
        pass

    def exitBootloader(self):
        pass

    def reset(self):
        # TODO: for now...let's not bother with resetting the port
        pass
        #try:
        #    import usb
        #    device = usb.core.find(custom_match = lambda d: d.bus == self.bus and d.port_number == self.portnum)
        #    device.reset()
        #except:
        #    traceback.print_exc()
        
class TinyFPGAQSeries(ProgrammerHardwareAdapter):
    def __init__(self, port):
        super(TinyFPGAQSeries, self).__init__(port)

    @staticmethod
    def canProgram(port):
        return "1D50:6130" in port[2] or "1D50:6140" in port[2] or "0000:0000" in port[2]

    def displayName(self):
        if "1D50:6130" in self.port[2]:
            return "%s (QuickFeather)" % self.port[0]

        if "1D50:6140" in self.port[2]:
            return "%s (QuickFeather)" % self.port[0]

    def get_file_extensions(self):
        return ('.hex', '.bin')

    def get_image_info(self, image_index):
        with serial.Serial(self.port[0], 115200, timeout=60, writeTimeout=60) as ser:
            fpga = TinyFPGAQ(ser, progress)

            meta_addr = image_address[image_index][2]
            read_meta = bytearray(fpga.read(meta_addr, 12, False))

            read_image_info = read_meta[-4:]

            return read_image_info

    def set_image_info(self, image_index, image_info, progress, description="", checkrev=False, update=False):
        with serial.Serial(self.port[0], 115200, timeout=60, writeTimeout=60) as ser:
            fpga = TinyFPGAQ(ser, progress)
            #convert image_info to bytearray
            image_info_bytearray = bytearray(image_info)            
            
            # rmw needed, read metadata first
            meta_addr = image_address[image_index][2]
            read_meta = bytearray(fpga.read(meta_addr, 12, False))
            
            # check the last 4 bytes (image_info) in the metadata
            read_image_info = read_meta[-4:]
            
            # if they are already the same as what we want to write, nothing to do
            if(image_info_bytearray == read_image_info):
                print("image_info is already set correctly, not writing again")
            else:
                # set image_info into metadata, replace last 4 bytes with new image_info
                read_meta[-4:] = image_info
                
                # write metadata
                meta_bitstream = bytes(read_meta)
                try:
                    print ("writing new image_info to metadata")
                    fpga.program_bitstream(meta_addr, meta_bitstream, "metadata")
                    #print("Not programming metadata");
                except:
                    program_failure = True
                    traceback.print_exc()


    def reset_meta(self, image_index, progress, description="", checkrev=False, update=False):
        global max_progress

        with serial.Serial(self.port[0], 115200, timeout=60, writeTimeout=60) as ser:
            fpga = TinyFPGAQ(ser, progress)
            crc32 = 0xFFFFFFFF
            meta_array = bytearray(crc32.to_bytes(4,'little'))
            bitstream_size = 0xFFFFFFFF
            meta_array.extend(bitstream_size.to_bytes(4,'little'))

            meta_addr = image_address[image_index][2]
            meta_bitstream = bytes(meta_array)

            try:
                print ("resetting metadata")
                fpga.program_bitstream(meta_addr, meta_bitstream, "metadata")
                #print("Not programming metadata");
            except:
                program_failure = True
                traceback.print_exc()

    def program(self, filename, progress, description="", checkrev=False, update=False):
        global max_progress

        with serial.Serial(self.port[0], 115200, timeout=60, writeTimeout=60) as ser:
            fpga = TinyFPGAQ(ser, progress)

            (addr, bitstream) = fpga.slurp(filename)
            #print("Address = ", hex(addr), len(bitstream))
            #crc32 = binascii.crc32(bitstream, 0xFFFFFFFF)
            #print("Crc32 =", hex(crc32))
            
            qcrc32 = get_crc32_from_string(bitstream);
            #print("QCrc32 =", hex(qcrc32))
            crc32 = qcrc32
            
            meta_array = bytearray(crc32.to_bytes(4,'little'))
            bitstream_size = len(bitstream)
            meta_array.extend(bitstream_size.to_bytes(4,'little'))
            #meta_array.extend(bytes(b"\0"*(4096-8)))
            #print("META = ", bytes(meta_array))

            
            #get the image type selection and look-up the address, size and metadata address
            if image_index == -1:
                index = image_options.index(imagename_sv.get())
            else:
                index = image_index
            addr = image_address[index][0]
            max_size = image_address[index][1]
            meta_addr = image_address[index][2]
            meta_bitstream = bytes(meta_array)
            
            if(bitstream_size > max_size):
                print("Error: The file size", bitstream_size, "exceeds max size", max_size, "for the selected image")
                return
                
            try:
                actual_crc = fpga.read(meta_addr, 8, False)
            except:
                program_failure = True
                traceback.print_exc()
                return()
                
            # If just wants to check the revision, print match/mismatch and return
            if checkrev:
                if meta_bitstream == actual_crc:
                    print("is  up-to-date:", filename);
                    return()
                else:
                    print("not up-to-date:", filename);
                    return()
                    
            # If specified update, then return if CRC matches, otherwise program
            if update and (meta_bitstream == actual_crc):
                print("Skipping programming because CRC matches for ", filename);
                return()
                
            # Need to program
            print(description, filename)
                
            #print("Address = ", hex(addr), hex(max_size), hex(meta_addr))

            max_progress = len(bitstream) * 3 

            try:
                fpga.program_bitstream(addr, bitstream, "binary")
                #print("Not programming ");
            except:
                program_failure = True
                traceback.print_exc()

            #bootloader does not have metatdata
            #if(meta_addr > 0x20000):
            #    return

            try:
                print ("Writing metadata")
                fpga.program_bitstream(meta_addr, meta_bitstream, "metadata")
                #print("Not programming metadata");
            except:
                program_failure = True
                traceback.print_exc()



    def checkPortStatus(self, update_button_state):
        try:
            print (self.port)
            with serial.Serial(self.port[0], 115200, timeout=0.2, writeTimeout=2) as ser:
                fpga = TinyFPGAQ(ser)
                if fpga.is_bootloader_active():
                    com_port_status_sv.set("Connected to QuickFeather. Ready to program.")
                    return True
                else:            
                    com_port_status_sv.set("Unable to communicate with QuickFeather. Reconnect and reset QuickFeather before programming.")
                    return False

        except serial.SerialTimeoutException:
            com_port_status_sv.set("Hmm...try pressing the reset button on QuickFeather again.")
            return False

        except:
            com_port_status_sv.set("Bootloader not active. Press reset button on QuickFeather before programming.")
            return False

    def exitBootloader(self):
        with serial.Serial(self.port[0], 115200, timeout=0.2, writeTimeout=2) as ser:
            try:
                TinyFPGAQ(ser).boot()
                print("boot sent")

            except serial.SerialTimeoutException:
                com_port_status_sv.set("Hmm...try pressing the reset button on QuickFeather again.")
                
    def printCRCs(self):
        with serial.Serial(self.port[0], 115200, timeout=10, writeTimeout=10) as ser:
            fpga = TinyFPGAQ(ser, progress)
            
            crc = fpga.read(image_address[0][2], 8, False)
            print("bootloader:", binascii.hexlify(crc))
            crc = fpga.read(image_address[1][2], 8, False)
            print("boot fpga :", binascii.hexlify(crc))
            crc = fpga.read(image_address[4][2], 8, False)
            print("M4 app    :", binascii.hexlify(crc))
            crc = fpga.read(image_address[2][2], 8, False)
            print("app fpga  :", binascii.hexlify(crc))

        
            

class TinyFPGABSeries(ProgrammerHardwareAdapter):
    def __init__(self, port):
        super(TinyFPGABSeries, self).__init__(port)

    @staticmethod
    def canProgram(port):
        return "1209:2100" in port[2] or "0000:0000" in port[2]

    def displayName(self):
        if "1209:2100" in self.port[2]:
            return "%s (TinyFPGA Bx)" % self.port[0]

        if "0000:0000" in self.port[2]:
            return "%s (Maybe TinyFPGA Bx Prototype)" % self.port[0]

    def get_file_extensions(self):
        return ('.hex', '.bin')

    def program(self, filename, progress):
        global max_progress

        with serial.Serial(self.port[0], 115200, timeout=2, writeTimeout=2) as ser:
            fpga = TinyFPGAB(ser, progress)

            (addr, bitstream) = fpga.slurp(filename)

            max_progress = len(bitstream) * 3 

            try:
                fpga.program_bitstream(addr, bitstream)
            except:
                program_failure = True
                traceback.print_exc()



    def checkPortStatus(self, update_button_state):
        try:
            with serial.Serial(self.port[0], 115200, timeout=0.2, writeTimeout=0.2) as ser:
                fpga = TinyFPGAB(ser)
            
                if fpga.is_bootloader_active():
                    com_port_status_sv.set("Connected to TinyFPGA B2. Ready to program.")
                    return True
                else:            
                    com_port_status_sv.set("Unable to communicate with TinyFPGA. Reconnect and reset TinyFPGA before programming.")
                    return False

        except serial.SerialTimeoutException:
            com_port_status_sv.set("Hmm...try pressing the reset button on TinyFPGA again.")
            return False

        except:
            com_port_status_sv.set("Bootloader not active. Press reset button on TinyFPGA before programming.")
            return False

    def exitBootloader(self):
        with serial.Serial(self.port[0], 10000000, timeout=0.2, writeTimeout=0.2) as ser:
            try:
                TinyFPGAB(ser).boot()

            except serial.SerialTimeoutException:
                com_port_status_sv.set("Hmm...try pressing the reset button on TinyFPGA again.")
            
        

class TinyFPGAASeries(ProgrammerHardwareAdapter):
    def __init__(self, port):
        super(TinyFPGAASeries, self).__init__(port)

    @staticmethod
    def canProgram(port):
        return "1209:2101" in port[2]

    def displayName(self):
        return "%s (TinyFPGA Ax)" % self.port[0]

    def get_file_extensions(self):
        return ('.jed')

    def program(self, filename, progress):
        global max_progress

        with serial.Serial(self.port[0], 12000000, timeout=10, writeTimeout=5) as ser:            
            async_serial = tinyfpgaa.SyncSerial(ser)
            pins = tinyfpgaa.JtagTinyFpgaProgrammer(async_serial)
            jtag = tinyfpgaa.Jtag(pins)
            programmer = tinyfpgaa.JtagCustomProgrammer(jtag)
           
            progress("Parsing JEDEC file")
            jedec_file = tinyfpgaa.JedecFile(open(filename, 'r'))

            max_progress = jedec_file.numRows() * 3

            try:
                programmer.program(jedec_file, progress)

            except:
                program_failure = True
                self.reset()
                traceback.print_exc()

    port_success = False
    def checkPortStatus(self, update_button_state):
        global port_success
        with serial.Serial(self.port[0], 12000000, timeout=.5, writeTimeout=0.1) as ser:
            async_serial = tinyfpgaa.SyncSerial(ser)
            pins = tinyfpgaa.JtagTinyFpgaProgrammer(async_serial)
            jtag = tinyfpgaa.Jtag(pins)
            programmer = tinyfpgaa.JtagCustomProgrammer(jtag)
            port_success = False

            def status_callback(status):
                global port_success
                
                if status == [0x43, 0x80, 0x2B, 0x01]:
                    com_port_status_sv.set("Connected to TinyFPGA A1. Ready to program.")
                    port_success = True

                elif status == [0x43, 0xA0, 0x2B, 0x01]:
                    com_port_status_sv.set("Connected to TinyFPGA A2. Ready to program.")
                    port_success = True

                else:
                    com_port_status_sv.set("Cannot identify FPGA.  Please ensure proper FPGA power and JTAG connection.")
                    port_success = False

            ### read idcode
            programmer.write_ir(8, 0xE0)
            programmer.read_dr(32, status_callback, blocking = True)
            return port_success

    def exitBootloader(self):
        pass


## Global :( variables ##
image_index = -1    # -1 says get from GUI
parser = argparse.ArgumentParser()
# ensure that the mode is always passed in to prevent confusing use cases.
# user may want to change mode from fpga-m4 to m4 but forgets mode
# then BL will still be trying to load fpga
# and more such scenarios
parser.add_argument(
        "--mode",
        action="store",
        nargs="?",
        const="read", # send this if no args to --mode are provided, user wants to read the mode.
        type=str,
        #metavar='ffe-fpga-m4',
        metavar='fpga-m4',
        help='operation mode - m4/fpga/fpga-m4'
    )
parser.add_argument(
        "--m4app",
        type=argparse.FileType('r'),
        metavar='app.bin',
        help='m4 application program'
    )
parser.add_argument(
        "--appfpga",
        type=argparse.FileType('r'),
        metavar='appfpga.bin',
        help='application FPGA binary'
    )
parser.add_argument(
        "--bootloader",
        "--bl",
        type=argparse.FileType('r'),
        metavar='boot.bin',
        help='m4 bootloader program WARNING: do you really need to do this? It is not common, and getting it wrong can make you device non-functional'
    )
parser.add_argument(
        "--bootfpga",
        type=argparse.FileType('r'),
        metavar='fpga.bin',
        help='FPGA image to be used during programming WARNING: do you really need to do this? It is not common, and getting it wrong can make you device non-functional'
    )
parser.add_argument(
        "--reset",
        action="store_true",
        help='reset attached device'
    )
parser.add_argument(
        "--port",
        type=str,
        metavar='/dev/ttySx',
        help='use this port'
    )
parser.add_argument(
        "--crc",
        action="store_true",
        help='print CRCs'
    )
parser.add_argument(
        "--checkrev",
        action="store_true",
        help='check if CRC matches (flash is up-to-date)'
    )
parser.add_argument(
        "--update",
        action="store_true",
        help='program flash only if CRC mismatch (not up-to-date)'
    )
parser.add_argument(
        "--mfgpkg",
        type=str,
        metavar='qf_mfgpkg/',
        help='directory containing all necessary binaries'
    )
args = parser.parse_args()

if args.mode or args.m4app or args.appfpga or args.bootloader or args.bootfpga or args.reset or args.crc or args.mfgpkg or args.checkrev or --args.update:
    ################################################################################
    ################################################################################
    ##
    ## TinyFPGA Command Line Mode
    ##
    ################################################################################
    ################################################################################
    print ("CLI mode")
    
    ########################################
    ## Select Serial Port
    ########################################
    adapters = [TinyFPGABSeries, TinyFPGAASeries, TinyFPGAQSeries]
    def getProgrammerHardwareAdapter(port):
        for adapter in adapters:
            if adapter.canProgram(port):
                return adapter(port)

        return None
    
    if args.port:
        displayname =  "%s (QuickFeather)" % args.port
        for port in comports():
            if port[0] == args.port:
                tinyfpga_adapters = {displayname : TinyFPGAQSeries(port)}
    else:
        tinyfpga_adapters = dict((adapter.displayName(), adapter) for adapter in [getProgrammerHardwareAdapter(port) for port in comports()] if adapter is not None)
    
    try: tinyfpga_adapters
    except NameError: tinyfpga_adapters = None
    
    if tinyfpga_adapters is None:
        print("Did not find port -- exiting");
        exit(0);
    
    tinyfpga_ports = [key for key, value in iter(tinyfpga_adapters.items())]
    print("ports = ", tinyfpga_ports, len(tinyfpga_ports))
    
    if len(tinyfpga_ports) > 1:
        # ToDo allow user to specify which COM port
        print ("More than one QuickFeather found ... stopping")
        exit()
    elif len(tinyfpga_ports) < 1:
        print ("Did not find a QuickFeather in programming mode.  Press reset and then user button ... stopping")
        exit()


    ## Simple routine to show progress
    def progress(v): 
        print("", end="", flush=True)

    ## Copy of array from GUI -- really should use the same one
    image_options = [
    "Bootloader - 0x000000 to 0x010000",
    "USB FPGA   - 0x020000 to 0x03FFFF",
    "App FPGA   - 0x040000 to 0x05FFFF",
    "App FFE    - 0x060000 to 0x07FFFF",
    "M4 App     - 0x080000 to 0x0FFFFF"
    ]
    image_address = [
        #[address, size , metadata address ] 0xFFFFFF is invalid
        [0x000000, 0x010000, 0x01F000], #"Bootloader - 0x000000 to 0x010000",
        [0x020000, 0x020000, 0x010000], #"USB FPGA   - 0x020000 to 0x03FFFF",
        [0x040000, 0x020000, 0x011000], #"App FPGA   - 0x040000 to 0x05FFFF",
        [0x060000, 0x020000, 0x012000], #"App FFE    - 0x060000 to 0x07FFFF",
        [0x080000, 0x06E000, 0x013000], #"M4 App     - 0x080000 to 0x0FFFFF"
    ]
    IMAGE_INFO_ACTIVE_TRUE = 0x03
    IMAGE_INFO_ACTIVE_FALSE = 0xFF

    IMAGE_INFO_TYPE_M4 = 0x01
    IMAGE_INFO_TYPE_FFE = 0x02
    IMAGE_INFO_TYPE_FPGA = 0x03
    IMAGE_INFO_TYPE_FS = 0x04

    IMAGE_INFO_SUBTYPE_BOOT = 0x01
    IMAGE_INFO_SUBTYPE_APP = 0x02
    IMAGE_INFO_SUBTYPE_OTA = 0x03    
    IMAGE_INFO_SUBTYPE_FS_FAT = 0x20    
    image_info = [
         #[active, type, subtype, reserved] 0xFF is invalid
        [IMAGE_INFO_ACTIVE_TRUE,  IMAGE_INFO_TYPE_M4,   IMAGE_INFO_SUBTYPE_BOOT,    0xFF],
        [IMAGE_INFO_ACTIVE_TRUE,  IMAGE_INFO_TYPE_FPGA, IMAGE_INFO_SUBTYPE_BOOT,    0xFF],
        [IMAGE_INFO_ACTIVE_FALSE, IMAGE_INFO_TYPE_FPGA, IMAGE_INFO_SUBTYPE_APP,     0xFF],
        [IMAGE_INFO_ACTIVE_FALSE, IMAGE_INFO_TYPE_FFE,  IMAGE_INFO_SUBTYPE_APP,     0xFF],
        [IMAGE_INFO_ACTIVE_FALSE, IMAGE_INFO_TYPE_M4,   IMAGE_INFO_SUBTYPE_APP,     0xFF]
    ]

    ########################################
    ## If specified mfgpkg, populate names
    ########################################
    if args.mfgpkg:
        bootloadername = args.mfgpkg + "/qf_bootloader.bin"
        args.bootloader = True
        bootfpganame = args.mfgpkg + "/qf_bootfpga.bin"
        args.bootfpga = True
        m4appname = args.mfgpkg + "/qf_helloworldsw.bin"
        args.m4app = True
        appfpganame = ""
        args.appfpga = False
    else:
        if args.bootloader:
            bootloadername = args.bootloader.name
        if args.bootfpga:
            bootfpganame = args.bootfpga.name
        if args.m4app:
            m4appname = args.m4app.name
        if args.appfpga:
            appfpganame = args.appfpga.name
        
    ########################################
    ## Set up adapter
    ########################################
    print("Using port ", tinyfpga_ports[0])
    adapter = tinyfpga_adapters[tinyfpga_ports[0]]
    
    ########################################
    ## See if wants to print CRCs
    ########################################
    if args.crc:
        adapter = tinyfpga_adapters[tinyfpga_ports[0]]
        adapter.printCRCs()

    ########################################
    ## See if wants to program appfpga
    ########################################
    if args.appfpga:
        # pre-check : ensure user specifies mode
        if (not args.mode):
            print("error! please specify a mode with one of \"--mode [m4/fpga/fpga-m4]\"")
            exit()
        image_index = 2 # point to App FPGA image
        #print("Programming m4 application with ", m4appname)
        adapter.program(appfpganame, progress, "Programming application FPGA with ", args.checkrev, args.update)

    ########################################
    ## See if wants to program m4app
    ########################################
    if args.m4app:
        # pre-check : ensure user specifies mode
        if (not args.mode):
            print("error! please specify a mode with one of \"--mode [m4/fpga/fpga-m4]\"")
            exit()

        image_index = 4 # point to M4 App image
        #print("Programming m4 application with ", m4appname)
        adapter.program(m4appname, progress, "Programming m4 application with ", args.checkrev, args.update)

    ########################################
    ## See if wants to program bootloader
    ########################################
    if args.bootloader:
        # while flashing bootloader, mode is not necessary.
        # either it was already set previously, or when user flashes m4/fpga it will be set.
        # if mode is specified here, it will be set, if not, don't bother the user.

        image_index = 0 # point to bootloader image
        #print("Programming bootloader with ", bootloadername)
        adapter.program(bootloadername, progress, "Programming bootloader with ", args.checkrev, args.update)
    ########################################
    ## See if wants to program FPGA image used during programming
    ########################################
    if args.bootfpga:
        image_index = 1 # point to FPGA image used during programming
        #print("Programming FPGA image used during programming ", bootfpganame)
        adapter.program(bootfpganame, progress, "Programming FPGA image used during programming ", args.checkrev, args.update)

    #################################################################
    ## See if specified operation mode : AFTER all images are flashed
    #################################################################
    if args.mode:
        # if only --mode is passed in, user wants to read the mode
        if(args.mode == "read"): # due to const, this is what we get here.
            mode_list = []
            if(adapter.get_image_info(2)[0] == IMAGE_INFO_ACTIVE_TRUE):
                mode_list.append("fpga")
            #if(adapter.get_image_info(3)[0] == IMAGE_INFO_ACTIVE_TRUE):
            #    mode_list.append("ffe")
            if(adapter.get_image_info(4)[0] == IMAGE_INFO_ACTIVE_TRUE):
                mode_list.append("m4")
            mode_list.sort()
            mode_str = "[" + "-".join(mode_list) + "]"            
            print("mode:", mode_str)
        # else, mode with arguments is passed in, user wants to set the mode
        else:
            # --mode m4 or --mode m4-fpga or --mode fpga-m4 or --mode fpga
            # or --mode m4-ffe or --mode ffe-m4 ... and so on
            mode_list = args.mode.split("-")    

            # check if params passed in are all unique? use set()
            mode_set = set(mode_list)
            if(len(mode_set) != len(mode_list)):
                print("error! repetition in mode argument!")
                exit()

            # check if all the components of the mode string are correct:
            # check we have a subset of recognized components only.
            # reference set is set of components we support : m4, fpga, ffe*
            #ref_set = set(["m4", "fpga", "ffe"])
            ref_set = set(["m4", "fpga"])
            if(not set(mode_set).issubset(ref_set)):
                print("error! unrecognized or incomplete mode argument!")
                exit()

            mode_str = "[" + "-".join(mode_set) + "]"
            
            print("operating mode :", mode_str)

            # according to the mode selected, set the "active" flag in the corresponding images:
            image_index_to_set_image_info = -1
            image_info_for_image = None

            # App FPGA image:
            image_index_to_set_image_info = 2
            image_info_for_image = image_info[image_index_to_set_image_info].copy()
            if("fpga" in mode_set):
                print("setting appfpga active")
                image_info_for_image[0] = IMAGE_INFO_ACTIVE_TRUE
            else:
                print("setting appfpga inactive")
                image_info_for_image[0] = IMAGE_INFO_ACTIVE_FALSE
            #print(image_info_for_image)
            adapter.set_image_info(image_index_to_set_image_info, image_info_for_image, progress, "setting image_info for App FPGA", args.checkrev, args.update)

            # App FFE Image:
            #image_index_to_set_image_info = 3
            #image_info_for_image = image_info[image_index_to_set_image_info].copy()
            #if("ffe" in mode_set):
            #    print("setting appffe active")
            #    image_info_for_image[0] = IMAGE_INFO_ACTIVE_TRUE
            #else:
            #    print("setting appffe inactive")
            #    image_info_for_image[0] = IMAGE_INFO_ACTIVE_FALSE
            ##print(image_info_for_image)
            #adapter.set_image_info(image_index_to_set_image_info, image_info_for_image, progress, "setting image_info for App FFE", args.checkrev, args.update)

            # M4 App Image:
            image_index_to_set_image_info = 4
            image_info_for_image = image_info[image_index_to_set_image_info].copy()
            if("m4" in mode_set):
                print("setting m4app active")
                image_info_for_image[0] = IMAGE_INFO_ACTIVE_TRUE
            else:
                print("setting m4app inactive")
                image_info_for_image[0] = IMAGE_INFO_ACTIVE_FALSE
            #print(image_info_for_image)
            adapter.set_image_info(image_index_to_set_image_info, image_info_for_image, progress, "setting image_info for M4 App", args.checkrev, args.update)


    ########################################
    ##            MUST BE LAST IN SEQUENCE
    ## See if wants to reset the attached board
    ########################################
    if args.reset:
        print("Reset the device")
        adapter.exitBootloader()

else:
    ################################################################################
    ################################################################################
    ##
    ## TinyFPGA Programmer GUI
    ##
    ################################################################################
    ################################################################################
    print("GUI mode disabled: use --help to get help on CLI mode")
    exit()
    from tkinter import *
    from tkinter.ttk import *
    import tkinter.filedialog as tkFileDialog

    communication_lock = threading.Lock()

    r = Tk()
    r.title("TinyFPGA Flash Programmer")
    r.resizable(width=False, height=False)

    program_in_progress = False
    program_failure = False

    program_fpga_b = Button(r, text="Program Flash")
    program_progress_pb = Progressbar(r, orient="horizontal", length=400, mode="determinate")

    boot_fpga_b = Button(r, text="Exit Flash Programmer")

    program_status_sv = StringVar(r)

    serial_port_ready = False
    bitstream_file_ready = False
    file_mtime = 0

    def update_button_state(new_serial_port_ready = None):
        global serial_port_ready
        global bitstream_file_ready

        if new_serial_port_ready is not None:
            serial_port_ready = new_serial_port_ready

        if serial_port_ready and not program_in_progress:
            boot_fpga_b.config(state=NORMAL)

            if bitstream_file_ready:
                program_fpga_b.config(state=NORMAL)
            else:
                program_fpga_b.config(state=DISABLED)

        else:
            boot_fpga_b.config(state=DISABLED)
            program_fpga_b.config(state=DISABLED)


    ########################################
    ## Select Serial Port
    ########################################

    adapters = [TinyFPGABSeries, TinyFPGAASeries, TinyFPGAQSeries]

    def getProgrammerHardwareAdapter(port):
        for adapter in adapters:
            if adapter.canProgram(port):
                return adapter(port)

        return None


    com_port_status_sv = StringVar(r)
    com_port_status_l = Label(r, textvariable=com_port_status_sv)
    com_port_status_l.grid(column=1, row=0, sticky=W+E, padx=10, pady=8)
    com_port_sv = StringVar(r)
    com_port_sv.set("")
    select_port_om = OptionMenu(r, com_port_sv, ())
    select_port_om.grid(column=0, row=0, sticky=W+E, padx=10, pady=8)
    tinyfpga_adapters = dict()

    tinyfpga_ports = []
    def update_serial_port_list_task():
        global tinyfpga_ports
        global program_in_progress
        global tinyfpga_adapters
        
        if not program_in_progress:
            new_tinyfpga_adapters = dict((adapter.displayName(), adapter) for adapter in [getProgrammerHardwareAdapter(port) for port in comports()] if adapter is not None)
            #new_tinyfpga_ports = [key for key, value in new_tinyfpga_adapters.iteritems()]
            new_tinyfpga_ports = [key for key, value in iter(new_tinyfpga_adapters.items())]
            
            if new_tinyfpga_ports != tinyfpga_ports:
                if com_port_sv.get() == "" and len(new_tinyfpga_ports) > 0:
                    com_port_sv.set(new_tinyfpga_ports[0])
                    update_button_state(new_serial_port_ready = True)

                update_button_state(new_serial_port_ready = com_port_sv.get() in new_tinyfpga_ports)

                menu = select_port_om["menu"]
                menu.delete(0, "end")
                for string in new_tinyfpga_ports:
                    menu.add_command(
                        label=string, 
                        command=lambda value=string: com_port_sv.set(value))
                tinyfpga_ports = new_tinyfpga_ports
                tinyfpga_adapters = new_tinyfpga_adapters

        r.after(100, update_serial_port_list_task)

    update_serial_port_list_task()

    def check_port_status_task():
        global adapter
        try:
            adapter = tinyfpga_adapters[com_port_sv.get()]
            return adapter.checkPortStatus(update_button_state)

        except:
            com_port_status_sv.set("Unable to communicate with TinyFPGA.  Reset your TinyFPGA and check your connections.")
            traceback.print_exc()
            try:
                adapter.reset()
            except:
                traceback.print_exc()
            return False

    ########################################
    ## Select Image Type
    ########################################

    image_options = [
    "Bootloader - 0x000000 to 0x010000",
    "USB FPGA   - 0x020000 to 0x03FFFF",
    "App FPGA   - 0x040000 to 0x05FFFF",
    "App FFE   - 0x060000 to 0x07FFFF",
    "M4 App     - 0x080000 to 0x0FFFFF"
    ]
    image_address = [
        #[address, size , metadata address ] 0xFFFFFF is invalid
        [0x000000, 0x010000, 0xFFFFFF], #"Bootloader - 0x000000 to 0x010000",
        [0x020000, 0x020000, 0x010000], #"USB FPGA   - 0x020000 to 0x03FFFF",
        [0x040000, 0x020000, 0x011000], #"App FPGA   - 0x040000 to 0x05FFFF",
        [0x060000, 0x020000, 0x012000], #"App FFE    - 0x060000 to 0x07FFFF",
        [0x080000, 0x06E000, 0x013000], #"M4 App     - 0x080000 to 0x0FFFFF"
    ]

    imagename_sv = StringVar(r)
    imagename_sv.set(image_options[4])

    def select_image_type_cmd(value):
        imagename_sv.set(value)
        #index = image_options.index(value)
        #print("image =", value, index)

    select_image_b = Button(r, text="Select Image Type" )
    select_image_b.grid(column=0, row=1, sticky=W+E, padx=10, pady=8)
    imagename_om = OptionMenu(r, imagename_sv, image_options[4], *image_options, command=select_image_type_cmd)
    imagename_om.config(state="active")
    imagename_om["menu"].config(bg="white")
    #imagename_om["menu"]["highlightthickness"]=10
    imagename_om.grid(column=1, row=1, sticky=W+E, padx=10, pady=8)


    ########################################
    ## Select File
    ########################################

    filename_sv = StringVar(r)

    def select_bitstream_file_cmd():
        file_extensions = ('FPGA Bitstream Files', ('.hex', '.bin', '.jed'))

        try:
            adapter = tinyfpga_adapters[com_port_sv.get()]
            file_extensions = adapter.get_file_extensions()
        except:
            pass

        filename = tkFileDialog.askopenfilename(
            title = "Select file", 
            filetypes = [
                ('FPGA Bitstream Files', file_extensions), 
                ('all files', '.*')
            ]
        )

        filename_sv.set(filename)

    select_file_b = Button(r, text="Select File", command=select_bitstream_file_cmd)
    #select_file_b.grid(column=0, row=1, sticky=W+E, padx=10, pady=8)
    select_file_b.grid(column=0, row=2, sticky=W+E, padx=10, pady=8)
    filename_e = Entry(r)
    filename_e.config(textvariable=filename_sv)
    #filename_e.grid(column=1, row=1, sticky=W+E, padx=10, pady=8)
    filename_e.grid(column=1, row=2, sticky=W+E, padx=10, pady=8)

    def check_bitstream_file_status_cmd(): 
        global bitstream_file_ready
        global file_mtime

        if os.path.isfile(filename_sv.get()):
            new_file_mtime = os.stat(filename_sv.get()).st_mtime

            bitstream_file_ready = True
            update_button_state()

            if new_file_mtime > file_mtime:
                program_status_sv.set("Bitstream file updated.")
            
            file_mtime = new_file_mtime

        else:
            if bitstream_file_ready:
                program_status_sv.set("Bitstream file no longer exists.")

            bitstream_file_ready = False
            update_button_state()

    def check_bitstream_file_status_task():
        check_bitstream_file_status_cmd()
        r.after(1000, check_bitstream_file_status_task)

    check_bitstream_file_status_task()

    def check_bitstream_file_status_cb(*args):
        global file_mtime
        file_mtime = 0
        check_bitstream_file_status_cmd()

    filename_sv.trace("w", check_bitstream_file_status_cb)



    ########################################
    ## Program FPGA
    ########################################

    program_status_l = Label(r, textvariable=program_status_sv)
    #program_status_l.grid(column=1, row=3, sticky=W+E, padx=10, pady=8)
    program_status_l.grid(column=1, row=4, sticky=W+E, padx=10, pady=8)

    #program_progress_pb.grid(column=1, row=2, sticky=W+E, padx=10, pady=8)
    program_progress_pb.grid(column=1, row=3, sticky=W+E, padx=10, pady=8)

    def program_fpga_thread():
        with communication_lock:
            global program_failure
            global program_in_progress
            program_failure = False

            try:
                global current_progress
                global max_progress
                global progress_lock
                with progress_lock:
                    current_progress = 0

                def progress(v): 
                    global progress_lock
                    with progress_lock:
                        #if isinstance(v, int) or isinstance(v, long):
                        if isinstance(v, int):
                            global current_progress
                            current_progress += v
                        elif isinstance(v, str):
                            program_status_sv.set(v)

                adapter = tinyfpga_adapters[com_port_sv.get()]
                adapter.program(filename_sv.get(), progress)


            except:
                program_failure = True
                traceback.print_exc()

            finally:
                program_in_progress = False
                pass


    current_progress = 0
    max_progress = 0
    progress_lock = threading.Lock()

    def update_progress_task():
        global current_progress
        global max_progress
        global progress_lock

        if progress_lock.acquire(False):
            try:
                #if isinstance(current_progress, (int, long)):
                if isinstance(current_progress, (int, int)):
                    program_progress_pb["value"] = current_progress
                program_progress_pb["maximum"] = max_progress
            except:
                traceback.print_exc()
            finally:
                progress_lock.release()

        r.after(100, update_progress_task)

    update_progress_task()

    def program_fpga_cmd():
        if check_port_status_task():
            global program_in_progress
            program_in_progress = True
            update_button_state()
            t = threading.Thread(target=program_fpga_thread)
            t.start()

    program_fpga_b.configure(command=program_fpga_cmd)
    #program_fpga_b.grid(column=0, row=2, sticky=W+E, padx=10, pady=8)
    program_fpga_b.grid(column=0, row=3, sticky=W+E, padx=10, pady=8)


    ########################################
    ## Boot FPGA
    ########################################

    def boot_cmd():
        adapter = tinyfpga_adapters[com_port_sv.get()]
        adapter.exitBootloader()
        r.destroy()

    def boot_and_exit():
        boot_cmd()

    r.protocol("WM_DELETE_WINDOW", boot_and_exit)

    boot_fpga_b.configure(command=boot_cmd)
    #boot_fpga_b.grid(column=0, row=3, sticky=W+E, padx=10, pady=8)
    boot_fpga_b.grid(column=0, row=4, sticky=W+E, padx=10, pady=8)

    # make sure we can't get resized too small
    r.update()
    r.minsize(r.winfo_width(), r.winfo_height())

    # start the gui
    r.mainloop()
