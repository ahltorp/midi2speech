#!/usr/bin/python3

# requires pypi package: libmidi

import sys
import argparse

from libmidi.types.midifile import MidiFile
from libmidi.types.messages.meta import META_MESSAGE_VALUE
from libmidi.types.messages.channel import ChannelMessageType
from libmidi.types.messages.meta import MetaMessageType

# Return new tempo if tempo entry is at or earlier than pos

def find_tempo(tempoentry, pos):
    if tempoentry[0] <= pos:
        for k, v in tempoentry[1].items():
            if k == MetaMessageType.SET_TEMPO:
                return v.tempo / 1000000
    return None

semitone = pow(2, 1/12)

#
# Convert MIDI note to frequency in Hz
#

def note2freq(midinote):
    return round(440 * pow(semitone, midinote - 69), 2)

#
# Parse command line arguments
#

parser = argparse.ArgumentParser(
    description='Converts midi and phonetic symbols to MBROLA files'
)

parser.add_argument('midifile')
parser.add_argument('phonesfile')
parser.add_argument('vowelfile')

args = parser.parse_args()

#
# Read MIDI file
#

midifile = MidiFile.from_file(args.midifile)

ticks_per_quarter = midifile.division
assert(ticks_per_quarter < 32768) # We only handle ticks per quarter note, not SMTPE time

#
# Collect tempo information
#

raw_tempotrack = midifile.tracks[0]

tempotrack = [(0, {})]
pos = 0
for event in raw_tempotrack.events:
    assert event.message.get_status_byte() == META_MESSAGE_VALUE
    if event.delta_time > 0:
        pos += event.delta_time
        tempotrack.append((pos, {}))
    assert event.message.meta_message_type not in tempotrack[-1]
    tempotrack[-1][1][event.message.meta_message_type] = event.message

notetracks = midifile.tracks[1:]

#
# Collect MIDI notes
#

notes = []
playing_note = {}
for track in notetracks:
    pos = 0
    seconds = 0
    tempo = find_tempo(tempotrack[0], 0) or 0
    tempolist = tempotrack

    for event in track.events:
        seconds += event.delta_time / ticks_per_quarter * tempo
        pos += event.delta_time
        if event.message.get_status_byte() == META_MESSAGE_VALUE:
            continue
        if tempolist:
            new_tempo = find_tempo(tempolist[0], pos)
            if new_tempo is not None:
                tempo = new_tempo
        assert event.message.channel_message_type in [ChannelMessageType.NOTE_OFF, ChannelMessageType.NOTE_ON]
        if event.message.channel_message_type == ChannelMessageType.NOTE_ON and event.message.velocity > 0:
            if playing_note:
                print("overlapping notes at", seconds, "seconds", file=sys.stderr)
                print(playing_note, file=sys.stderr)
                print({"note":event.message.note, "on": seconds}, file=sys.stderr)
                sys.exit(1)
            playing_note = {"note":event.message.note, "on": seconds}
        else:
            playing_note["off"] = seconds
            notes.append(playing_note)
            playing_note = {}

#
# Read vowels file
#

vowels = set(open(args.vowelfile).read().split())

#
# Read phones file
#

phones = []
with open(args.phonesfile, "rt") as phonesfile:
    for row in phonesfile:
        row = row.strip()
        row = row.partition("#")[0]
        if not row:
            continue
        phones.append(row)

#
# Combine MIDI notes and phones
#

total = 0

offset = 0
for note, phonestring in zip(notes, phones):
    freq = note2freq(note["note"])
    diff = ((note["on"] - offset) * 1000)
    length = ((note["off"] - note["on"]) * 1000)
    if diff < 20:
        length += diff
        diff = 0
    if diff:
        print("_", diff)
        total += diff
    offset = note["off"]
    phonelist = phonestring.split(" ")
    isvowel = [phone in vowels for phone in phonelist]
    if sum(isvowel) == 1:
        if len(phonelist) == 2 and ":" not in phonestring and isvowel[0]:
            consonantdistribution = 2
            voweldistribution = 1
        elif len(phonelist) == 4 and ":" in phonestring:
            consonantdistribution = 1
            voweldistribution = 2
        elif len(phonelist) > 2 and ":" in phonestring:
            consonantdistribution = 1
            voweldistribution = 3
        elif len(phonelist) == 2:
            consonantdistribution = 1
            voweldistribution = 2
        else:
            consonantdistribution = 1
            voweldistribution = 1
    else:
        voweldistribution = 1
        consonantdistribution = 1
    distribution = []
    for phone in phonelist:
        if phone in vowels:
            distribution.append(voweldistribution)
        else:
            distribution.append(consonantdistribution)
    totalshares = sum(distribution)
    for phone, share in zip(phonelist, distribution):
        phonelength = length / totalshares * share
        if phone in vowels:
            print(phone, phonelength, 0, freq, 100, freq)
        else:
            print(phone, phonelength)
        total += phonelength
