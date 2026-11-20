"""Lightweight command-line entrypoints; GPU packages live in backend environments."""
import argparse
import json
import sys
from . import __version__
from .workspace import doctor, load_config, run_smoke
from .runner import RunCancelled, passed
from .workflows import launch


def main(argv=None):
    parser = argparse.ArgumentParser(prog='omi-shapeforge', description='OMI ShapeForge')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--config', help='Workspace TOML; defaults to configs/workspace.toml')
    subcommands = parser.add_subparsers(dest='command', required=True)
    subcommands.add_parser('doctor', help='Check paths and inspect backend Git provenance')
    smoke = subcommands.add_parser('smoke', help='Run a backend sample in its own environment')
    smoke.add_argument('backend', choices=('stereo', 'bundlesdf'))
    smoke.add_argument('--output', help='New output directory; existing paths are refused')
    simulation = subcommands.add_parser('simulate', help='Run a configured simulation workflow')
    simulation.add_argument('engine', choices=('mujoco',))
    simulation.add_argument('--scene', help='MJCF scene; defaults to the configured prototype')
    simulation.add_argument('--steps', type=int, default=240)
    simulation.add_argument('--output', help='New output directory; existing paths are refused')
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == 'doctor':
            result = doctor(config)
            code = 0 if result['ready'] else 1
        elif args.command == 'smoke':
            result = run_smoke(config, args.backend, args.output)
            code = 0 if passed(result) else 1
        else:
            result = launch(config, 'simulation.mujoco', args.output, args.scene, args.steps)
            code = 0 if passed(result) else 1
        if args.command != 'doctor' and result['execution']['state'] == 'cancelled':
            code = 130
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return code
    except RunCancelled as exc:
        if exc.record is not None:
            print(json.dumps(exc.record, indent=2, ensure_ascii=False))
        return 130
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, KeyError) as exc:
        print(f'omi-shapeforge: {exc}', file=sys.stderr)
        return 2
