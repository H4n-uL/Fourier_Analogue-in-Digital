#!/bin/bash

python3 Python/main.py modify "path/to/audio.flac" \
\
--meta "Metadata Title" "Metadata contents" \
--jsonmeta "path/to/metadata.json" \
--image "path/to/image/file"

# JSON Metadata goes prior comparing Metadata option.