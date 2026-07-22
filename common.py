import bpy


# TODO hardcoded
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
