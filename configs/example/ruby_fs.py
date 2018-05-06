
#
# Full system configuraiton for ruby
#

import optparse
import sys

import m5
from m5.defines import buildEnv
from m5.objects import *
from m5.util import addToPath, fatal

addToPath('../common')
addToPath('../ruby')
addToPath('../topologies')

import Ruby

from FSConfig import *
from SysPaths import *
from Benchmarks import *
import Simulation
import CacheConfig
import MemConfig
from Caches import *
import Options

parser = optparse.OptionParser()
Options.addCommonOptions(parser)
Options.addFSOptions(parser)

# Add the ruby specific and protocol specific options
if '--ruby' in sys.argv:
    Ruby.define_options(parser)
else:
    print "Error: This config only support ruby fs config"
    sys.exit(1)

clusters=[]

(options, args) = parser.parse_args()
options.ruby = True

if args:
    print "Error: script doesn't take any positional arguments"
    sys.exit(1)

# system under test can be any CPU
(CPUClass, test_mem_mode, FutureClass) = Simulation.setCPUClass(options)

# Match the memories with the CPUs, based on the options for the test system
TestMemClass = Simulation.setMemClass(options)

if options.benchmark:
    try:
        bm = Benchmarks[options.benchmark]
    except KeyError:
        print "Error benchmark %s has not been defined." % options.benchmark
        print "Valid benchmarks are: %s" % DefinedBenchmarks
        sys.exit(1)
else:
    bm = [SysConfig(disk=options.disk_image, mem=options.mem_size)]

# Check for timing mode because ruby does not support atomic accesses
if not (options.cpu_type == "detailed" or options.cpu_type == "timing"):
    print >> sys.stderr, "Ruby requires TimingSimpleCPU or O3CPU!!"
    sys.exit(1)

def cmd_line_template():
    if options.command_line and options.command_line_file:
        print "Error: --command-line and --command-line-file are " \
              "mutually exclusive"
        sys.exit(1)
    if options.command_line:
        return options.command_line
    if options.command_line_file:
        return open(options.command_line_file).read().strip()
    return None

for cluster in xrange(2):
    if buildEnv['TARGET_ISA'] == "alpha":
        cmdline = cmd_line_template()
        #system = makeLinuxAlphaRubySystem(test_mem_mode, bm[0])
        clusters.append(makeLinuxAlphaSystem(test_mem_mode, bm[0], options.ruby, cmdline=cmdline))
        Simulation.setWorkCountOptions(clusters[cluster], options)
    elif buildEnv['TARGET_ISA'] == "x86":
        cmdline = cmd_line_template()
        #system = makeLinuxX86System(test_mem_mode, options.num_cpus, bm[0], True)
        clusters.append(makeLinuxX86System(test_mem_mode, options.num_cpus, bm[0], options.ruby, cmdline=cmdline))
        Simulation.setWorkCountOptions(clusters[cluster], options)
    else:
        fatal("incapable of building non-alpha or non-x86 full system!")

# Command line
clusters[0].boot_osflags = 'earlyprintk=ttyS0 console=ttyS0 lpj=7999923 ' + \
                           'root=/dev/hda1'
#clusters[0].kernel = binary('x86_64-vmlinux-2.6.28.4-smp')

clusters[0].cache_line_size = options.cacheline_size
clusters[1].cache_line_size = options.cacheline_size


# Create a top-level voltage domain and clock domain
clusters[0].voltage_domain = VoltageDomain(voltage = options.sys_voltage)
clusters[1].voltage_domain = VoltageDomain(voltage = options.sys_voltage)

clusters[0].clk_domain = SrcClockDomain(clock = options.sys_clock,
                                   voltage_domain = clusters[0].voltage_domain)
clusters[1].clk_domain = SrcClockDomain(clock = options.sys_clock,
                                   voltage_domain = clusters[1].voltage_domain)
# Create a CPU voltage domain
clusters[0].cpu_voltage_domain = VoltageDomain()
clusters[1].cpu_voltage_domain = VoltageDomain()

# Create a source clock for the CPUs and set the clock period
clusters[0].cpu_clk_domain = SrcClockDomain(clock = options.cpu_clock,
                                       voltage_domain =
                                       clusters[0].cpu_voltage_domain)
clusters[1].cpu_clk_domain = SrcClockDomain(clock = options.cpu_clock,
                                       voltage_domain =
                                       clusters[1].cpu_voltage_domain)

if options.kernel is not None:
    clusters[0].kernel = binary(options.kernel)

if options.script is not None:
    clusters[0].readfile = options.script

clusters[0].cpu = [CPUClass(cpu_id=i) for i in xrange(options.num_cpus)]
clusters[1].cpu = [CPUClass(cpu_id=i) for i in xrange(options.num_cpus)]
# Create a source clock for the CPUs and set the clock period
clusters[0].cpu_clk_domain = SrcClockDomain(clock = options.cpu_clock,
                                       voltage_domain = clusters[0].voltage_domain)
clusters[1].cpu_clk_domain = SrcClockDomain(clock = options.cpu_clock,
                                       voltage_domain = clusters[1].voltage_domain)

rubysystem0 = Ruby.create_system(options, True, clusters[0], clusters[0].iobus, clusters[0]._dma_ports)
rubysystem1 = Ruby.create_system(options, True, clusters[1], clusters[1].iobus, clusters[1]._dma_ports)

# Create a seperate clock domain for Ruby
clusters[0].ruby.clk_domain = SrcClockDomain(clock = options.ruby_clock,
                                        voltage_domain = clusters[0].voltage_domain)
clusters[1].ruby.clk_domain = SrcClockDomain(clock = options.ruby_clock,
                                        voltage_domain = clusters[1].voltage_domain)

clusters[0].iobus.master = clusters[0].ruby._io_port.slave
clusters[1].iobus.master = clusters[1].ruby._io_port.slave

for (i, cpu) in enumerate(clusters[0].cpu):
    #
    # Tie the cpu ports to the correct ruby system ports
    #
    cpu.clk_domain = clusters[0].cpu_clk_domain
    cpu.createThreads()
    cpu.createInterruptController()

    cpu.icache_port =  clusters[0].ruby._cpu_ports[i].slave
    cpu.dcache_port =  clusters[0].ruby._cpu_ports[i].slave

    if buildEnv['TARGET_ISA'] == "x86":
        cpu.itb.walker.port = clusters[0].ruby._cpu_ports[i].slave
        cpu.dtb.walker.port = clusters[0].ruby._cpu_ports[i].slave

        cpu.interrupts.pio = clusters[0].ruby._cpu_ports[i].master
        cpu.interrupts.int_master = clusters[0].ruby._cpu_ports[i].slave
        cpu.interrupts.int_slave = clusters[0].ruby._cpu_ports[i].master

    #clusters[0].ruby._cpu_ports[i].access_phys_mem = True

for (i, cpu) in enumerate(clusters[1].cpu):
    #
    # Tie the cpu ports to the correct ruby system ports
    #
    cpu.clk_domain = clusters[1].cpu_clk_domain
    cpu.createThreads()
    cpu.createInterruptController()

    cpu.icache_port =  clusters[1].ruby._cpu_ports[i].slave
    cpu.dcache_port =  clusters[1].ruby._cpu_ports[i].slave

    if buildEnv['TARGET_ISA'] == "x86":
        cpu.itb.walker.port = clusters[1].ruby._cpu_ports[i].slave
        cpu.dtb.walker.port = clusters[1].ruby._cpu_ports[i].slave

        cpu.interrupts.pio = clusters[1].ruby._cpu_ports[i].master
        cpu.interrupts.int_master = clusters[1].ruby._cpu_ports[i].slave
        cpu.interrupts.int_slave = clusters[1].ruby._cpu_ports[i].master

    #clusters[1].ruby._cpu_ports[i].access_phys_mem = True

# Create the appropriate memory controllers and connect them to the
# PIO bus
#clusters[0].mem_ctrls = [TestMemClass(range = r) for r in clusters[0].mem_ranges]
#clusters[1].mem_ctrls = [TestMemClass(range = r) for r in clusters[1].mem_ranges]
#for i in xrange(len(clusters[0].mem_ctrls)):
#    clusters[0].mem_ctrls[i].port = clusters[0].iobus.master
#for i in xrange(len(clusters[1].mem_ctrls)):
#    clusters[1].mem_ctrls[i].port = clusters[1].iobus.master
#clusters[1].membus.master = clusters[1].membus.master[0]


root = Root(full_system = True, system = clusters[0])
Simulation.run(options, root, clusters, FutureClass)


