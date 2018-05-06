#!/bin/bash
export M5_PATH=/home/zhangqianlong/MyPHD/gem5_ccnuma/system/alpha
#./build/ALPHA_MOESI_CMP_directory/gem5.opt configs/example/fs.py -n 4 --l1i_size=32kB --l1d_size=32kB --l2_size=16MB --num-l2caches=4 --ruby --topology=Mesh --cpu-type=timing --mesh-rows=2 --num-dirs=4 --garnet-network=flexible --kernel=vmlinux_2.6.27-gcc_4.3.4 --disk=linux-parsec-2-1-m5-with-test-inputs.img
./build/ALPHA_MOESI_CMP_directory/gem5.opt configs/example/fs.py -n 1 --l1i_size=32kB --l1d_size=32kB --l2_size=16MB --num-l2caches=1 --ruby --topology=Mesh --cpu-type=timing --mesh-rows=1 --num-dirs=1 --garnet-network=flexible --kernel=vmlinux_2.6.27-gcc_4.3.4 --disk=linux-parsec-2-1-m5-with-test-inputs.img
