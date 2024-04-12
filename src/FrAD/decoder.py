from .common import variables, methods
from .fourier import fourier
from .header import header
# import matplotlib.pyplot as plt
# from scipy.fft import dct
import numpy as np
import math, os, platform, shutil, struct, subprocess, sys, time, traceback, zlib
import sounddevice as sd
from .tools.ecc import ecc
from .tools.headb import headb
from .tools.dsd import dsd

class decode:
    def internal(file_path, play: bool = False, speed: float = 1, e: bool = False, gain: float = 1, verbose: bool = False):
        with open(file_path, 'rb') as f:
            # Fixed Header
            header = f.read(64)

            # File signature verification
            methods.signature(header[0x0:0x4])

            # Taking Stream info
            channels = None
            sample_rate = None
            header_length = struct.unpack('>Q', header[0x8:0x10])[0] # 0x08-8B: Total header size

            f.seek(header_length)

            # Inverse Fourier Transform #
            i = 0
            frameNo = 0

            # Getting secure framed source length
            dlen = framescount = 0
            ecc_dsize = ecc_codesize = 0
            duration = 0
            warned = False
            error_dir = []
            while True:
                fhead = f.read(32)
                if not fhead: break
                framelength = struct.unpack('>I', fhead[0x4:0x8])[0]        # 0x04-4B: Audio Stream Frame length
                lossy = struct.unpack('>B', fhead[0x8:0x9])[0]>>5&0b1==0b1 and True or False
                srate_frame = struct.unpack('>I', fhead[0xc:0x10])[0]       # 0x0c-4B: Sample rate
                samples_p_chnl = struct.unpack('>I', fhead[0x18:0x1c])[0]   # 0x18-4B: Samples in a frame per channel
                crc32 = fhead[0x1c:0x20]                                    # 0x1c-4B: ISO 3309 CRC32 of Audio Data
                frame = f.read(framelength)
                if e and zlib.crc32(frame) != struct.unpack('>I', crc32)[0]:
                    error_dir.append(str(framescount))
                    if not warned:
                        warned = True
                        print('This file may had been corrupted. Please repack your file via \'ecc\' option for the best music experience.')

                duration += samples_p_chnl / srate_frame
                if lossy: duration -= samples_p_chnl//16 / srate_frame

                dlen += len(frame)
                framescount += 1
            if lossy: duration += samples_p_chnl // 16 / srate_frame
            if error_dir != []: print(f'Corrupt frames: {", ".join(error_dir)}')

            f.seek(header_length)

            try:
                # Starting stream
                if play:
                    print()
                    if verbose: print()
                else:
                    stream = open(variables.temp_pcm, 'ab')
                    dlen = os.path.getsize(file_path) - header_length
                    cli_width = 40
                    start_time = time.time()
                    if verbose: print('\n\n')
                prev = None

                while True:
                    # Reading Frame Header
                    fhead = f.read(32)
                    if not fhead:
                        if prev is not None:
                            if play == True: stream.write(prev.astype(np.float32))
                            else: stream.write(prev.astype(np.float64).tobytes())
                        break
                    framelength = struct.unpack('>I', fhead[0x4:0x8])[0]        # 0x04-4B: Audio Stream Frame length
                    efb = struct.unpack('>B', fhead[0x8:0x9])[0]                # 0x08:    Cosine-Float Bit
                    lossy, is_ecc_on, endian, float_bits = headb.decode_efb(efb)
                    channels_frame = struct.unpack('>B', fhead[0x9:0xa])[0] + 1 # 0x09:    Channels
                    ecc_dsize = struct.unpack('>B', fhead[0xa:0xb])[0]          # 0x0a:    ECC Data block size
                    ecc_codesize = struct.unpack('>B', fhead[0xb:0xc])[0]       # 0x0b:    ECC Code size
                    srate_frame = struct.unpack('>I', fhead[0xc:0x10])[0]       # 0x0c-4B: Sample rate
                    crc32 = fhead[0x1c:0x20]                                    # 0x1c-4B: ISO 3309 CRC32 of Audio Data
                    ssize_dict = {0b110: 16*channels_frame, 0b101: 8*channels_frame, 0b100: 6*channels_frame, 0b011: 4*channels_frame, 0b010: 3*channels_frame, 0b001: 2*channels_frame, 0b000: 1.5*channels_frame}

                    # Reading Block
                    frame = f.read(framelength)

                    if is_ecc_on:
                        if e and zlib.crc32(frame) != struct.unpack('>I', crc32)[0]:
                            frame = ecc.decode(frame, ecc_dsize, ecc_codesize)
                        else: frame = ecc.unecc(frame, ecc_dsize, ecc_codesize)

                    segment = fourier.digital(frame, float_bits, channels_frame, endian, lossy=lossy) * gain # Inversing

                    if prev is not None:
                        fade_in = np.linspace(0, 1, len(prev))
                        fade_out = np.linspace(1, 0, len(prev))
                        for c in range(channels_frame):
                            segment[:len(prev), c] = (segment[:len(prev), c] * fade_in) + (prev[:, c] * fade_out)
                    if lossy:
                        prev = segment[-len(segment)//16:]
                        segment = segment[:-len(prev)]
                    else:
                        prev = None

                    if play:
                        if channels != channels_frame or sample_rate != srate_frame:
                            stream = sd.OutputStream(samplerate=int(srate_frame*speed), channels=channels_frame)
                            stream.start()
                            channels, sample_rate = channels_frame, srate_frame

                        # for i in range(channels_frame):
                        #     plt.subplot(channels_frame, 1, i+1)
                        #     plt.plot(segment[:, i], alpha=0.5)
                        #     y = np.abs(dct(segment[:, i]) / len(segment))
                        #     plt.fill_between(range(1, len(y)+1), y, -y, edgecolor='none')
                        #     # plt.xscale('log', base=2)
                        #     plt.ylim(-1, 1)
                        # plt.draw()
                        # plt.pause(0.000001)
                        # plt.clf()

                        i += len(segment) / (sample_rate*speed)
                        frameNo += 1
                        if verbose:
                            print('\x1b[1A\x1b[2K\x1b[1A\x1b[2K', end='')
                            depth = [12, 16, 24, 32, 48, 64, 128][float_bits]
                            lg = int(math.log(srate_frame, 1000))
                            kmgt = ['','k','M','G','T'][lg]
                            print(f'{methods.tformat(i)} / {methods.tformat(duration)} (Frame #{frameNo} / {framescount} Frames); {depth}b@{srate_frame/10**(lg*3)} {kmgt}Hz {not endian and "B" or "L"}E {channels_frame} channel{channels_frame>1 and "s" or ""}')
                            print(f'{lossy and "Lossy" or "Lossless"}, ECC{is_ecc_on and f": {ecc_dsize}/{ecc_codesize}" or " disabled"}, {len(segment)} samples & {framelength} Bytes per frame')
                        else:
                            print('\x1b[1A\x1b[2K', end='')
                            print(f'{(i):.3f} s / {(duration):.3f} s')

                        stream.write(segment.astype(np.float32))
                    else:
                        if channels != channels_frame or sample_rate != srate_frame:
                            if channels != None or sample_rate != None:
                                print('\x1b[1A\x1b[2K\x1b[1A\x1b[2K', end='')
                                print('Warning: Fourier Analogue-in-Digital supports variable sample rates and channels, while other codecs do not.')
                                print('The decoder has only decoded the first track. The decoding of two or more tracks with variable sample rates and channels is planned for an update.')
                                return sample_rate, channels
                            channels, sample_rate = channels_frame, srate_frame
                        stream.write(segment.astype(np.float64).tobytes())
                        i += framelength + 32
                        if verbose:
                            elapsed_time = time.time() - start_time
                            bps = i / elapsed_time
                            mult = bps / (ssize_dict[float_bits] * sample_rate)
                            percent = i*100 / dlen
                            b = int(percent / 100 * cli_width)
                            eta = (elapsed_time / (percent / 100)) - elapsed_time if percent != 0 else 'infinity'
                            print('\x1b[1A\x1b[2K\x1b[1A\x1b[2K\x1b[1A\x1b[2K', end='')
                            print(f'Decode Speed: {(bps / 10**6):.3f} MB/s, X{mult:.3f}')
                            print(f'elapsed: {methods.tformat(elapsed_time)}, ETA {methods.tformat(eta)}')
                            print(f"[{'█'*b}{' '*(cli_width-b)}] {percent:.3f}% completed")
                time.sleep(1)
                stream.close()
                if play or verbose:
                    print('\x1b[1A\x1b[2K', end='')
                    if play and verbose: print('\x1b[1A\x1b[2K', end='')
                return sample_rate, channels
            except KeyboardInterrupt:
                if play:
                    try: stream.abort()
                    except UnboundLocalError: pass
                else:
                    try: stream.close()
                    except UnboundLocalError: pass
                    print('Aborting...')
                    os.remove(variables.temp_pcm)
                sys.exit(0)

    def split_q(s):
        if s == None:
            return None, 'c'
        if not s[0].isdigit():
            raise ValueError('Quality format should be [{Positive integer}{c/v/a}]')
        number = ''.join(filter(str.isdigit, s))
        strategy = ''.join(filter(str.isalpha, s))
        return number, strategy

    def setaacq(quality, channels):
        if quality == None:
            if channels == 1:
                quality = 256000
            elif channels == 2:
                quality = 320000
            else: quality = 160000 * channels
        return quality

    ffmpeg_lossless = ['wav', 'flac', 'wavpack', 'tta', 'truehd', 'alac', 'dts', 'mlp']

    def ffmpeg(sample_rate, channels, codec, f, s, out, ext, quality, strategy, nsr):
        command = [
            variables.ffmpeg, '-y',
            '-loglevel', 'error',
            '-f', 'f64le',
            '-ar', str(sample_rate),
            '-ac', str(channels),
            '-i', variables.temp_pcm,
            '-i', variables.meta,
        ]
        if os.path.exists(f'{variables.meta}.image'):
            command.extend(['-i', f'{variables.meta}.image', '-c:v', 'copy'])

        command.extend(['-map_metadata', '1', '-map', '0:a'])

        if os.path.exists(f'{variables.meta}.image'):
            command.extend(['-map', '2:v'])

        if nsr is not None and nsr != sample_rate: command.extend(['-ar', str(nsr)])

        command.append('-c:a')
        if codec in ['wav', 'riff']:
            command.append(f'pcm_{f}')
        else:
            command.append(codec)

        # Lossy VS Lossless
        if codec in decode.ffmpeg_lossless:
            command.append('-sample_fmt')
            command.append(s)
        else:
            # Variable bitrate quality
            if strategy == 'v' or codec == 'libvorbis':
                if quality == None: quality = '10' if codec == 'libvorbis' else '0'
                command.append('-q:a')
                command.append(quality)

            # Constant bitrate quality
            if strategy in ['c', '', None] and codec != 'libvorbis':
                if quality == None: quality = '4096000'
                if codec == 'libopus' and int(quality) > 512000:
                    quality = '512000'
                command.append('-b:a')
                command.append(quality)

        if ext == 'ogg':
            # Muxer
            command.append('-f')
            command.append(ext)

        # File name
        command.append(f'{out}.{ext}')
        subprocess.run(command)
        os.remove(variables.temp_pcm)

    def AppleAAC_macOS(sample_rate, channels, out, quality, strategy):
        try:
            quality = str(quality)
            command = [
                variables.ffmpeg, '-y',
                '-loglevel', 'error',
                '-f', 'f64le',
                '-ar', str(sample_rate),
                '-ac', str(channels),
                '-i', variables.temp_pcm,
                '-sample_fmt', 's32',
                '-f', 'flac', variables.temp_flac
            ]
            subprocess.run(command)
            os.remove(variables.temp_pcm)
        except KeyboardInterrupt:
            print('Aborting...')
            os.remove(variables.temp_pcm)
            os.remove(variables.temp_flac)
            sys.exit(0)
        try:
            if strategy in ['c', '', None]: strategy = '0'
            elif strategy == 'a': strategy = '1'
            else: raise ValueError()

            command = [
                variables.aac,
                '-f', 'adts', '-d', 'aac' if int(quality) > 64000 else 'aach',
                variables.temp_flac,
                '-b', quality,
                f'{out}.aac',
                '-s', strategy
            ]
            subprocess.run(command)
            os.remove(variables.temp_flac)
        except KeyboardInterrupt:
            print('Aborting...')
            os.remove(variables.temp_flac)
            sys.exit(0)

    def AppleAAC_Windows(sample_rate, channels, out, quality, nsr):
        try:
            command = [
                variables.aac,
                '--raw', variables.temp_pcm,
                '--raw-channels', str(channels),
                '--raw-rate', str(sample_rate),
                '--raw-format', 'f64l',
                '--adts',
                '-c', str(quality),
            ]
            if nsr is not None and nsr != sample_rate: command.extend(['--rate', str(nsr)])
            command.extend([
                '-o', f'{out}.aac',
                '-s'
            ])
            subprocess.run(command)
            os.remove(variables.temp_pcm)
        except KeyboardInterrupt:
            print('Aborting...')
            os.remove(variables.temp_pcm)
            sys.exit(0)

    def dec(file_path, out: str = None, bits: int = 32, codec: str = None, quality: str = None, e: bool = False, gain: list = None, nsr: int = None, verbose: bool = False):
        # Decoding
        sample_rate, channels = decode.internal(file_path, e=e, gain=methods.get_gain(gain), verbose=verbose)
        header.parse_to_ffmeta(file_path, variables.meta)

        try:
            quality, strategy = decode.split_q(quality)
            # Checking name
            if out:
                out, ext = os.path.splitext(out)
                ext = ext.lstrip('.').lower()
                if codec:
                    if ext: pass
                    else:   ext = codec
                else:
                    if ext: codec = ext
                    else:   codec = ext = 'flac'
            else:
                out = os.path.basename(file_path).rsplit('.', 1)[0]
                if codec:   ext = codec
                else:       codec = ext = 'flac'

            codec = codec.lower()

            # Checking Codec and Muxers
            if codec in ['vorbis', 'opus', 'speex']:
                if codec in ['vorbis', 'speex']:
                    ext = 'ogg'
                codec = 'lib' + codec
            if codec == 'ogg': codec = 'libvorbis'
            if codec == 'mp3': codec = 'libmp3lame'

            if bits == 32:
                f = 's32le'
                s = 's32'
            elif bits == 16:
                f = 's16le'
                s = 's16'
            elif bits == 8:
                f = s = 'u8'
            else: raise ValueError(f"Illegal value {bits} for bits: only 8, 16, and 32 bits are available for decoding.")

            if quality: int(quality.replace('k', '000'))

            if (codec == 'aac' and sample_rate <= 48000 and channels <= 2) or codec in ['appleaac', 'apple_aac']:
                if strategy in ['c', 'a']: quality = decode.setaacq(quality, channels)
                if platform.system() == 'Darwin': decode.AppleAAC_macOS(sample_rate, channels, out, quality, strategy)
                elif platform.system() == 'Windows': decode.AppleAAC_Windows(sample_rate, channels, out, quality, nsr)
            elif codec in ['dsd', 'dff']:
                dsd.encode(sample_rate, channels, out, ext, verbose)
            elif codec not in ['pcm', 'raw']:
                decode.ffmpeg(sample_rate, channels, codec, f, s, out, ext, quality, strategy, nsr)
            else:
                shutil.move(variables.temp_pcm, f'{out}.{ext}')

        except KeyboardInterrupt:
            print('Aborting...')
            os.remove(variables.temp_pcm)
        except Exception as e:
            if os.path.exists(variables.meta): os.remove(variables.meta)
            if os.path.exists(f'{variables.meta}.image'): os.remove(f'{variables.meta}.image')
            os.remove(variables.temp_pcm)
            sys.exit(traceback.format_exc())
        finally:
            os.remove(variables.meta)
            if os.path.exists(f'{variables.meta}.image'): os.remove(f'{variables.meta}.image')
            sys.exit(0)