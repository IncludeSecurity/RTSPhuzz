# includesec-boofuzz-rtsp

Boofuzz-RTSP is a [boofuzz](https://github.com/jtpereyda/boofuzz)-based fuzzer for [RTSP](https://tools.ietf.org/html/rfc2326) servers. It connects as a client to target RTSP servers and fuzzes messages or sequences of messages. It's inital development by Include Security was sponsored by the Mozilla Open Source Support (MOSS) awards program (https://www.mozilla.org/en-US/moss/). It is provided as free and open unsupported software for the greater good of the maintainers and authors of RTSP services.

# Usage

Specify the host, port, and RTSP path to a media file on the target server:

```boofuzz-rtsp.py --host target.server.host --port 554 --path test/media/file.mp3```

In addition, a single method can be fuzzed, and the range of test cases can be specified:

```boofuzz-rtsp.py --host target.server.host --port 554 --path test/media/file.mp3 --method play --index-start 100 --index-end 150```

Boofuzz will open a web interface on localhost, and will record results locally.

# Design

The code supports fuzzing every client to server message defined in the RTSP protocol (RFC 2326.) Most of the protocol's supported headers are distributed amongst the fuzzed methods such that each is fuzzed in at least one message, but not everywhere in order to reduce redundant fuzzing. The `OPTIONS` message was chosen to fuzz all of the attributes present in first line of a request.
Header values and message bodies are given reasonable default values in order to hopefully allow successful fuzzing of later messages in a sequence of messages. In some cases, multiple versions of the same method are defined; one is intended to have better values for a sequence of messages, the other intended to cover more headers.
The RTSP protocol's `CSeq`, `Session`, and `Content-Length` headers are special cases. `CSeq` is a sequence counter, and is incremented with each message in a sequence. The `Session` header value is recorded from message responses, and reflected in subsequent requests. The `Content-Length` header is set to the correct value for messages with a body.

# Limitations / Potential Improvements

The code currently doesn't implement monitoring or restarting of the target.

Using boofuzz orients this fuzzer more toward discovering bugs related to parsing the protocol or incorrect values in protocol fields. It is less suited to discovering bugs triggered by strange sequences of requests, for example.

This fuzzer also only fuzzes the RTSP protocol. RTSP is intended to be used with another stream transport protocol, usually RTP; however, this fuzzer does not interact with RTP. It also doesn't fuzz SDP stream descriptions, or certain header values that support multiple formats. In addition, the `SET_PARAMETER` and `GET_PARAMETER` methods don't use real-world parameters.

Finally, the RTSP protocol supports interleaved RTP stream data on the same transport (e.g. TCP) as the RTSP messages. This feature hasn't currently been implemented.

