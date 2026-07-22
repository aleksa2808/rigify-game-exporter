from . import nla_action_loader
from . import game_rig_generator


modules = ( 
    nla_action_loader,
    game_rig_generator,
)

def register():
    for module in modules:
        module.register()

def unregister():
    for module in reversed(modules):
        module.unregister()
