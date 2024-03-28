# Fourier Analogue-in-Digital

## Project Overview

It was developed as part of [Project Archivist](https://mikhael-openworkspace.notion.site/Project-Archivist-e512fa7a21474ef6bdbd615a424293cf) with the goal of keeping analogue signals in digital. More information can be found in the [Notion](https://mikhael-openworkspace.notion.site/Fourier-Analogue-in-Digital-d170c1760cbf4bb4aaea9b1f09b7fead?pvs=4).

**Warning: Fourier Analogue-in-Digital Compact is unstable because the format is constantly changing. Please do not use the lossy compression option when encoding Fourier Analogue-in-Digital just yet.**

## How to install

1. Download the Git zip
2. Install Python (3.11^)
3. Execute install.sh
4. Restart shell with source ~/.*shrc

Installation is still only supported on Unix-like OS.

## External Resources

[Python](https://github.com/python/cpython), [FFmpeg](https://github.com/FFmpeg/FFmpeg), [QAAC](https://github.com/nu774/qaac), [QTFiles](https://github.com/AnimMouse/QTFiles), afconvert

### pip Packages

1. mdctn
2. numpy
3. reedsolo
4. scipy
5. sounddevice

## How to use

Encoding

```bash
fourier encode "path/to/audio.flac" \
--bits 32 \                                        # Bit depth
\  # Optional
--output "path/to/fourierAnalogue.frad" \          # Output file
--frame_size 2048 \                                # Samples per block
--enable_ecc \                                     # ECC enabled or not
--data_ecc_size 128 20 \                           # Sizes of data block and ECC block when ECC enabled
--little_endian \                                  # Endianness
--gain -6 \                                        # Gain
--dbfs \                                           # Gain units flag
--metadata "Metadata Title" "Metadata contents" \  # Metadata
--jsonmeta "path/to/metadata.json" \               # Metadata json, will override --metadata.
--image "path/to/image/file" \                     # Image file
--verbose
```

Decoding

```bash
fourier decode "path/to/fourierAnalogue.frad" \
\  # Optional
--bits 32 \                      # Bit depth for lossless compression codecs (supports 8, 16, 32)
--enable_ecc \                   # ECC verification or not
--gain 1.2 \                     # Gain
--dbfs \                         # Gain units flag
--output "path/for/audio.aac" \  # Output file
--codec "codec" \                # Codec type
--quality "320000c" \            # Quailty factor for lossy compression codecs (example is constant 320 kbps)
--verbose
```

Playback

```bash
fourier play "path/to/fourierAnalogue.frad" \
\  # Optional
--key keys \     # Playback keys
--speed speed \  # Playback speed
--gain 3.4 \     # Gain
--dbfs \         # Gain units flag
--enable_ecc \   # ECC verification or not
--verbose
```

Edit metadata

```bash
fourier meta-modify "path/to/fourierAnalogue.frad" \
\  # Optional
--metadata "Metadata Title" "Metadata contents" \  # Metadata
--jsonmeta "path/to/metadata.json" \               # Metadata json, will override --metadata.
--image "path/to/image/file" \                     # Image file
```

Extract metadata

```bash
fourier parse "path/to/fourierAnalogue.frad" \
\  # Optional
--output "path/for/metadata" \  # Output file.meta.json, Output file.meta.image
```

ECC packing/repacking

```bash
fourier ecc "path/to/fourierAnalogue.frad" \
\  # Optional
--verbose
```

Software Recording

```bash
fourier record "path/to/fourierAnalogue.frad" \
\  # Optional
--bits 32 \                                        # Bit depth
--frame_size 2048 \                                # Samples per block
--enable_ecc \                                     # ECC enabled or not
--data_ecc_size 128 20 \                           # Sizes of data block and ECC block when ECC enabled
--little_endian \                                  # Endianness
--metadata "Metadata Title" "Metadata contents" \  # Metadata
--jsonmeta "path/to/metadata.json" \               # Metadata json, will override --metadata.
--image "path/to/image/file" \                     # Image file
```

Metadata JSON

```json
[
    {"key": "KEY",                              "type": "string", "value": "VALUE"},
    {"key": "AUTHOR",                           "type": "string", "value": "H4n_uL"},
    {"key": "Key & String value encoding type", "type": "string", "value": "UTF-8"},
    {"key": "Base64 type Value",                "type": "base64", "value": "QmFzZTY0IEV4YW1wbGU="},
    {"key": "File is also available",           "type": "base64", "value": "U3VwcG9ydHMgdXAgdG8gMjU2IFRpQg=="},
    {"key": "No unsupported characters",        "type": "string", "value": "All utf-8/base64 metadata is allowed!"},
    {"key": "Supports duplicate keys",          "type": "string", "value": "See what happens!"},
    {"key": "Supports duplicate keys",          "type": "string", "value": "Voilà!"}
]
```

## How to contribute

Simply create a new branch in the repository, make your changes, and submit a merge request to me for approval. Pretty much anything will pass if it conforms to the FrAD format standard.

## Developer information

HaמuL, <jun061119@proton.me>