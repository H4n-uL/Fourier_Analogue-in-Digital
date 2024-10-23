from .tools import cli
import os, sys

PATH_ABSOLUTE = os.path.dirname(os.path.abspath(__file__))
BANNER = \
'               Fourier Analogue-in-Digital Master encoder/decoder\n' + \
'                             Original Author - HaמuL\n'

def main():
    executable = os.path.basename(sys.argv[0])
    ACTION, METAACTION, INPUT, PARAMS = cli.parse(sys.argv)

    if ACTION in cli.ENCODE_OPT:
        from . import encoder
        encoder.encode(INPUT, PARAMS)
    elif ACTION in cli.DECODE_OPT:
        from . import decoder
        decoder.decode(INPUT, PARAMS, False)
    elif ACTION in cli.PLAY_OPT:
        from . import decoder
        decoder.decode(INPUT, PARAMS, True)
    elif ACTION in cli.REPAIR_OPT:
        from . import repairer
        repairer.repair(INPUT, PARAMS)
    elif ACTION in cli.METADATA_OPT:
        from . import header
        header.modify(INPUT, METAACTION, PARAMS)
    elif ACTION in cli.HELP_OPT:
        print(BANNER)
        helpname = 'general'
        if INPUT in cli.ENCODE_OPT:       helpname = 'encode'
        elif INPUT in cli.DECODE_OPT:     helpname = 'decode'
        elif INPUT in cli.REPAIR_OPT:     helpname = 'repair'
        elif INPUT in cli.PLAY_OPT:       helpname = 'play'
        elif INPUT in cli.METADATA_OPT:   helpname = 'metadata'
        elif INPUT in cli.JSONMETA_OPT:   helpname = 'jsonmeta'
        elif INPUT in cli.VORBISMETA_OPT: helpname = 'vorbismeta'
        elif INPUT in cli.PROFILES_OPT:   helpname = 'profiles'
        print(open(f'{PATH_ABSOLUTE}/help/{helpname}.txt', 'r').read().replace(b'{frad}'.decode(), executable))
        print()
    else:
        print('Fourier Analogue-in-Digital Master encoder/decoder', file=sys.stderr)
        print(f'Abstract syntax: {executable} [encode|decode|repair] <input> [kwargs...]', file=sys.stderr)
        print(f'type `{executable} help` to get help.', file=sys.stderr)

if __name__ == '__main__': main()