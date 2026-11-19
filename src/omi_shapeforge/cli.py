"""Lightweight command-line entrypoints; GPU packages live in backend environments."""
import argparse
import json
import sys
from . import __version__
from .workspace import doctor, load_config, run_smoke


def main(argv=None):
    parser = argparse.ArgumentParser(prog='omi-shapeforge', description='OMI ShapeForge')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--config', help='Workspace TOML; defaults to configs/workspace.toml')
    subcommands = parser.add_subparsers(dest='command', required=True)
    subcommands.add_parser('doctor', help='Check paths and inspect backend Git provenance')
    smoke = subcommands.add_parser('smoke', help='Run a backend sample in its own environment')
    smoke.add_argument('backend', choices=('stereo', 'bundlesdf'))
    smoke.add_argument('--output', help='New output directory; existing paths are refused')
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == 'doctor':
            result = doctor(config)
            code = 0 if result['ready'] else 1
        else:
            result = run_smoke(config, args.backend, args.output)
            code = 0 if result['status'] == 'passed' else 1
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return code
    except (OSError, ValueError, KeyError) as exc:
        print(f'omi-shapeforge: {exc}', file=sys.stderr)
        return 1
