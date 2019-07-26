#! /bin/sh

sudo strace -p 1 &
sudo kill -9 1
