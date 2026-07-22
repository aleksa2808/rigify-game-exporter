import bpy
from bpy_extras import anim_utils

from . import common

def is_bone_kept(bone):
    return bone.select or bone.use_deform

# TODO hardcoded
def renamed_action(name):
    return name.replace("CTRL_", "")

class RGE_OT_generate_game_rig(bpy.types.Operator):
    bl_idname = "rigify_game_exporter.generate_game_rig"
    bl_label = "Generate Game Rig"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return common.find_rigify_rig() != None and common.find_game_rig() == None

    def execute(self, context):
        rigify_rig = common.find_rigify_rig()

        if rigify_rig == None or common.find_game_rig() != None:
            return {'CANCELLED'}

        game_rig = self.generate_rig(context, rigify_rig)
        self.bake_actions(context, rigify_rig, game_rig)

        return {"FINISHED"}

    def generate_rig(self, context, rigify_rig):
        is_object_hidden = rigify_rig.hide_get()
        is_object_hidden_in_viewport = rigify_rig.hide_viewport
        rigify_rig.hide_viewport = False
        rigify_rig.hide_set(False)

        context.view_layer.objects.active = rigify_rig
        bpy.ops.object.mode_set(mode="OBJECT")

        rigify_rig.hide_viewport = is_object_hidden_in_viewport
        rigify_rig.hide_set(is_object_hidden)

        game_rig = rigify_rig.copy()
        # TODO check if there isn't one already
        game_rig.name = common.GAME_RIG_NAME

        game_rig.display_type = "SOLID"
        game_rig.show_in_front = True
        game_rig.data = rigify_rig.data.copy()

        if not bpy.context.collection.objects.get(game_rig.name):
            bpy.context.collection.objects.link(game_rig)

        bpy.ops.object.select_all(action="DESELECT")
        game_rig.select_set(True)
        context.view_layer.objects.active = game_rig
        bpy.ops.object.mode_set(mode="EDIT")

        # clear bone collections
        for collection in list(game_rig.data.collections):
            game_rig.data.collections.remove(collection)

        edit_bones = game_rig.data.edit_bones
        bones_to_remove = []
        for bone in edit_bones:
            if not is_bone_kept(bone):
                bones_to_remove.append(bone)
                continue

            bone.use_inherit_rotation = True
            bone.use_local_location = True
            bone.inherit_scale = "FULL"

            # find and attach surviving parent
            if bone.parent and not is_bone_kept(bone.parent):
                new_parent = None
                for ancestor in bone.parent_recursive:
                    if is_bone_kept(ancestor):
                        new_parent = ancestor
                        break
                    else:
                        deform_bone = edit_bones.get(ancestor.name.replace("ORG-", "DEF-"))
                        # check that the deform bone exists and that it's not the same as the current bone
                        # first DEF bone in the chain, like shoulders, get parented to their respective ORG bones
                        if deform_bone and deform_bone.name != bone.name and deform_bone.use_deform:
                            new_parent = deform_bone
                            break
                
                if not new_parent:
                    self.report({'WARNING'}, f"Bone {bone.name} left without surviving parent.")
                bone.parent = new_parent
        
        for bone in bones_to_remove:
            edit_bones.remove(bone)
        self.report({'INFO'}, f"Removed {len(bones_to_remove)} bones from game skeleton.")

        # clear leftover animation data
        game_rig.animation_data_clear()
        game_rig.data.animation_data_clear()
        
        bpy.ops.object.mode_set(mode="POSE")
        pose_bones = game_rig.pose.bones
        for bone in pose_bones:
            # remove rigify widget, display as a standard bone
            bone.custom_shape = None

            # unlock bone transforms
            bone.lock_location[0] = False
            bone.lock_location[1] = False
            bone.lock_location[2] = False

            bone.lock_scale[0] = False
            bone.lock_scale[1] = False
            bone.lock_scale[2] = False

            bone.lock_rotation_w = False
            bone.lock_rotation[0] = False
            bone.lock_rotation[1] = False
            bone.lock_rotation[2] = False

            # remove existing constraints
            for constraint in list(bone.constraints):
                bone.constraints.remove(constraint)

            # add transform constraints
            constraint = bone.constraints.new("COPY_LOCATION")
            constraint.target = rigify_rig
            constraint.subtarget = bone.name

            constraint = bone.constraints.new("COPY_ROTATION")
            constraint.target = rigify_rig
            constraint.subtarget = bone.name

        bpy.ops.object.mode_set(mode="OBJECT")
        for object in bpy.data.objects:
            armature_modifiers = [modifier for modifier in object.modifiers if modifier.type == "ARMATURE"]
            if len(armature_modifiers) > 1:
                self.report({'WARNING'}, f"Object {object.name} contains multiple armature modifiers.")

            for modifier in armature_modifiers:
                if modifier.object == rigify_rig:
                    # retarget armature modifier
                    modifier.object = game_rig

                    # reparent model
                    matrix_world = object.matrix_world.copy()
                    object.parent = game_rig
                    object.matrix_world = matrix_world

        game_rig.hide_render = False

        return game_rig

    def bake_actions(self, context, rigify_rig, game_rig):
        if rigify_rig.animation_data == None:
            self.report({'INFO'}, f"Rigify rig ({rigify_rig.name}) doesn't contain animation data, nothing to bake.")
            return

        rigify_rig_use_nla_backup = rigify_rig.animation_data.use_nla
        rigify_rig.animation_data.use_nla = False
        rigify_rig_action_backup = rigify_rig.animation_data.action

        actions_to_bake = []
        if rigify_rig != None and rigify_rig.animation_data != None:
            for nla_track in rigify_rig.animation_data.nla_tracks:
                for nla_strip in nla_track.strips:
                    nla_action = nla_strip.action
                    if nla_action and nla_action not in actions_to_bake:
                        actions_to_bake.append(nla_action)

        for action in actions_to_bake:
            rigify_rig.animation_data.action = action
            start_frame = int(action.frame_range[0])
            end_frame = int(action.frame_range[1]) + 1

            # TODO not sure if this is needed
            context.scene.frame_current = start_frame
            context.view_layer.update()

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

            baked_action.name = renamed_action(action.name)

            # create NLA track and strip
            track = game_rig.animation_data.nla_tracks.new()
            track.name = baked_action.name
            track.strips.new(baked_action.name, int(baked_action.frame_range[0]), baked_action)

        # mute game rig constraints
        for bone in game_rig.pose.bones:
            for constraint in bone.constraints:
                constraint.mute = True

        # restore rigify rig settings
        rigify_rig.animation_data.action = rigify_rig_action_backup
        if rigify_rig_use_nla_backup is not None:
            rigify_rig.animation_data.use_nla = rigify_rig_use_nla_backup

class RGE_PT_game_rig_generator(bpy.types.Panel):
    bl_label = "Game Rig Generator"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Rigify Game Exporter"

    def draw(self, context):
        layout = self.layout
        rigify_rig = common.find_rigify_rig()

        if rigify_rig == None:
            box = layout.box()
            box.label(text=f"Cannot find Rigify Rig ({common.RIGIFY_RIG_NAME})", icon="ERROR")
            return

        # show list of selected bones (can only do it when in pose mode)
        if context.mode == 'POSE' and context.object == rigify_rig:
            selected = context.selected_pose_bones or []

            if len(selected) > 0:
                header, body = layout.panel("selected_bones_subpanel", default_closed=True)
                header.label(text=f"{len(selected)} Extra Bone(s) Selected")
                if body != None:
                    for bone in sorted(selected, key=lambda b: b.name):
                        body.label(text=bone.name, icon='BONE_DATA')

                    layout.separator()

        col = layout.column(align=True)
        col.scale_y = 2
        col.operator("rigify_game_exporter.generate_game_rig", icon="OUTLINER_OB_ARMATURE")


classes = (
    RGE_OT_generate_game_rig,
    RGE_PT_game_rig_generator,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
