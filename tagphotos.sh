#!/bin/bash

find /data/ncas-cam-3/images/20221130/10 -type f | xargs -0 /opt/scripts/tag_photos/writeinfo.py
