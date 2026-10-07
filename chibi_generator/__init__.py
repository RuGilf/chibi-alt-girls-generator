bl_info={'name':'CHIBI CHARACTER GENERATOR','author':'Character Generator Project','version':(0,8,0),'blender':(4,2,0),'location':'View3D > Sidebar > АЛЬТУШКА','description':'Russian character creator: random or manual, visual presets and favourites','category':'Add Mesh'}
from .scene import generate_character,load_character,active_character,Character

def register():
    from . import ui
    ui.register()
def unregister():
    from . import ui
    ui.unregister()
