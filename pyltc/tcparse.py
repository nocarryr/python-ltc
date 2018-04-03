#! /usr/bin/env python

import os
from fractions import Fraction
import subprocess
import shlex
import datetime
import mimetypes
import json
import argparse

from pyltc.framerate import FrameRate, FrameFormat
from pyltc.frames import Frame

def _cmp(o1, o2):
    if o1 < o2:
        return -1
    elif o1 > o2:
        return 1
    else:
        return 0

class Timecode(Frame):
    @classmethod
    def from_str(cls, tc_str, **kwargs):
        l = tc_str.split(':')
        df = False
        if len(l) == 4:
            h, m, s, f = [int(v) for v in l]
        elif len(l) == 3:
            if ';' not in tc_str:
                raise Exception()
            df = True
            h, m = [int(v) for v in l[:2]]
            s, f = [int(v) for v in l[-1].split(';')]
        kwargs['hours'] = h
        kwargs['minutes'] = m
        kwargs['seconds'] = s
        kwargs['frames'] = f
        fr = kwargs['frame_rate']
        ff = FrameFormat(rate=fr, drop_frame=df)
        kwargs['frame_format'] = ff
        return cls(**kwargs)
    def get_dt_time(self):
        h, m, s, f = self.get_hmsf_values()
        fr = self.frame_format.rate
        ms = float(f / fr)
        return datetime.time(h, m, s, ms)


class Encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, FrameRate):
            return {
                '__class__':'FrameRate',
                'numerator':o.numerator,
                'denom':o.denom,
            }
        elif isinstance(o, FrameFormat):
            return {
                '__class__':'FrameFormat',
                'drop_frame':o.drop_frame,
                'rate':o.rate,
            }
        elif isinstance(o, Timecode):
            d = o.get_hmsf_dict()
            d.update({
                '__class__':'Timecode',
                'frame_format':o.frame_format
            })
            return d
        elif isinstance(o, datetime.time):
            d = {key:getattr(o, key) for key in ['hour', 'minute', 'second']}
            d['__class__'] = 'datetime.time'
            return d
        return super(Encoder, self).default(o)

def json_obj_hook(d, current_cls=None):
    clsname = d.get('__class__')
    if current_cls == clsname:
        return d
    if clsname == 'FrameFormat':
        # if 'rate' in d and not isinstance(d['rate'], FrameRate):
        #     d = json_obj_hook(d)
        d = json_obj_hook(d, clsname)
        return FrameFormat(**d)
    elif clsname == 'FrameRate':
        return FrameRate.create(d['numerator'], d['denom'])
    elif clsname == 'Timecode':
        # if 'frame_format' in d and not isinstance(d['frame_format'], FrameFormat):
        #     d = json_obj_hook(d)
        d = json_obj_hook(d, clsname)
        return Timecode(**d)
    elif clsname == 'datetime.time':
        return datetime.time(d['hour'], d['minute'], d['second'])
    return d

def json_dumps(o, **kwargs):
    kwargs.setdefault('cls', Encoder)
    return json.dumps(o, **kwargs)

def json_loads(s):
    return json.loads(s, object_hook=json_obj_hook)

def get_tc(filename):
    cmdstr = 'ffprobe -show_streams -pretty -loglevel quiet {}'.format(filename)
    try:
        ffp = subprocess.check_output(shlex.split(cmdstr))
    except subprocess.CalledProcessError as e:
        print(e.output)
        raise
    in_stream = False
    stream_type = None
    tc_str = None
    fr_str = None

    for line in ffp.splitlines():
        if isinstance(line, bytes):
            line = line.decode('UTF-8')
        if '[STREAM]' in line:
            in_stream = True
            continue
        elif '[/STREAM]' in line:
            in_stream = False
            stream_type = None
            continue
        if not in_stream:
            continue
        if line.startswith('codec_type='):
            stream_type = line.split('=')[1]
        elif stream_type == 'video' and line.startswith('r_frame_rate'):
            fr_str = line.split('=')[1]
        elif line.startswith('TAG:timecode='):
            tc_str = line.split('=')[1]
    fr = FrameRate.create(*[int(v) for v in fr_str.split('/')])
    return Timecode.from_str(tc_str, frame_rate=fr)


# def get_tc(filename):
#     tc_str = get_tc_string(filename)
#     hms, frame = tc_str.split(';')
#     dt = datetime.time(*[int(v) for v in hms.split(':')])
#     return Timecode(dt, int(frame))

def shift_tc(parsed):
    min_tc = None
    for camdir, tc_list in parsed.items():
        _min_tc = min(tc_list)
        if min_tc is None or _min_tc < min_tc:
            min_tc = _min_tc
    print('min_tc: ', min_tc)
    # td = datetime.timedelta(
    #     hours=min_tc.time.hour,
    #     minutes=min_tc.time.minute,
    #     seconds=min_tc.time.second,
    # )
    for camdir, tc_list in parsed.items():
        for tc in tc_list:
            tc -= min_tc


def parse_files(*filenames):
    parsed = {'filenames':{}}
    min_tc = None
    for filename in filenames:
        tc = get_tc(filename)
        if min_tc is None or tc < min_tc:
            min_tc = tc
        parsed['filenames'][filename] = {'tc':tc}

    parsed['min_tc'] = min_tc
    all_tc = [d['tc'] for d in parsed['filenames'].values()]
    fr_match = True
    if len(set([tc.frame_format.drop_frame for tc in all_tc])) != 1:
        fr_match = False
    # print(set([tc.drop_frame for tc in all_tc]))
    # print(set([tc.frame_rate for tc in all_tc]))
    if len(set([tc.frame_format.rate.value for tc in all_tc])) != 1:
        fr_match = False
    if not fr_match:
        parsed['same_format'] = False
        return parsed
    parsed['same_format'] = True
    parsed['min_tc_frames'] = min_tc.total_frames
    parsed['by_tc'] = {}
    for key, d in parsed['filenames'].items():
        tc_str = str(d['tc'])
        if tc_str not in parsed['by_tc']:
            parsed['by_tc'][tc_str] = []
        parsed['by_tc'][tc_str].append({
            'filename':key,
            'abs_filename':os.path.abspath(key),
            'tc':d['tc'],
            'tc_offset':d['tc'] - min_tc,
            'frame_offset':d['tc'].total_frames - min_tc.total_frames,
            'tc_start_frame_number':d['tc'].total_frames,
        })
    return parsed


def parse_bdmv_dir(p):
    parsed = {}
    for camdir in os.listdir(p):
        _camdir = os.path.join(p, camdir)
        if not os.path.isdir(_camdir):
            continue
        parsed[camdir] = []
        _camdir = os.path.join(_camdir, 'PRIVATE', 'JVC', 'CQAVC', 'CLIP')
        for fn in os.listdir(_camdir):
            t = mimetypes.guess_type(fn)[0]
            if t is None:
                continue
            if 'video' not in t:
                continue
            full_fn = os.path.join(_camdir, fn)
            tc = get_tc(full_fn)
            tc.filename = fn
            tc.camdir = camdir
            parsed[camdir].append(tc)
        parsed[camdir].sort()
    shift_tc(parsed)
    data_fn = os.path.join(p, 'timecode.json')
    with open(data_fn, 'w') as f:
        json.dump(parsed, f, cls=Encoder, indent=4)
    # data_fn = os.path.join(p, 'timecode.txt')
    # lines = ['{} = {}'.format(tc.filename, tc) for tc in parsed]
    # with open(data_fn, 'w') as f:
    #     f.write('\n'.join(lines))
    return parsed

def create_bl_import_script(parsed):
    if not parsed['same_format']:
        raise Exception('frame formats do not match')

    def build_clip_kwargs(d, channel, first_clip=False):
        clip_kwargs = {'filepath':d['abs_filename'], 'channel':channel, 'frame_start':d['frame_offset']}
        if first_clip:
            clip_kwargs['use_framerate'] = True
        else:
            clip_kwargs['use_framerate'] = False
        return clip_kwargs

    min_tc = parsed['min_tc']
    first_clip = True
    channel = 1
    all_clip_kwargs = []
    filenames_built = set()
    for d in parsed['by_tc'][str(min_tc)]:
        all_clip_kwargs.append(build_clip_kwargs(d, channel, first_clip))
        first_clip = False
        channel += 1
        filenames_built.add(d['abs_filename'])
    for l in parsed['by_tc'].values():
        for d in l:
            if d['abs_filename'] in filenames_built:
                continue
            all_clip_kwargs.append(build_clip_kwargs(d, channel))
            channel += 1
            filenames_built.add(d['abs_filename'])
    line_fmt = 'bpy.ops.sequencer.movie_strip_add(filepath="{filepath}", channel={channel}, frame_start={frame_start}, use_framerate={use_framerate})'
    lines = ['import bpy']
    lines.extend([line_fmt.format(**clip_kwargs) for clip_kwargs in all_clip_kwargs])
    return '\n'.join(lines)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--bl-script-name', dest='bl_script_name')
    p.add_argument('--bl-script-data', dest='bl_script_data')
    p.add_argument('--bdmv', dest='bdmv', action='store_true')
    p.add_argument('-f', '--filename', dest='filename', action='append')
    p.add_argument('-o', '--outfile', dest='outfile')
    args = p.parse_args()
    if args.bl_script_name:
        data_fn = args.bl_script_data
        with open(data_fn, 'r') as f:
            s = f.read()
        parsed = json_loads(s)
        script = create_bl_import_script(parsed)
        with open(args.bl_script_name, 'w') as f:
            f.write(script)
    elif args.bdmv:
        parse_dir(os.getcwd())
    else:
        parsed = parse_files(*args.filename)
        s = json_dumps(parsed, indent=4)
        if args.outfile:
            with open(args.outfile, 'w') as f:
                f.write(s)
        else:
            print(s)
