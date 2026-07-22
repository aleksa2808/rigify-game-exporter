import bpy

from . import nla_action_loader
from . import game_rig_generator
from . import action_baker
from . import common


class RGE_OT_clear_actions(bpy.types.Operator):
    bl_idname = "rigify_game_exporter.clear_actions"
    bl_label = "Clear Actions"
    bl_options = {"UNDO"}

    def execute(self, context):
        context.scene.RGE_actions_to_bake.clear()
        return {"FINISHED"}

class RGE_OT_load_actions_from_rigify_nla(bpy.types.Operator):
    bl_idname = "rigify_game_exporter.load_actions_from_rigify_nla"
    bl_label = "Load Actions from Rigify NLA"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return common.find_rigify_rig() != None

    def execute(self, context):
        scene = context.scene
        action_items = scene.RGE_actions_to_bake
        rigify_rig = common.find_rigify_rig()

        scene.RGE_actions_to_bake_index = 0
        if rigify_rig != None and rigify_rig.animation_data != None:
            for nla_track in rigify_rig.animation_data.nla_tracks:
                for nla_strip in nla_track.strips:
                    nla_action = nla_strip.action
                    if nla_action and nla_action not in [action_item.action for action_item in action_items]:
                        action_item = action_items.add()
                        action_item.action = nla_action

        return {"FINISHED"}

class RGE_PT_main(bpy.types.Panel):
    bl_label = "Rigify Game Exporter"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Rigify Game Exporter"

    def draw(self, context):
        layout = self.layout
        rigify_rig = common.find_rigify_rig()
        game_rig = common.find_game_rig()

        if rigify_rig == None:
            box = layout.box()
            box.label(text=f"Cannot find Rigify Rig ({common.RIGIFY_RIG_NAME})", icon="ERROR")
            return

        if game_rig == None:
            self.draw_game_rig_generator(context, rigify_rig)
        else:
            self.draw_action_baker(context)

    def draw_game_rig_generator(self, context, rigify_rig):
        layout = self.layout

        # show list of selected bones
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

    def draw_action_baker(self, context):
        layout = self.layout
        scene = context.scene

        layout.label(text="Select Actions to Bake from Rigify Rig")
        row = layout.row(align=True)
        row.template_list(
            "RGE_UL_action_items",
            "actions_to_bake",
            scene,
            "RGE_actions_to_bake",
            scene,
            "RGE_actions_to_bake_index",
        )

        row = layout.row(align=True)
        col = row.column(align=True)
        col.operator(
            "rigify_game_exporter.load_actions_from_rigify_nla",
            text="Load Rigify NLA",
            icon="NLA_PUSHDOWN",
        )

        col = row.column(align=True)
        col.operator(
            "rigify_game_exporter.clear_actions",
            text="Clear All",
            icon="TRASH",
        )

        conflicting_action_items = common.find_conflicting_action_items(scene.RGE_actions_to_bake)
        conflicting_action_item_count = len(conflicting_action_items)
        if conflicting_action_item_count > 0:
            header, body = layout.panel("conflicting_action_items_subpanel", default_closed=True)

            selected_action_item_count = len([action_item for action_item in scene.RGE_actions_to_bake if action_item.selected])
            if conflicting_action_item_count == selected_action_item_count:
                header.label(text="All Selected Actions Already Exist")
            else:
                header.label(text=f"{conflicting_action_item_count} out of {selected_action_item_count} Selected Actions Already Exist")

            if body != None:
                for action_item in conflicting_action_items:
                    # TODO remove redundant renamed_action call
                    body.label(text=f"{action_item.action.name} -> {common.renamed_action(action_item.action.name)}", icon="ACTION")

                layout.separator()

        row = layout.row(align=True)
        row.scale_y = 2
        row.operator("rigify_game_exporter.bake_actions", icon="KEYTYPE_KEYFRAME_VEC")


modules = ( 
    common,
    nla_action_loader,
    game_rig_generator,
    action_baker,
)

classes = (
    RGE_OT_clear_actions,
    RGE_OT_load_actions_from_rigify_nla,
    RGE_PT_main,
 )

def register():
    for module in modules:
        module.register()

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.RGE_actions_to_bake = bpy.props.CollectionProperty(type=common.RGE_PG_action_item)
    bpy.types.Scene.RGE_actions_to_bake_index = bpy.props.IntProperty()

def unregister():
    del bpy.types.Scene.RGE_actions_to_bake_index
    del bpy.types.Scene.RGE_actions_to_bake

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    for module in reversed(modules):
        module.unregister()
