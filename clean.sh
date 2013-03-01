find . -type f -name "*.so" -o -name "*.pyc" -o -name "*.pyd" | xargs rm -f
rm -f pyspades/{bytes,common,contained,loaders,mapmaker,packet,vxl,world}.cpp
rm -rf build
rm -rf enet/build
rm -f enet/enet.c
