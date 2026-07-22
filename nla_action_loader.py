import bpy

from . import common


# TODO deduplicate with `common.find_conflicting_action_items()``
def find_conflicting_action_items(context):
    action_items = context.scene.RGE_actions_to_load
    rigify_rig = common.find_rigify_rig()

    if rigify_rig == None or rigify_rig.animation_data == None or rigify_rig.animation_data.nla_tracks == None:
        return []

    filtered_actions = []
    for action_item in action_items:
        if not action_item.selected:
            continue

        action = action_item.action
        if action is None:
            continue

        exists = False
        for track in rigify_rig.animation_data.nla_tracks:
            for strip in track.strips:
                if strip.action == action:
                    exists = True
                    break
            if exists:
                break

        if exists:
            filtered_actions.append(action_item)

    return filtered_actions

class RGE_OT_refresh_actions(bpy.types.Operator):
    bl_idname = "rigify_game_exporter.refresh_actions"
    bl_label = "Refresh Actions"

    def execute(self, context):
        scene = context.scene

        scene.RGE_actions_to_load.clear()
        for action in bpy.data.actions:
            item = scene.RGE_actions_to_load.add()
            item.action = action
            item.selected = False

        return {'FINISHED'}


class RGE_OT_select_all_actions(bpy.types.Operator):
    bl_idname = "rigify_game_exporter.select_all_actions"
    bl_label = "Select All"

    def execute(self, context):
        for item in context.scene.RGE_actions_to_load:
            item.selected = True

        return {'FINISHED'}


class RGE_OT_clear_selected_actions(bpy.types.Operator):
    bl_idname = "rigify_game_exporter.clear_selected_actions"
    bl_label = "Clear Selected"

    @classmethod
    def poll(cls, context):
        return any([item.selected for item in context.scene.RGE_actions_to_load])

    def execute(self, context):
        for item in context.scene.RGE_actions_to_load:
            item.selected = False

        return {'FINISHED'}


class RGE_OT_load_actions_to_nla(bpy.types.Operator):
    bl_idname = "rigify_game_exporter.load_actions_to_nla"
    bl_label = "Load Actions to Rigify Rig NLA"

    @classmethod
    def poll(cls, context):
        actions = context.scene.RGE_actions_to_load
        selected_action_count = len([action for action in actions if action.selected])

        return common.find_rigify_rig() != None and selected_action_count > len(find_conflicting_action_items(context))

    def execute(self, context):
        rigify_rig = common.find_rigify_rig()
        if rigify_rig == None or rigify_rig.animation_data == None:
            return {'CANCELLED'}

        added = 0
        for action_item in context.scene.RGE_actions_to_load:
            if not action_item.selected:
                continue

            action = action_item.action
            if action is None:
                continue

            # check duplicates
            exists = False
            for track in rigify_rig.animation_data.nla_tracks:
                for strip in track.strips:
                    if strip.action == action:
                        exists = True
            if exists:
                continue

            track = rigify_rig.animation_data.nla_tracks.new()
            track.name = action.name

            strip = track.strips.new(
                action.name,
                int(action.frame_range[0]),
                action
            )

            added += 1

        self.report({'INFO'}, f"Added {added} actions to Rigify NLA")
        return {'FINISHED'}


class RGE_PT_nla_action_loader(bpy.types.Panel):
    bl_label = "NLA Action Loader"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Rigify Game Exporter"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        if common.find_rigify_rig() == None:
            box = layout.box()
            box.label(text=f"Cannot find Rigify Rig ({common.RIGIFY_RIG_NAME})", icon="ERROR")
            return

        layout.label(text="Select Actions to Load into Rigify Rig NLA")
        row = layout.row(align=True)
        row.template_list(
            "RGE_UL_action_items",
            "actions_to_load",
            scene,
            "RGE_actions_to_load",
            scene,
            "RGE_actions_to_load_index",
        )

        row = layout.row(align=True)
        row.operator("rigify_game_exporter.refresh_actions", icon="FILE_REFRESH")

        row = layout.row(align=True)
        row.operator("rigify_game_exporter.select_all_actions")
        row.operator("rigify_game_exporter.clear_selected_actions")

        layout.separator()

        filtered_actions = find_conflicting_action_items(context)
        filtered_action_count = len(filtered_actions)
        if filtered_action_count > 0:
            header, body = layout.panel("filtered_action_items_subpanel", default_closed=True)

            selected_action_item_count = len([action_item for action_item in scene.RGE_actions_to_load if action_item.selected])
            if filtered_action_count == selected_action_item_count:
                header.label(text="All Actions Already Exist in Rigify Rig NLA")
            else:
                header.label(text=f"{filtered_action_count} out of {selected_action_item_count} Actions Already Exist in Rigify Rig NLA")

            if body != None:
                for action_item in filtered_actions:
                    body.label(text=action_item.action.name, icon="ACTION")

                layout.separator()

        row = layout.row(align=True)
        row.scale_y = 2
        row.operator("rigify_game_exporter.load_actions_to_nla", icon="NLA")


classes = (
    RGE_OT_refresh_actions,
    RGE_OT_select_all_actions,
    RGE_OT_clear_selected_actions,
    RGE_OT_load_actions_to_nla,
    RGE_PT_nla_action_loader,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.RGE_actions_to_load = bpy.props.CollectionProperty(type=common.RGE_PG_action_item)
    bpy.types.Scene.RGE_actions_to_load_index = bpy.props.IntProperty()

def unregister():
    del bpy.types.Scene.RGE_actions_to_load_index
    del bpy.types.Scene.RGE_actions_to_load

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
