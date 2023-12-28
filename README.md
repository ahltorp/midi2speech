Midi2speech
===========

Requirements
------------

* Python 3.9
* libmidi package from pypi
* MBROLA for the actual synthesis: [MBROLA](https://github.com/numediart/MBROLA)

Running
-------

```
./midi2speech.py test.mid test.txt vowels.txt > test.pho
mbrola sw2/sw2 test.pho test.wav
```

