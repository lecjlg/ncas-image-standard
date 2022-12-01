#! /usr/bin/python3

import sys, datetime, os, errno
from dateutil.parser import *


import module_exiftool_python3
handler = module_exiftool_python3.Handler()
template_id = handler.load_a_template("/opt/scripts/tag_photos/iceland_template.yaml")

handler.set_option("allow_tag_overwrites", True)
handler.set_option("verbosity_level" , 2)

files = sys.argv[1]
for f in files:
    print ("files")
    #exit_code = handler.embed_from_template(template_id,{},"files")
#exit_code = handler.embed_from_template(template_id,{},"/data/ncas-cam-3/images/20221130/10/20221130105300-ncas-cam-3.jpg")

