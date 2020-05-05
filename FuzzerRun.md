# Fuzzing Live555MediaServer

## Building Live555MediaServer with ASAN
* The following was performed on an Ubuntu 18.04 host
* Install gcc, g++, libssl-dev, make
* Get latest source code for live555
  * wget http://www.live555.com/liveMedia/public/live555-latest.tar.gz
* The code is extracted to the live/ directory where the config files live
  * Create a new config file config.fuzz.  The below file contents were based off of the existing config.linux with a few modifications to add ASAN and debugging symbols:

```
COMPILE_OPTS =          $(INCLUDES) -I/usr/local/include -I. -O2 -DSOCKLEN_T=socklen_t -D_LARGEFILE_SOURCE=1 -D_FILE_OFFSET_BITS=64 -fsanitize=address -g3
C =                     c
C_COMPILER =            gcc
C_FLAGS =               $(COMPILE_OPTS) $(CPPFLAGS) $(CFLAGS)
CPP =                   cpp
CPLUSPLUS_COMPILER =    g++
CPLUSPLUS_FLAGS =       $(COMPILE_OPTS) -Wall -DBSD=1 $(CPPFLAGS) $(CXXFLAGS)
OBJ =                   o
LINK =                  g++ -o
LINK_OPTS =             -L. $(LDFLAGS) -fsanitize=address
CONSOLE_LINK_OPTS =     $(LINK_OPTS)
LIBRARY_LINK =          ar cr 
LIBRARY_LINK_OPTS =
LIB_SUFFIX =                    a
LIBS_FOR_CONSOLE_APPLICATION = -lssl -lcrypto
LIBS_FOR_GUI_APPLICATION =
EXE =
```

* Run the following commands to build:
```
./genMakeFiles fuzz
make
```
* The live555MediaServer binary will be at mediaServer/live555MediaServer

### Fuzzing
To setup a basic fuzz run, the server can be run in the following manner:
```
while true; do ./live555MediaServer; sleep 65; done;
```
Note: For this basic example case time optimization, parallelism, and adjusting the code to use SO_REUSEADDR via setsockopt(2) are not considered.

After the process crashes, the connection will be left in state TIME_WAIT, which times out after 60 seconds.  If the process is restarted before the connection times out, the server will not be able to bind to the listening port.
* Note: Running as a regular user will default to port 8554 rather than 554
Then start the fuzzer:
```
python3 RTSPhuzz.py --host target.server.host --port 554 --path test/media/file.mp3
```


### Modifiying RTSPServer.cpp to Create a Crash Test Case
We can create a contrived crash case to ensure the fuzzer is exercising the protocol and that the server target is setup correctly to capture crashes for root cause analysis.

To do so first we'll explore the file live/liveMedia/RTSPServer.cpp.  In this file on line 406 there is a function handeCmd_bad() that handles bad requests.  Inserting the following code will cause a crash whenever a bad request is issued.
```
  int a = 1;
  int buf[10];

  for (int i = 0; i <= 15; i++) {
          buf[i] = 7;
  }
```

To rebuild the live555MediaServer binary, from the live directory run:
```
make clean
./genMakefiles fuzz
make
```
The following python script will issue a bad request causing a crash:
```
import socket
s = socket.socket()
port = 8554                   # set port properly for your setup
host = '<IP-ADDRESS-HERE>'    # insert IP for your setup
s.connect((host, port))
s.send("OPTIONS:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:7:777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777777:7:7:7:777777777777777777777 RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: fuzz\r\n\r\n")
print(s.recv(1024))
s.close()
```

This will result in a crash showing address sanitizier information on where the crash occured.  Pointing the fuzzer at the server compiled with the bad code also produces a crash almost immediately verfying the fuzzer and ASAN are setup properly.
