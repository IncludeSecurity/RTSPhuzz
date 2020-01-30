# RTSPhuzz

RTSPhuzz is a [boofuzz](https://github.com/jtpereyda/boofuzz)-based fuzzer for [RTSP](https://tools.ietf.org/html/rfc2326) servers. It connects as a client to target RTSP servers and fuzzes messages or sequences of messages. The inital development work by Include Security was sponsored by the [Mozilla Open Source Support (MOSS) awards program](https://www.mozilla.org/en-US/moss/). It is provided as free and open unsupported software for the greater good of the maintainers and authors of RTSP services -- FOSS and COTS alike!

# Usage

Specify the host, port, and RTSP path to a media file on the target server:

```RTSPhuzz.py --host target.server.host --port 554 --path test/media/file.mp3```

In addition, a single method can be fuzzed, and the range of test cases can be specified:

```RTSPhuzz.py --host target.server.host --port 554 --path test/media/file.mp3 --method play --index-start 100 --index-end 150```

The `gdb-restarter.py` script may be useful for restarting the target and storing cores. Use it like this:

```gdb -q -x gdb-restarter.py [target-rtsp-server]```

Compiling targets with [Address Sanitizer is also useful](https://clang.llvm.org/docs/AddressSanitizer.html)

The Boofuzz framework will open a web interface on localhost port 26000, and will record results locally in a `boofuzz-results/` directory. The web interface can be re-opened for the database from a previous run with Boofuzz's `boo` tool:

```boo open <run-*.db>```

For more information, see [boofuzz's documentation](https://boofuzz.readthedocs.io/en/stable/user/quickstart.html).

# Design

The code supports fuzzing all client to server directed messages defined in the RTSP protocol [(RFC 2326.)](https://tools.ietf.org/html/rfc2326) Most of the protocol's supported headers are distributed amongst the fuzzed methods such that each is fuzzed in at least one message, but not everywhere in order to reduce redundant fuzzing. The `OPTIONS` message was chosen to fuzz all of the attributes present in first line of a request.

Header values and message bodies are given reasonable default values in order to hopefully allow successful fuzzing of later messages in a sequence of messages. In some cases, multiple versions of the same method are defined; one is intended to have better values for a sequence of messages, the other intended to cover more headers.
The RTSP protocol's `CSeq`, `Session`, and `Content-Length` headers are special cases. `CSeq` is a sequence counter, and is incremented with each message in a sequence. The `Session` header value is recorded from message responses, and reflected in subsequent requests. The `Content-Length` header is set to the correct value for messages with a body.

The boofuzz fuzzing framework was chosen to leverage its built-in mutations, logging, and web interface. The use of boofuzz also makes the fuzzer mostly deterministic; boofuzz will iterate through all of its mutations of every fuzzable part of the defined protocol. The data that will change most commonly between executions will be the `Session` header, which is reflected from a server response header.

# Prior Work
We are aware of two existing RTSP fuzzers, [StreamFUZZ](https://github.com/rabimba/StreamFUZZ) and [RtspFuzzer](https://github.com/iSECPartners/RtspFuzzer). 

RtspFuzzer uses the Peach fuzzing framework to fuzz RTSP responses, however it targets RTSP client implementations, whereas our fuzzer targets RTSP servers.

StreamFUZZ is a Python script that does not utilize a fuzzing framework. Similar to our fuzzer, it fuzzes different parts of RTSP messages and sends them to a server. However, it is more simplistic; it doesn't fuzz as many messages or header fields as our fuzzer, it does not account for the types of the fields it fuzzes, and it does not keep track of sesisons for fuzzing sequences of messages.

# Limitations / Future Improvements

This is a v1 release, we encourage you to think of ways to improve this tool and make it better. We will accept PRs and shout-outs for any bugs you find with this tool (@includesecurity).

The code currently doesn't implement monitoring or restarting of the target, although an example GDB controlling Python script is provided with this tool as a base to form your own fuzzing harness enviornement. 

Using boofuzz orients this fuzzer more toward discovering bugs related to parsing the protocol or incorrect values in protocol fields. It is less suited to discovering bugs triggered by strange sequences of requests, for example.

This fuzzer also only fuzzes the RTSP protocol. RTSP is intended to be used with another stream transport protocol, usually RTP; however, this fuzzer does not interact with RTP. It also doesn't fuzz SDP stream descriptions, or certain header values that support multiple formats. 

In addition, the `SET_PARAMETER` and `GET_PARAMETER` methods don't use real-world parameters. The parameter names for `SET_PARAMETER` and `GET_PARAMETER` are not defined in the RTSP specification, and different RTSP servers support different parameters, or don't support any parameters for these methods.

Finally, the RTSP protocol supports interleaved RTP stream data on the same transport (e.g. TCP) as the RTSP messages. This feature hasn't currently been implemented.
