import bpy

from . import game_rig_generator
from . import animation_baker
from . import utils


class RGE_OT_clear_actions(bpy.types.Operator):
    bl_idname = "rigify_game_exporter.clear_actions"
    bl_label = "Clear Actions"
    bl_options = {"UNDO"}

    def execute(self, context):
        context.scene.RGE_action_items.clear()
        return {"FINISHED"}

class RGE_OT_load_actions_from_rigify_nla(bpy.types.Operator):
    bl_idname = "rigify_game_exporter.load_actions_from_rigify_nla"
    bl_label = "Load Actions from Rigify NLA"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene.RGE_settings.rigify_rig != None

    def execute(self, context):
        scene = context.scene
        action_items = scene.RGE_action_items
        settings = scene.RGE_settings
        rigify_rig = settings.rigify_rig

        scene.RGE_action_item_index = 0
        if rigify_rig != None and rigify_rig.animation_data != None:
            for nla_track in rigify_rig.animation_data.nla_tracks:
                for nla_strip in nla_track.strips:
                    nla_action = nla_strip.action
                    if nla_action and nla_action not in [action_item.action for action_item in action_items]:
                        action_item = action_items.add()
                        action_item.action = nla_action

        return {"FINISHED"}

class RGE_UL_action_items(bpy.types.UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        row = layout.row(align=True)
        action = item.action

        if action != None:
            row.prop(item, "selected", text="")
            row.prop(action, "name", text="", emboss=False, icon="ACTION")
        else:
            row.label(text="Missing Action", icon="ERROR")

class RGE_PG_action_item(bpy.types.PropertyGroup):
    action: bpy.props.PointerProperty(name="Action", type=bpy.types.Action)
    selected: bpy.props.BoolProperty(default=True)

class RGE_PT_main(bpy.types.Panel):
    bl_label = "Rigify Game Exporter"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Rigify Game Exporter"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = scene.RGE_settings
        rigify_rig = settings.rigify_rig

        col = layout.column(align=True)
        col.label(text="Rigify Rig")

        row = col.row(align=True)
        row.prop(settings, "rigify_rig", text="", placeholder="Rigify Rig")
        if settings.rigify_rig:
            row.prop(settings.rigify_rig, "hide_viewport", text="")

        col.label(text="Game Rig")
        row = col.row(align=True)
        row.prop(settings, "game_rig", text="", placeholder="Game Rig")
        if settings.game_rig:
            row.prop(settings.game_rig, "hide_viewport", text="")

        layout.separator()

        # ----------------------------
        # Game Rig Generator
        # ----------------------------
        if not rigify_rig:
            box = layout.box()
            box.label(text="Select Rigify Rig", icon="INFO")
        
        col = layout.column(align=True)
        col.scale_y = 2
        col.enabled = rigify_rig is not None
        col.operator("rigify_game_exporter.generate_game_rig", icon="OUTLINER_OB_ARMATURE")

        layout.separator()

        # ----------------------------
        # Action Baker
        # ----------------------------
        row = layout.row(align=True)
        row.template_list(
            "RGE_UL_action_items",
            "",
            scene,
            "RGE_action_items",
            scene,
            "RGE_action_item_index",
        )

        row = layout.row(align=True)
        col = row.column(align=True)
        col.operator(
            "rigify_game_exporter.load_actions_from_rigify_nla",
            text="From NLA",
            icon="NLA_PUSHDOWN",
        )

        col = row.column(align=True)
        col.operator(
            "rigify_game_exporter.clear_actions",
            text="Clear All",
            icon="TRASH",
        )

        if not settings.rigify_rig:
            box = layout.box()
            box.label(text="Select Rigify Rig", icon="ERROR")
        if not settings.game_rig:
            box = layout.box()
            box.label(text="Select Game Rig", icon="ERROR")

        for action_item in utils.find_conflicting_action_items(scene.RGE_action_items):
            box = layout.box()
            # TODO remove redundant renamed_action call
            box.label(text=f"{action_item.action.name} -> {utils.renamed_action(action_item.action.name)}", icon="ERROR")
            box.label(text="Action already exists")

        row = layout.row(align=True)
        row.scale_y = 2
        row.operator("rigify_game_exporter.bake_animations", icon="KEYTYPE_KEYFRAME_VEC")

def poll_armature(self, object):
    return object.type == "ARMATURE"

class RGE_PG_settings(bpy.types.PropertyGroup):
    rigify_rig: bpy.props.PointerProperty(name="Rigify Rig", type=bpy.types.Object, poll=poll_armature)
    game_rig: bpy.props.PointerProperty(name="Game Rig", type=bpy.types.Object, poll=poll_armature)

    # TODO why
    clear_transform_before_baking: bpy.props.BoolProperty(default=False)


modules = ( 
    game_rig_generator,
    animation_baker,
)

classes = (
    RGE_OT_clear_actions,
    RGE_OT_load_actions_from_rigify_nla,
    RGE_UL_action_items,
    RGE_PG_action_item,
    RGE_PT_main,
    RGE_PG_settings,
 )

def register():
    for module in modules:
        module.register()

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.RGE_action_items = bpy.props.CollectionProperty(type=RGE_PG_action_item)
    bpy.types.Scene.RGE_action_item_index = bpy.props.IntProperty()
    bpy.types.Scene.RGE_settings = bpy.props.PointerProperty(type=RGE_PG_settings)

def unregister():
    for module in modules:
        module.unregister()

    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.RGE_action_items
    del bpy.types.Scene.RGE_action_item_index
    del bpy.types.Scene.RGE_settings
