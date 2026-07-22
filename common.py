import bpy


RIGIFY_RIG_NAME = "CTRL_rig"
GAME_RIG_NAME = "rig"

def find_rigify_rig():
    object = bpy.data.objects.get(RIGIFY_RIG_NAME)

    if object == None or object.type != 'ARMATURE':
        return None

    return object

def find_game_rig():
    object = bpy.data.objects.get(GAME_RIG_NAME)

    if object == None or object.type != 'ARMATURE':
        return None

    return object

def renamed_action(name):
    return name.replace("CTRL_", "")

def find_conflicting_action_items(actions):
    conflicting_actions = []
    for action_item in actions:
        if action_item.action != None and action_item.selected:
            baked_action_name = renamed_action(action_item.action.name)

            for action in bpy.data.actions:
                if action.name == baked_action_name:
                    conflicting_actions.append(action_item)
                    break

    return conflicting_actions

class RGE_PG_action_item(bpy.types.PropertyGroup):
    action: bpy.props.PointerProperty(name="Action", type=bpy.types.Action)
    selected: bpy.props.BoolProperty(default=True)

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


classes = [
    RGE_PG_action_item,
    RGE_UL_action_items,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
