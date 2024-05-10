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
    @staticmethod
    def internal(file_path, play: bool = False, speed: float = 1, e: bool = False, gain: float | None = 1, verbose: bool = False):
        with open(file_path, 'rb') as f:
            # Fixed Header
            head = f.read(64)

            # File signature verification
            methods.signature(head[0x0:0x4])

            # Taking Stream info
            channels = int()
            smprate = int()
            header_length = struct.unpack('>Q', head[0x8:0x10])[0] # 0x08-8B: Total header size

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
                profile = struct.unpack('>B', fhead[0x8:0x9])[0]>>5&0b1==0b1 and True or False
                srate_frame = struct.unpack('>I', fhead[0xc:0x10])[0]       # 0x0c-4B: Sample rate
                fsize = struct.unpack('>I', fhead[0x18:0x1c])[0]   # 0x18-4B: Samples in a frame per channel
                crc32 = fhead[0x1c:0x20]                                    # 0x1c-4B: ISO 3309 CRC32 of Audio Data
                frame = f.read(framelength)
                if e and zlib.crc32(frame) != struct.unpack('>I', crc32)[0]:
                    error_dir.append(str(framescount))
                    if not warned:
                        warned = True
                        print('This file may had been corrupted. Please repack your file via \'ecc\' option for the best music experience.')

                duration += fsize / srate_frame
                if profile in [1, 2]: duration -= fsize//16 / srate_frame

                dlen += len(frame)
                framescount += 1
            if profile in [1, 2]: duration += fsize // 16 / srate_frame
            if error_dir != []: print(f'Corrupt frames: {", ".join(error_dir)}')
            duration /= speed

            f.seek(header_length)
            # if verbose: 
            #     meta, img = header.parse(file_path)
            #     if meta:
            #         meta_tlen = max([len(m[0]) for m in meta])
            #         print('Metadata')
            #         for m in meta:
            #             if '\n' in m[1]:
            #                 m[1] = m[1].replace('\n', '\n'+' '*max(meta_tlen+2, 20))
            #             print(f'  {m[0].ljust(17, ' ')}: {m[1]}')

            try:
                # Starting stream
                if play:
                    print()
                    if verbose: print()
                    bps, avgbps = 0, []
                    stdoutstrm = sd.OutputStream()
                else:
                    tempfstrm = open(variables.temp_pcm, 'ab')
                    dlen = os.path.getsize(file_path) - header_length
                    cli_width = 40
                    start_time = time.time()
                    if verbose: print('\n\n')
                fhead, prev = None, None

                while True:
                    # Reading Frame Header
                    if fhead is None: fhead = f.read(4)
                    if fhead != b'\xff\xd0\xd2\x97':
                        hq = f.read(1)
                        if not hq:
                            if prev is not None:
                                if play: stdoutstrm.write(segment.astype(np.float32))
                                else: tempfstrm.write(segment.astype('>d').tobytes())
                            break
                        fhead = fhead[1:]+hq
                        continue
                    t_frame = time.time()
                    fhead += f.read(28)
                    framelength = struct.unpack('>I', fhead[0x4:0x8])[0]        # 0x04-4B: Audio Stream Frame length
                    efb = struct.unpack('>B', fhead[0x8:0x9])[0]                # 0x08:    Cosine-Float Bit
                    profile, is_ecc_on, endian, float_bits = headb.decode_efb(efb)
                    channels_frame = struct.unpack('>B', fhead[0x9:0xa])[0] + 1 # 0x09:    Channels
                    ecc_dsize = struct.unpack('>B', fhead[0xa:0xb])[0]          # 0x0a:    ECC Data block size
                    ecc_codesize = struct.unpack('>B', fhead[0xb:0xc])[0]       # 0x0b:    ECC Code size
                    srate_frame = struct.unpack('>I', fhead[0xc:0x10])[0]       # 0x0c-4B: Sample rate
                    crc32 = fhead[0x1c:0x20]                                    # 0x1c-4B: ISO 3309 CRC32 of Audio Data

                    # Reading Block
                    frame = f.read(framelength)

                    if is_ecc_on:
                        if e and zlib.crc32(frame) != struct.unpack('>I', crc32)[0]:
                            frame = ecc.decode(frame, ecc_dsize, ecc_codesize)
                        else: frame = ecc.unecc(frame, ecc_dsize, ecc_codesize)

                    segment = fourier.digital(frame, float_bits, channels_frame, endian, profile=profile, smprate=srate_frame, fsize=fsize) * gain # Inversing

                    if prev is not None:
                        fade_in = np.linspace(0, 1, len(prev))
                        fade_out = np.linspace(1, 0, len(prev))
                        for c in range(channels_frame):
                            segment[:len(prev), c] = (segment[:len(prev), c] * fade_in) + (prev[:, c] * fade_out)
                    if profile in [1, 2]:
                        prev = segment[-len(segment)//16:]
                        segment = segment[:-len(prev)]
                    else:
                        prev = None

                    if play:
                        if channels != channels_frame or smprate != srate_frame:
                            stdoutstrm = sd.OutputStream(samplerate=int(srate_frame*speed), channels=channels_frame)
                            stdoutstrm.start()
                            channels, smprate = channels_frame, srate_frame

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

                        i += len(segment) / (smprate*speed)
                        frameNo += 1

                        bps = ((framelength * 8) * srate_frame / len(segment))
                        avgbps.extend([bps, i])
                        depth = [[12,16,24,32,48,64,128],[8,12,16,24,32,48,64]][profile][float_bits]
                        lgs = int(math.log(srate_frame, 1000))
                        lgv = int(math.log(sum(avgbps[::2])/(len(avgbps)//2), 1000))
                        if verbose:
                            print('\x1b[1A\x1b[2K\x1b[1A\x1b[2K', end='')
                            print(f'{methods.tformat(i)} / {methods.tformat(duration)} (Frame #{frameNo} / {framescount} Frames); {depth}b@{srate_frame/10**(lgs*3)} {['','k','M','G','T'][lgs]}Hz {not endian and "B" or "L"}E {channels_frame} channel{channels_frame==1 and "" or "s"}')
                            lgf = int(math.log(bps, 1000))
                            print(f'Profile {profile}, ECC{is_ecc_on and f": {ecc_dsize}/{ecc_codesize}" or " disabled"}, {len(segment)} sample{len(segment)!=1 and"s"or""}/fr {framelength} B/fr {bps/10**(lgf*3):.3f} {['','k','M','G','T'][lgf]}bps/fr, {sum(avgbps[::2])/(len(avgbps)//2)/10**(lgv*3):.3f} {['','k','M','G','T'][lgv]}bps avg')
                        else:
                            print('\x1b[1A\x1b[2K', end='')
                            cq = {1:'Mono',2:'Stereo',4:'Quad',6:'5.1 Surround',8:'7.1 Surround'}.get(channels_frame, f'{channels_frame} ch')
                            print(f'{methods.tformat(i)} / {methods.tformat(duration)}, {profile==0 and f"{depth}b@"or f"{sum(avgbps[::2])/(len(avgbps)//2)/10**(lgv*3):.3f} {['','k','M','G','T'][lgv]}bps "}{srate_frame/10**(lgs*3)} {['','k','M','G','T'][lgs]}Hz {cq}')

                        stdoutstrm.write(segment.astype(np.float32))
                        while avgbps[::1][0] < i - 30: avgbps = avgbps[2:]
                    else:
                        if channels != channels_frame or smprate != srate_frame:
                            if channels != int() or smprate != int():
                                print('\x1b[1A\x1b[2K\x1b[1A\x1b[2K', end='')
                                print('Warning: Fourier Analogue-in-Digital supports variable sample rates and channels, while other codecs do not.')
                                print('The decoder has only decoded the first track. The decoding of two or more tracks with variable sample rates and channels is planned for an update.')
                                return smprate, channels
                            channels, smprate = channels_frame, srate_frame
                        tempfstrm.write(segment.astype('>d').tobytes())
                        i += framelength + 32
                        if verbose:
                            elapsed_time = time.time() - start_time
                            bps = i / elapsed_time
                            lgb = int(math.log(bps, 1000))
                            mult = (fsize / srate_frame) / (time.time() - t_frame)
                            percent = i*100 / dlen
                            b = int(percent / 100 * cli_width)
                            eta = (elapsed_time / (percent / 100)) - elapsed_time if percent != 0 else 'infinity'
                            print('\x1b[1A\x1b[2K\x1b[1A\x1b[2K\x1b[1A\x1b[2K', end='')
                            print(f'Decode Speed: {(bps/10**(lgb*3)):.3f} {['','k','M','G','T'][lgb]}B/s, X{mult:.3f}')
                            print(f'elapsed: {methods.tformat(elapsed_time)}, ETA {methods.tformat(eta)}')
                            print(f"[{'█'*b}{' '*(cli_width-b)}] {percent:.3f}% completed")
                    fhead = None

                if play: stdoutstrm.stop()
                else: tempfstrm.close()
                if play or verbose:
                    print('\x1b[1A\x1b[2K', end='')
                    if play and verbose: print('\x1b[1A\x1b[2K', end='')
                return smprate, channels
            except KeyboardInterrupt:
                if play:
                    try: stdoutstrm.abort()
                    except UnboundLocalError: pass
                else:
                    try: stdoutstrm.close()
                    except UnboundLocalError: pass
                    print('Aborting...')
                sys.exit(0)

    @staticmethod
    def split_q(s) -> tuple[int|None, str]:
        if s == None:
            return None, 'c'
        if not s[0].isdigit():
            raise ValueError('Quality format should be [{Positive integer}{c/v/a}]')
        number = int(''.join(filter(str.isdigit, s)))
        strategy = ''.join(filter(str.isalpha, s))
        return number, strategy

    @staticmethod
    def setaacq(quality: int | None, channels: int):
        if quality == None:
            if channels == 1:
                return 256000
            elif channels == 2:
                return 320000
            else: return 160000 * channels
        return quality

    ffmpeg_lossless = ['wav', 'flac', 'wavpack', 'tta', 'truehd', 'alac', 'dts', 'mlp']

    @staticmethod
    def directcmd(smprate, channels, ffmpeg_cmd):
        command = [
            variables.ffmpeg, '-y',
            '-loglevel', 'error',
            '-f', 'f64be',
            '-ar', str(smprate),
            '-ac', str(channels),
            '-i', variables.temp_pcm,
            '-i', variables.meta,
        ]
        command.extend(['-map_metadata', '1', '-map', '0:a'])
        command.extend(ffmpeg_cmd)
        subprocess.run(command)

    @staticmethod
    def ffmpeg(smprate, channels, codec, f, s, out, ext, quality, strategy, new_srate):
        command = [
            variables.ffmpeg, '-y',
            '-loglevel', 'error',
            '-f', 'f64be',
            '-ar', str(smprate),
            '-ac', str(channels),
            '-i', variables.temp_pcm,
            '-i', variables.meta,
        ]
        if os.path.exists(f'{variables.meta}.image'):
            command.extend(['-i', f'{variables.meta}.image', '-c:v', 'copy'])

        command.extend(['-map_metadata', '1', '-map', '0:a'])

        if os.path.exists(f'{variables.meta}.image'):
            command.extend(['-map', '2:v'])

        if new_srate is not None and new_srate != smprate: command.extend(['-ar', str(new_srate)])

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

    @staticmethod
    def AppleAAC_macOS(smprate, channels, out, quality, strategy):
        try:
            quality = str(quality)
            command = [
                variables.ffmpeg, '-y',
                '-loglevel', 'error',
                '-f', 'f64be',
                '-ar', str(smprate),
                '-ac', str(channels),
                '-i', variables.temp_pcm,
                '-sample_fmt', 's32',
                '-f', 'flac', variables.temp_flac
            ]
            subprocess.run(command)
        except KeyboardInterrupt:
            print('Aborting...')
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
        except KeyboardInterrupt:
            print('Aborting...')
            sys.exit(0)

    @staticmethod
    def AppleAAC_Windows(smprate, channels, out, quality, new_srate):
        try:
            command = [
                variables.aac,
                '--raw', variables.temp_pcm,
                '--raw-channels', str(channels),
                '--raw-rate', str(smprate),
                '--raw-format', 'f64l',
                '--adts',
                '-c', str(quality),
            ]
            if new_srate is not None and new_srate != smprate: command.extend(['--rate', str(new_srate)])
            command.extend([
                '-o', f'{out}.aac',
                '-s'
            ])
            subprocess.run(command)
        except KeyboardInterrupt:
            print('Aborting...')
            sys.exit(0)

    @staticmethod
    def dec(file_path, ffmpeg_cmd, out: str | None = None, bits: int = 32, codec: str | None = None,
            quality: str | None = None, e: bool = False, gain: float | None = None, new_srate: int | None = None, verbose: bool = False):
        # Decoding
        smprate, channels = decode.internal(file_path, e=e, gain=gain, verbose=verbose)
        header.parse_to_ffmeta(file_path, variables.meta)

        try:
            if quality: quality = quality.replace('k', '000').replace('M', '000000').replace('G', '000000000').replace('T', '000000000000')
            q, strategy = decode.split_q(quality)
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
            else: raise ValueError(f'Illegal value {bits} for bits: only 8, 16, and 32 bits are available for decoding.')

            if ffmpeg_cmd is not None:
                decode.directcmd(smprate, channels, ffmpeg_cmd)
            else:
                if (codec == 'aac' and smprate <= 48000 and channels <= 2) or codec in ['appleaac', 'apple_aac']:
                    if strategy in ['c', 'a']: q = decode.setaacq(q, channels)
                    if platform.system() == 'Darwin': decode.AppleAAC_macOS(smprate, channels, out, q, strategy)
                    elif platform.system() == 'Windows': decode.AppleAAC_Windows(smprate, channels, out, q, new_srate)
                elif codec in ['dsd', 'dff']:
                    dsd.encode(smprate, channels, out, ext, verbose)
                elif codec not in ['pcm', 'raw']:
                    decode.ffmpeg(smprate, channels, codec, f, s, out, ext, q, strategy, new_srate)
                else:
                    shutil.move(variables.temp_pcm, f'{out}.{ext}')

        except KeyboardInterrupt:
            print('Aborting...')
        except Exception as exc:
            sys.exit(traceback.format_exc())
        finally:
            sys.exit(0)
