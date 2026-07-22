import bpy

def renamed_action(name):
    # TODO hardcoded
    return name.replace("CTRL_", "")

def find_conflicting_action_items(actions):
    conflicting_actions = []
    for action_item in actions:
        if action_item.action != None:
            baked_action_name = renamed_action(action_item.action.name)

            for action in bpy.data.actions:
                if action.name == baked_action_name:
                    conflicting_actions.append(action_item)
                    break

    return conflicting_actions