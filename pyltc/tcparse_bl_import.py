bl_info = {
    "name": "Timecode Tools",
    "description": "Timecode Tools",
    "author": "Matthew Reid",
    "version": (1, 0),
    "blender": (2, 79, 0),
    "location": "Sequencer > UI",
    "warning": "", # used for warning icon and text in addons panel
    # "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/"
    #             "Scripts/My_Script",
    # "tracker_url": "https://developer.blender.org/maniphest/task/edit/form/2/",
    "support": "COMMUNITY",
    "category": "Sequencer",
}

import json
import bpy


class TcClip(bpy.types.PropertyGroup):
    filepath = bpy.props.StringProperty(subtype='FILE_PATH')
    strip_data_path = bpy.props.StringProperty()
    frame_start = bpy.props.IntProperty()
    tc_start_frame_number = bpy.props.IntProperty()
    channel = bpy.props.IntProperty()
    def get_strip(self):
        scene = self.id_data
        if self.strip_data_path:
            try:
                strip = scene.path_resolve(self.strip_data_path)
            except ValueError:
                self.strip_data_path = ''
                strip = None
        else:
            strip = None
        if strip is not None:
            return strip
        for strip in scene.sequence_editor.sequences:
            if strip.channel == self.channel:
                data_path = strip.path_from_id()
                if self.strip_data_path != data_path:
                    self.strip_data_path = data_path
                return strip
    # def save_to_strip(self):
    #     strip = self.get_strip()
    #     # keys = set(strip.keys())
    #     # bpy.ops.wm.properties_add(data_path=self.strip_data_path)
    #     # keys = set(strip.keys()) - keys
    #     # prop_name = keys.pop()
    #     #
    #     # bpy.ops.wm.properties_edit(data_path="scene.sequence_editor.active_strip", property="prop1", value="1.0")


class TcClipGroup(bpy.types.PropertyGroup):
    @classmethod
    def register(cls):
        bpy.types.Scene.tcparse_clips = bpy.props.CollectionProperty(type=cls)
        cls.clips = bpy.props.CollectionProperty(type=TcClip)
    @classmethod
    def unregister(cls):
        del bpy.types.Scene.tcparse_clips
    @classmethod
    def get_or_create(cls, context=None):
        if context is None:
            context = bpy.context
        coll = context.scene.tcparse_clips
        if len(coll):
            obj = coll[0]
        else:
            obj = coll.add()
        return obj
    def get_next_channel(self):
        ch = 0
        for clip in self.clips:
            if clip.channel > ch:
                ch = clip.channel
        return ch
    def add_clip(self, context, **kwargs):
        tc_start_frame_number = kwargs.pop('tc_start_frame_number')
        frame_start = kwargs['frame_start']
        filepath = kwargs['filepath']
        bpy.ops.sequencer.movie_strip_add(**kwargs)
        for seq in context.selected_sequences:
            if seq.name in self.clips:
                continue
            clip = self.clips.add()
            clip.name = seq.name
            clip.filepath = filepath
            clip.strip_data_path = seq.path_from_id()
            clip.channel = seq.channel
            clip.frame_start = frame_start
            clip.tc_start_frame_number = tc_start_frame_number

class TcImportOp(bpy.types.Operator):
    bl_idname = "tcparse.import"
    bl_label = "Import TC Clips"

    bl_options = {'REGISTER', 'UNDO'}

    filepath = bpy.props.StringProperty(subtype="FILE_PATH")

    def add_clip(self, context, **kwargs):
        # clips = context.scene.tcparse_clips
        tc_start_frame_number = kwargs.pop('tc_start_frame_number')
        frame_start = kwargs['frame_start']
        filepath = kwargs['filepath']
        bpy.ops.sequencer.movie_strip_add(**kwargs)
        for seq in context.selected_sequences:
            # if seq.name in self.clips:
            #     continue
            # clip = clips.add()
            clip = seq.tcparse_clip
            clip.name = seq.name
            clip.filepath = filepath
            clip.strip_data_path = seq.path_from_id()
            clip.channel = seq.channel
            clip.frame_start = frame_start
            clip.tc_start_frame_number = tc_start_frame_number

    def execute(self, context):
        with open(self.filepath, 'r') as f:
            s = f.read()
        parsed = json.loads(s)
        # tc_clips = TcClipGroup.get_or_create(context)
        first_clip = True
        channel = 1
        # channel = tc_clips.get_next_channel()
        for clips in parsed['by_tc'].values():
            for d in clips:
                clip_kwargs = {
                    'filepath':d['abs_filename'],
                    'channel':channel,
                    'frame_start':d['frame_offset'],
                    'tc_start_frame_number':d['tc_start_frame_number'],
                }
                if first_clip:
                    clip_kwargs['use_framerate'] = True
                else:
                    clip_kwargs['use_framerate'] = False
                self.add_clip(context, **clip_kwargs)
                # bpy.ops.sequencer.movie_strip_add(**clip_kwargs)
                first_clip = False
                channel += 1
                # channel = tc_clips.get_next_channel()
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class TcImportPanel(bpy.types.Panel):
    bl_idname = 'tcparse.panel'
    bl_label = 'TC Panel'
    bl_region_type = 'UI'
    bl_space_type = 'SEQUENCE_EDITOR'
    @classmethod
    def poll(cls, context):
        if context.area.type != 'SEQUENCE_EDITOR':
            return False
        return True
    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text='Import TC json')
        row = col.row()
        row.operator(TcImportOp.bl_idname)

def register():
    bpy.utils.register_class(TcClip)
    # bpy.utils.register_class(TcClipGroup)
    # bpy.types.Scene.tcparse_clips = bpy.props.CollectionProperty(type=TcClip)
    bpy.types.Sequence.tcparse_clip = bpy.props.PointerProperty(type=TcClip)
    bpy.utils.register_class(TcImportOp)
    bpy.utils.register_class(TcImportPanel)
def unregister():
    bpy.utils.unregister_class(TcImportPanel)
    bpy.utils.unregister_class(TcImportOp)
    # bpy.utils.unregister_class(TcClipGroup)
    # del bpy.types.Scene.tcparse_clips
    del bpy.types.Sequence.tcparse_clip
    bpy.utils.unregister_class(TcClip)

if __name__ == '__main__':
    register()
