import bpy
from bpy_extras import anim_utils

from . import utils


def clear_pose(object):
    for bone in object.pose.bones:
        bone.location = (0, 0, 0)
        bone.scale = (1, 1, 1)

        match bone.rotation_mode:
            case 'QUATERNION':
                bone.rotation_quaternion.identity()
            case 'AXIS_ANGLE':
                bone.rotation_axis_angle = (0, 0, 1, 0)
            case _:
                bone.rotation_euler.zero()

class RGE_OT_bake_animations(bpy.types.Operator):
    bl_idname = "rigify_game_exporter.bake_animations"
    bl_label = "Bake Animations"
    bl_info = {"UNDO"}

    @classmethod
    def poll(cls, context):
        settings = context.scene.RGE_settings
        action_items = context.scene.RGE_action_items
        return settings.rigify_rig and settings.game_rig and len(utils.find_conflicting_action_items(action_items)) == 0

    def execute(self, context):
        scene = context.scene
        settings = scene.RGE_settings
        rigify_rig = settings.rigify_rig
        game_rig = settings.game_rig

        if not rigify_rig or rigify_rig.type != "ARMATURE" or not game_rig or game_rig.type != "ARMATURE":
            return {"CANCELLED"}

        rigify_rig.hide_set(False)
        game_rig.hide_set(False)
        rigify_rig.hide_viewport = False
        game_rig.hide_viewport = False

        rigify_rig_use_nla_backup = None
        rigify_rig_action_backup = None

        game_rig_use_nla_backup = None

        if rigify_rig.animation_data:
            rigify_rig_use_nla_backup = rigify_rig.animation_data.use_nla
            rigify_rig.animation_data.use_nla = False
            rigify_rig_action_backup = rigify_rig.animation_data.action

        if game_rig.animation_data:
            game_rig_use_nla_backup = game_rig.animation_data.use_nla
            game_rig.animation_data.use_nla = False

        if settings.clear_transform_before_baking:
            clear_pose(rigify_rig)
            clear_pose(game_rig)

        action_items = scene.RGE_action_items
        for action_item in action_items:
            # TODO this shouldn't change during the loop, right?
            if rigify_rig.animation_data:
                # mute constraints
                pose_bones = game_rig.pose.bones
                for bone in pose_bones:
                    for constraint in bone.constraints:
                        constraint.mute = False

                if action_item.action and action_item.selected:
                    action = action_item.action

                    rigify_rig.animation_data.action = action

                    if settings.clear_transform_before_baking:
                        clear_pose(rigify_rig)
                        clear_pose(game_rig)

                    action_name = utils.renamed_action(action.name)

                    start_frame = int(action.frame_range[0])
                    end_frame = int(action.frame_range[1]) + 1

                    context.scene.frame_current = start_frame

                    baked_action = anim_utils.bake_action(
                        game_rig,
                        action=None,
                        frames=range(start_frame, end_frame),
                        bake_options=anim_utils.BakeOptions(
                            only_selected=False,
                            do_pose=True,
                            do_object=False,
                            do_visual_keying=True,
                            do_constraint_clear=False,
                            do_parents_clear=False,
                            do_clean=True,
                            do_location=True,
                            do_rotation=True,
                            do_scale=True,
                            do_bbone=True,
                            do_custom_props=True,
                        ),
                    )

                    baked_action.name = action_name

                    # offset keyframes to frame 0
                    start_frame = int(baked_action.frame_range[0])

                    for channelbag in baked_action.layers[0].strips[0].channelbags:
                        for fcurve in channelbag.fcurves:
                            for keyframe_point in fcurve.keyframe_points:
                                keyframe_point.co.x = keyframe_point.co.x - start_frame

                    context.view_layer.update()

                    # remove old NLA track and strips
                    for track in game_rig.animation_data.nla_tracks:
                        if track.name == baked_action.name:
                            strips_to_remove = [strip for strip in track.strips if strip.action == baked_action]
                            for strip in strips_to_remove:
                                track.strips.remove(strip)

                    tracks_to_remove = [track for track in game_rig.animation_data.nla_tracks if len(track.strips) == 0 and track.name == baked_action.name]
                    for track in tracks_to_remove:
                        game_rig.animation_data.nla_tracks.remove(track)

                    # create new NLA track and strips
                    track = game_rig.animation_data.nla_tracks.new()
                    track.name = baked_action.name
                    track.strips.new(baked_action.name, int(baked_action.frame_range[0]), baked_action)

                # mute constraints
                pose_bones = game_rig.pose.bones
                for bone in pose_bones:
                    for constraint in bone.constraints:
                        constraint.mute = True

                # restore previous action
                if rigify_rig.animation_data:
                    if rigify_rig.animation_data.action:
                        rigify_rig.animation_data.action = rigify_rig_action_backup

                # clear action on the game rig
                if game_rig.animation_data:
                    if game_rig.animation_data.action:
                        game_rig.animation_data.action = None

        if rigify_rig.animation_data:
            if rigify_rig_use_nla_backup is not None:
                rigify_rig.animation_data.use_nla = rigify_rig_use_nla_backup
        if game_rig.animation_data:
            if game_rig_use_nla_backup is not None:
                game_rig.animation_data.use_nla = game_rig_use_nla_backup

        return {"FINISHED"}

classes = [
    RGE_OT_bake_animations,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
