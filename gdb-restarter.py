import os
import sys
import gdb
from datetime import datetime
import uuid

def stop_event_cb(event):
    time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f")
    crashname = time + "_" + uuid.uuid4().hex
    corefilename = crashname + ".core"
    logfilename = crashname + ".log"
    gdb.execute(f"generate-core-file {corefilename}")
    gdb.execute(f"set logging file {logfilename}")
    gdb.execute("set logging on")
    gdb.execute("p $_siginfo")
    gdb.execute("bt")
    gdb.execute("maintenance info sections")
    gdb.execute("info proc all")
    gdb.execute("set logging off")
    gdb.execute("kill")
    gdb.execute("run")

gdb.events.stop.connect(stop_event_cb)
gdb.execute("set pagination off")
gdb.execute("set confirm off")
gdb.execute("run")
