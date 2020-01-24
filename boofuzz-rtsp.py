#!/usr/bin/env python

from boofuzz import *
from boofuzz.ifuzzable import *
import boofuzz.helpers
import re
import argparse

# Global sequence counter & session id for persisting state between requests
cseqCounter = 0
sessionId = None

# Renders Session header with value reflected from a response, or a string fuzz primitive
class SessionHeader(IFuzzable):
    def __init__(self, fuzzable=False, name=None):
        self._fuzzable = fuzzable
        self._name = name
        self.string = boofuzz.primitives.String("", fuzzable=fuzzable)
        self._fuzz_complete = False
        self._mutant_index = self.string.mutant_index

    @property
    def name(self):
        return self._name

    @property
    def mutant_index(self):
        return self._mutant_index

    @property
    def fuzzable(self):
        return self._fuzzable

    @property
    def original_value(self):
        global sessionId
        if sessionId:
            return b"Session: " + sessionId + b"\r\n"
        else:
            return b""

    def mutate(self):
        self._mutant_index += 1
        not_finished_yet = self.string.mutate()
        self._fuzz_complete = not not_finished_yet
        return not_finished_yet

    def num_mutations(self):
        return self.string.num_mutations()

    def render(self):
        if self._fuzzable and (self.string.mutant_index != 0) and not self._fuzz_complete:
            return b"Session: " + self.string.render() + b"\r\n"
        else:
            return self.original_value

    def reset(self):
        self.string.reset()

    def fuzzable(self):
        return self._fuzzable

    def __len__(self):
        return len(self.render())

    def __bool__(self):
        return True
 

# Renders CSeq header with incrementing value, or BitField fuzz primitive
class CSeqHeader(IFuzzable):
    def __init__(self, fuzzable=False, name=None, width=32):
        self._fuzzable = fuzzable
        self._name = name
        self.bitfield = boofuzz.primitives.BitField(0, width, output_format="ascii", fuzzable=fuzzable)
        self._fuzz_complete = False
        self._mutant_index = self.bitfield.mutant_index

    @property
    def name(self):
        return self._name

    @property
    def mutant_index(self):
        return self._mutant_index

    @property
    def fuzzable(self):
        return self._fuzzable

    @property
    def original_value(self):
        global cseqCounter
        return boofuzz.helpers.str_to_bytes(f"CSeq: {str(cseqCounter)}\r\n")

    def mutate(self):
        self._mutant_index += 1
        not_finished_yet = self.bitfield.mutate()
        self._fuzz_complete = not not_finished_yet
        return not_finished_yet

    def num_mutations(self):
        return self.bitfield.num_mutations()

    def render(self):
        if self._fuzzable and (self.bitfield.mutant_index != 0) and not self._fuzz_complete:
            return b"CSeq: " + self.bitfield.render() + b"\r\n"
        else:
            return self.original_value

    def reset(self):
        self.bitfield.reset()

    def fuzzable(self):
        return self._fuzzable

    def __len__(self):
        return len(self.render())

    def __bool__(self):
        return True

# Callbacks

def cb_reset_headers(target, fuzz_data_logger, session, sock, *args, **kwargs):
    global cseqCounter
    global sessionId
    cseqCounter = 1
    sessionId = None

def cb_update_headers(target, fuzz_data_logger, session, node, edge, *args, **kwargs):
    global cseqCounter
    global sessionId
    cseqCounter += 1
    data = session.last_recv
    if data:
        p = re.compile(b'\nSession: ([A-Za-z0-9$_.+-]*)') 
        m = p.search(data)
        if m:
            newSessionId = m.group(1)
            sessionId = newSessionId

# RTSP-Specific protocol definition static functions

def s_cseq_header(fuzzable=False):
    h = CSeqHeader(fuzzable=fuzzable)
    blocks.CURRENT.push(h)

def s_session_header(fuzzable=False):
    h = SessionHeader(fuzzable=fuzzable)
    blocks.CURRENT.push(h)

def s_content_length_header(body_block_name, fuzzable=False):
    s_static("Content-Length: ")
    s_size(body_block_name, output_format="ascii", fuzzable=fuzzable)
    s_static("\r\n")

def init_rtsp_method(name, host, port, media_path, fuzz_everything=False, name_suffix=""):
    s_initialize(name.lower() + name_suffix)
    s_static(name.upper())
    s_delim(" ", fuzzable=fuzz_everything)
    s_string("rtsp", fuzzable=fuzz_everything)
    s_delim(":", fuzzable=fuzz_everything)
    s_delim("/", fuzzable=fuzz_everything)
    s_delim("/", fuzzable=fuzz_everything)
    s_string(host, fuzzable=fuzz_everything)
    s_delim(":", fuzzable=fuzz_everything)
    s_string(str(port), fuzzable=fuzz_everything)
    s_static("/")
    s_string(media_path, fuzzable=fuzz_everything)
    s_static(" RTSP/1.0\r\n")
    s_cseq_header(fuzzable=fuzz_everything)


def main():
    method_paths = {
            "options": ["options"],
            "describe": ["describe"],
            "describe.more_headers": ["describe2"],
            "setup": ["setup"],
            "play": ["setup", "play"],
            "pause": ["setup", "play", "pause"],
            "teardown": ["setup", "play", "pause", "teardown"],
            "get_parameter": ["setup", "get_parameter"],
            "set_parameter": ["setup", "set_parameter"],
            "set_parameter.encoding": ["setup", "set_parameter2"],
            "announce": ["setup", "announce"],
            "record": ["setup", "record"]
            }

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--host")
    argparser.add_argument("--port", type=int)
    argparser.add_argument("--proto", choices=("tcp", "udp"))
    argparser.add_argument("--path")
    argparser.add_argument("--method", choices=method_paths.keys())
    argparser.add_argument("--index-start", type=int)
    argparser.add_argument("--index-end", type=int)
    args = argparser.parse_args()

    host = "127.0.0.1"
    if args.host:
        host = args.host
    port = 554
    if args.port:
        port = args.port
    protocol = 'tcp'
    if args.proto:
        protocol = args.proto
    media_path = "test.mp3"
    if args.path:
        media_path = args.path
    index_start = 1
    if args.index_start:
        index_start = args.index_start
    index_end = None
    if args.index_end:
        index_start = args.index_end

    session = Session(target=Target(connection=SocketConnection(host, port, proto=protocol)), receive_data_after_fuzz=True,
                      restart_callbacks=[], pre_send_callbacks=[cb_reset_headers], post_test_case_callbacks=[],
                      index_start=index_start, index_end=index_end)

    init_rtsp_method("options", host, port, media_path, fuzz_everything=True)
    s_string("User-Agent")
    s_delim(":")
    s_delim(" ")
    s_string("fuzz")
    s_static("\r\n")
    s_static("\r\n")

    init_rtsp_method("describe", host, port, media_path)
    s_static("Accept: ")
    s_string("application/sdp")
    s_static("\r\n")
    s_static("\r\n")

    init_rtsp_method("describe", host, port, media_path, name_suffix="2")
    s_static("Accept: application/sdp\r\n")
    s_static("Accept-Encoding: ")
    s_string("iso-8859-5, unicode-1-1;q=0.8")
    s_static("\r\n")
    s_static("Accept-Language: ")
    s_string("da, en-gb;q=0.8, en;q=0.7")
    s_static("\r\n")
    s_static("Authorization: ")
    s_string("fuzz")
    s_static("\r\n")
    s_static("Bandwidth: ")
    s_dword(4000, output_format="ascii")
    s_static("\r\n")
    s_static("Connection: ")
    s_string("close")
    s_static("\r\n")
    s_static("Date: ")
    s_string("Tue, 15 Nov 1994 08:12:31 GMT")
    s_static("\r\n")
    s_static("Referer: ")
    s_string("http://example.com/")
    s_static("\r\n")
    s_static("\r\n")

    init_rtsp_method("setup", host, port, media_path)
    s_static("Transport: ")
    s_string("RTP/AVP")
    s_delim(";")
    s_string("unicast")
    s_delim(";")
    s_string("client_port")
    s_delim("=")
    s_string("55808")
    s_delim("-")
    s_string("55809")
    s_static("\r\n")
    s_static("Blocksize: ")
    s_dword(1000, output_format="ascii") # TODO: what won't break the protocol?
    s_static("\r\n")
    s_static("Cache-Control: ")
    s_string("no-cache")
    s_static("\r\n")
    s_static("From: ")
    s_string("test@example.com")
    s_static("\r\n")
    s_static("\r\n")

    init_rtsp_method("teardown", host, port, media_path)
    s_session_header()
    s_static("\r\n")
    s_static("\r\n")

    init_rtsp_method("play", host, port, media_path)
    s_session_header()
    s_static("Range: ")
    s_string("npt")
    s_delim("=")
    s_qword(0, output_format="ascii")
    s_static(".")
    s_qword(0, output_format="ascii")
    s_delim("-")
    s_qword(5, output_format="ascii")
    s_static(".")
    s_qword(0, output_format="ascii")
    s_static("\r\n")
    s_static("Scale: ")
    s_dword(1, output_format="ascii")
    s_static("\r\n")
    s_static("Speed: ")
    s_dword(1, output_format="ascii")
    s_static(".")
    s_dword(0, output_format="ascii")
    s_static("\r\n")
    s_static("\r\n")

    init_rtsp_method("pause", host, port, media_path)
    s_session_header(fuzzable=True)
    s_static("\r\n")

    init_rtsp_method("get_parameter", host, port, media_path)
    s_session_header()
    s_content_length_header("body")
    s_static("Content-Type: ")
    s_string("text/parameters")
    s_static("\r\n")
    s_static("If-Modified-Since: ")
    s_string("Tue, 15 Nov 1994 08:12:31 GMT")
    s_static("\r\n")
    s_static("Last-Modified: ")
    s_string("Tue, 15 Nov 1994 08:12:31 GMT")
    s_static("\r\n")
    s_static("\r\n")
    with s_block("body"):
        s_string("packets_received")
        s_delim("\n")
        s_string("jitter")

    init_rtsp_method("set_parameter", host, port, media_path)
    s_session_header()
    s_content_length_header("body")
    s_static("Content-Type: ")
    s_string("text/parameters")
    s_static("\r\n")
    s_static("Content-Language: ")
    s_string("en")
    s_static("\r\n")
    s_static("\r\n")
    with s_block("body"):
        s_string("barparam")
        s_delim(":")
        s_delim(" ")
        s_string("barstuff")

    init_rtsp_method("set_parameter", host, port, media_path, name_suffix="2")
    s_session_header()
    s_content_length_header("body")
    s_static("Content-Type: text/parameters\r\n")
    s_static("Content-Encoding: ")
    s_string("gzip")
    s_static("\r\n")
    s_static("\r\n")
    with s_block("body"):
        s_random("", 0, 4096)

    init_rtsp_method("announce", host, port, media_path)
    s_session_header()
    s_content_length_header("body")
    s_static("Content-Type: ")
    s_string("application/sdp")
    s_static("\r\n")
    s_static("\r\n")
    with s_block("body"):
        s_string("v=0\no=mhandley 2890844526 2890845468 IN IP4 127.0.0.1\ns=SDP Seminar\ni=A Seminar on the session description protocol\nu=http://127.0.0.1/staff/M.Handley/sdp.03.ps\ne=mjh@isi.edu (Mark Handley)\nc=IN IP4 127.0.0.1/127\nt=2873397496 2873404696\na=recvonly\nm=audio 3456 RTP/AVP 0\nm=video 2232 RTP/AVP 31")

    init_rtsp_method("record", host, port, "recording.test")
    s_static("Conference: ")
    s_string("127.0.0.1/32492374")
    s_static("\r\n")
    s_static("Expires: ")
    s_string("Thu, 01 Dec 2044 16:00:00 GMT")
    s_static("\r\n")
    s_static("Scale: ")
    s_dword(1, output_format="ascii")
    s_static(".")
    s_dword(0, output_format="ascii")
    s_static("\r\n")
    s_static("\r\n")

    session.connect(s_get("options"))
    session.connect(s_get("describe"))
    session.connect(s_get("describe2"))
    session.connect(s_get("setup"))
    session.connect(s_get("setup"), s_get("play"), callback=cb_update_headers)
    session.connect(s_get("play"), s_get("pause"), callback=cb_update_headers)
    session.connect(s_get("pause"), s_get("teardown"), callback=cb_update_headers)
    session.connect(s_get("setup"), s_get("get_parameter"), callback=cb_update_headers)
    session.connect(s_get("setup"), s_get("set_parameter"), callback=cb_update_headers)
    session.connect(s_get("setup"), s_get("set_parameter2"), callback=cb_update_headers)
    session.connect(s_get("setup"), s_get("announce"), callback=cb_update_headers)
    session.connect(s_get("setup"), s_get("record"), callback=cb_update_headers)

    if args.method:
        path = method_paths[args.method.lower()]
        session.fuzz_single_node_by_path(path)
    else:
        session.fuzz()

if __name__ == "__main__":
    main()

