import bpy


def is_bone_kept(bone):
    return bone.select or bone.use_deform

class RGE_OT_generate_game_rig(bpy.types.Operator):
    bl_idname = "rigify_game_exporter.generate_game_rig"
    bl_label = "Generate Game Rig"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene.RGE_settings.rigify_rig != None

    def execute(self, context):
        scene = context.scene
        settings = scene.RGE_settings
        rigify_rig = settings.rigify_rig

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
        game_rig.name = "rig"
        settings.game_rig = game_rig

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

        return {"FINISHED"}


classes = [RGE_OT_generate_game_rig]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
