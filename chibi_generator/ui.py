"""Russian native character creator with visual presets and independent randomization."""
import json,secrets
from pathlib import Path
import bpy,bpy.utils.previews
from bpy.props import IntProperty,FloatProperty,BoolProperty,PointerProperty,StringProperty,EnumProperty,CollectionProperty
from bpy_extras.io_utils import ImportHelper,ExportHelper
from . import model,scene,studio,library

_PREVIEWS=None
FACE_LABELS={'classic':'Классическое','round':'Круглое','oval':'Овальное','heart':'Сердечком','soft_square':'Мягкое квадратное','elfin':'Эльфийское'}
MAKEUP_LABELS={'natural':'Нежный','rose':'Розовый','peach':'Персиковый','lavender':'Лавандовый','smoky':'Дымчатый','graphic':'Графические стрелки','berry':'Ягодный','teal':'Бирюзовый','sunset':'Закатный','freckles':'Веснушки'}
EXPRESSION_LABELS={'calm':'Спокойное','cheerful':'Радостное','serious':'Серьёзное','dreamy':'Мечтательное','wink':'Подмигивание'}
EYE_LABELS={'violet':'Фиолетовый','blue':'Синий','jade':'Нефритовый','amber':'Янтарный','brown':'Карий','rose':'Розовый'}
POSE_ITEMS=[(k,v['label'],v['label'],0,i) for i,(k,v) in enumerate(model.POSE_PRESETS.items())];GESTURE_ITEMS=[(k,v,v,i) for i,(k,v) in enumerate(model.GESTURES.items())]
FACE_ITEMS=[];MAKEUP_ITEMS=[];HAIR_ITEMS=[(key,cfg['label'],cfg['label'],0,i) for i,(key,cfg) in enumerate(model.HAIR_PRESETS.items())]
def asset_items(slot):return [(key,data['label'],data['label'],i) for i,(key,data) in enumerate(model.ASSETS[slot].items())]
TOP_ITEMS=asset_items('top');BOTTOM_ITEMS=asset_items('bottom');SHOE_ITEMS=asset_items('shoes');DRESS_ITEMS=asset_items('dress');LEGWEAR_ITEMS=asset_items('legwear')
PALETTE_ITEMS=[(key,label,'',i) for i,(key,label) in enumerate([('default','Цвета вещи'),('black','Чёрный / серебро'),('burgundy','Бордовый / чёрный'),('pastel','Розовый / лиловый'),('neon','Чёрный / кислотный'),('earthy','Мох / коричневый')])]
STYLE_ITEMS=[('any','Свободное сочетание','Все вещи без привязки к стилю',0)]+[(key,data['label'],'',i+1) for i,(key,data) in enumerate(model.STYLES.items())]

HAIR_COLOR_ITEMS=[(key,data[0],data[0],i) for i,(key,data) in enumerate(model.HAIR_COLORS.items())]
HAIR_PATTERN_ITEMS=[(key,label,label,i) for i,(key,label) in enumerate(model.HAIR_PATTERNS.items())]
SKIN_ITEMS=[(key,data[0],data[0],i) for i,(key,data) in enumerate(model.SKIN_TONES.items())]

def selected_style(settings):
    if settings.style_primary=='any':return {}
    if not settings.style_mixing:return {settings.style_primary:1}
    b=settings.mix_secondary/100;c=settings.mix_tertiary/100;weights={}
    for key,value in [(settings.style_primary,max(0,1-b-c)),(settings.style_secondary,b),(settings.style_tertiary,c)]:
        if key!='any':weights[key]=weights.get(key,0)+value
    return model.validate_style(weights) if weights and sum(weights.values()) else {settings.style_primary:1}

def accessory_get(key):
    def get(self):
        c=current();return key in (c.parameters['accessories'] if c else model.default_accessories())
    return get

def accessory_set(key):
    def write(self,value):
        c=current()
        if c:
            values=set(c.parameters['accessories'])
            if value:values.add(key)
            else:values.discard(key)
            c.set_accessories([k for k in model.ACCESSORY_CATALOG if k in values])
    return write

EXPRESSION_ITEMS=[(key,label,'',i) for i,(key,label) in enumerate(EXPRESSION_LABELS.items())]
EYE_ITEMS=[(key,label,'',i) for i,(key,label) in enumerate(EYE_LABELS.items())]

def current(context=None):
    context=context or bpy.context
    c=scene.active_character(context)
    if c:return c
    settings=getattr(context.scene,'chibi_settings',None);target=settings.target if settings else None
    if target and target.get('chibi_spec') and target.name in context.scene.objects:return scene.Character(target)
    return None

def focus(context,c):
    context.scene.chibi_settings.target=c.rig
    bpy.ops.object.select_all(action='DESELECT');c.rig.select_set(True);context.view_layer.objects.active=c.rig
    return c

def remember(c):c.rig['chibi_previous_spec']=json.dumps(c.parameters,ensure_ascii=False)

def refresh_library(settings):
    settings.favourites.clear()
    if not settings.library_path:return
    for entry in library.entries(bpy.path.abspath(settings.library_path)):
        item=settings.favourites.add();item.name=entry['name'];item.filepath=entry['path'];item.seed=entry['seed']
    settings.favourite_index=min(settings.favourite_index,max(0,len(settings.favourites)-1))

def default_library():
    return str(Path(bpy.utils.user_resource('DATAFILES',path='chibi_generator/presets',create=True)))

def getter(key,default=.5,scale=1):
    def get(self):
        c=current();return float((c.parameters['body'][key] if c else default)*scale)
    return get

def setter(key,scale=1):
    def set(self,value):
        c=current()
        if c:c.set_body(**{key:float(value)/scale})
    return set

def curve_get(self):
    c=current();return c is not None and c.parameters['body']['curve_severity']>0

def curve_set(self,value):
    c=current()
    if c:c.set_body(curve_severity=.65 if value else 0)

def group_get(group,key,default):
    def get(self):
        c=current();return c.parameters[group][key] if c else default
    return get

def group_set(group,key):
    def set(self,value):
        c=current()
        if c:getattr(c,'set_'+group)(**{key:value})
    return set

def enum_get(group,key,items):
    def get(self):
        c=current();value=c.parameters[group][key] if c else items[0][0]
        return next(i for i,item in enumerate(items) if item[0]==value)
    return get

def enum_set(group,key,items):
    def set(self,value):
        c=current()
        if c:getattr(c,'set_'+group)(**{key:items[value][0]})
    return set

class ChibiFavourite(bpy.types.PropertyGroup):
    filepath:StringProperty()
    seed:IntProperty()

class ChibiSettings(bpy.types.PropertyGroup):
    target:PointerProperty(type=bpy.types.Object)
    tab:EnumProperty(name='Раздел',items=[('BODY','Тело','Пропорции тела','OUTLINER_OB_ARMATURE',0),('FACE','Лицо','Форма лица и глаза','USER',1),('MAKEUP','Макияж','Косметика и веснушки','BRUSH_DATA',2),('OUTFIT','Одежда','Гардероб','MOD_CLOTH',4),('STYLE','Стиль','Стили и смешивание','COLOR',5),('ACCESSORIES','Детали','Украшения и аксессуары','SOLO_ON',6),('HAIR','Волосы','Причёски и окрашивание','CURVES_DATA',7),('SKIN','Кожа','Оттенок и подтон','SHADING_RENDERED',8),('POSE','Позы','Положение тела и жесты','ARMATURE_DATA',9),('SAVE','Мои','Избранное и сохранение','HEART',3)],default='FACE')
    pose_preset:EnumProperty(name='Поза',items=lambda self,ctx:POSE_ITEMS,get=enum_get('pose','preset',POSE_ITEMS),set=enum_set('pose','preset',POSE_ITEMS))
    pose_mirror:BoolProperty(name='Отразить позу',get=group_get('pose','mirror',False),set=group_set('pose','mirror'))
    gesture_left:EnumProperty(name='Левая кисть',items=GESTURE_ITEMS,get=enum_get('pose','left',GESTURE_ITEMS),set=enum_set('pose','left',GESTURE_ITEMS))
    gesture_right:EnumProperty(name='Правая кисть',items=GESTURE_ITEMS,get=enum_get('pose','right',GESTURE_ITEMS),set=enum_set('pose','right',GESTURE_ITEMS))
    hair_preset:EnumProperty(name='Причёска',items=lambda self,ctx:HAIR_ITEMS,get=enum_get('hair','preset',HAIR_ITEMS),set=enum_set('hair','preset',HAIR_ITEMS))
    hair_color:EnumProperty(name='Основной цвет',items=HAIR_COLOR_ITEMS,get=enum_get('hair','color',HAIR_COLOR_ITEMS),set=enum_set('hair','color',HAIR_COLOR_ITEMS))
    hair_secondary:EnumProperty(name='Второй цвет',items=HAIR_COLOR_ITEMS,get=enum_get('hair','secondary',HAIR_COLOR_ITEMS),set=enum_set('hair','secondary',HAIR_COLOR_ITEMS))
    hair_pattern:EnumProperty(name='Окрашивание',items=HAIR_PATTERN_ITEMS,get=enum_get('hair','pattern',HAIR_PATTERN_ITEMS),set=enum_set('hair','pattern',HAIR_PATTERN_ITEMS))
    skin_preset:EnumProperty(name='Оттенок',items=SKIN_ITEMS,get=enum_get('skin','preset',SKIN_ITEMS),set=enum_set('skin','preset',SKIN_ITEMS))
    skin_shade:FloatProperty(name='Светлее / темнее',min=-.25,max=.25,get=group_get('skin','shade',0.),set=group_set('skin','shade'))
    skin_undertone:FloatProperty(name='Холоднее / теплее',min=-.25,max=.25,get=group_get('skin','undertone',0.),set=group_set('skin','undertone'))
    lock_hair:BoolProperty(name='Волосы',description='Сохранить причёску и окрашивание')
    lock_skin:BoolProperty(name='Кожа',description='Сохранить оттенок кожи')
    style_hair:BoolProperty(name='Также подобрать причёску',default=False)
    style_primary:EnumProperty(name='Основной стиль',items=STYLE_ITEMS,default='goth')
    style_secondary:EnumProperty(name='Второй стиль',items=STYLE_ITEMS,default='egirl')
    style_tertiary:EnumProperty(name='Третий стиль',items=STYLE_ITEMS,default='grunge')
    style_mixing:BoolProperty(name='Смешать три стиля')
    mix_secondary:FloatProperty(name='Доля второго, %',min=0,max=100,default=20)
    mix_tertiary:FloatProperty(name='Доля третьего, %',min=0,max=100,default=10)
    style_makeup:BoolProperty(name='Также подобрать макияж',default=False)
    lock_accessories:BoolProperty(name='Детали',description='Сохранить аксессуары при случайной сборке')
    outfit_dress:EnumProperty(name='Платье',items=DRESS_ITEMS,get=enum_get('outfit','dress',DRESS_ITEMS),set=enum_set('outfit','dress',DRESS_ITEMS))
    outfit_legwear:EnumProperty(name='Колготки / гольфы',items=LEGWEAR_ITEMS,get=enum_get('outfit','legwear',LEGWEAR_ITEMS),set=enum_set('outfit','legwear',LEGWEAR_ITEMS))
    outfit_palette:EnumProperty(name='Палитра',items=PALETTE_ITEMS,get=enum_get('outfit','palette',PALETTE_ITEMS),set=enum_set('outfit','palette',PALETTE_ITEMS))
    lock_body:BoolProperty(name='Тело',description='Сохранить тело при случайной сборке')
    lock_face:BoolProperty(name='Лицо',description='Сохранить лицо при случайной сборке')
    lock_outfit:BoolProperty(name='Одежда',description='Сохранить одежду при случайной сборке')
    outfit_top:EnumProperty(name='Верх',items=TOP_ITEMS,get=enum_get('outfit','top',TOP_ITEMS),set=enum_set('outfit','top',TOP_ITEMS))
    outfit_bottom:EnumProperty(name='Низ',items=BOTTOM_ITEMS,get=enum_get('outfit','bottom',BOTTOM_ITEMS),set=enum_set('outfit','bottom',BOTTOM_ITEMS))
    outfit_shoes:EnumProperty(name='Обувь',items=SHOE_ITEMS,get=enum_get('outfit','shoes',SHOE_ITEMS),set=enum_set('outfit','shoes',SHOE_ITEMS))
    lock_makeup:BoolProperty(name='Макияж',description='Сохранить макияж при случайной сборке')
    character_name:StringProperty(name='Имя',default='Моя альтушка',maxlen=120)
    library_path:StringProperty(name='Папка избранного',subtype='DIR_PATH')
    favourites:CollectionProperty(type=ChibiFavourite)
    favourite_index:IntProperty(default=0,min=0)
    advanced:BoolProperty(name='Дополнительные настройки',default=False)
    seed:IntProperty(name='Номер образа',default=12345,min=0,max=2147483647)
    curve_chance:FloatProperty(name='Вероятность искривления, %',default=4,min=0,max=100)
    height:FloatProperty(name='Рост',min=0,max=1,get=getter('height'),set=setter('height'))
    thigh:FloatProperty(name='Объём бёдер',min=0,max=1,get=getter('thigh_size'),set=setter('thigh_size'))
    calf:FloatProperty(name='Объём икр',min=0,max=1,get=getter('calf_size'),set=setter('calf_size'))
    breast:FloatProperty(name='Размер груди',min=0,max=1,get=getter('breast_size',0),set=setter('breast_size'))
    glute:FloatProperty(name='Размер ягодиц',min=0,max=1,get=getter('glute_size'),set=setter('glute_size'))
    asymmetry:FloatProperty(name='Разница толщины ног, %',min=-10,max=10,get=getter('leg_asymmetry',0,100),set=setter('leg_asymmetry',100))
    shoulder:FloatProperty(name='Наклон плеч',min=-.02,max=.02,subtype='ANGLE',get=getter('shoulder_tilt',0),set=setter('shoulder_tilt'))
    curve:BoolProperty(name='Лёгкое искривление осанки',get=curve_get,set=curve_set)
    severity:FloatProperty(name='Выраженность',min=0,max=1,get=getter('curve_severity',0),set=setter('curve_severity'))
    face_preset:EnumProperty(name='Форма лица',items=FACE_ITEMS,get=enum_get('face','preset',FACE_ITEMS),set=enum_set('face','preset',FACE_ITEMS))
    expression:EnumProperty(name='Выражение',items=EXPRESSION_ITEMS,get=enum_get('face','expression',EXPRESSION_ITEMS),set=enum_set('face','expression',EXPRESSION_ITEMS))
    eye_color:EnumProperty(name='Цвет глаз',items=EYE_ITEMS,get=enum_get('face','eye_color',EYE_ITEMS),set=enum_set('face','eye_color',EYE_ITEMS))
    makeup_preset:EnumProperty(name='Макияж',items=MAKEUP_ITEMS,get=enum_get('makeup','preset',MAKEUP_ITEMS),set=enum_set('makeup','preset',MAKEUP_ITEMS))
    face_width:FloatProperty(name='Ширина лица',min=-1,max=1,get=group_get('face','width',0),set=group_set('face','width'))
    jaw:FloatProperty(name='Челюсть',min=-1,max=1,get=group_get('face','jaw',0),set=group_set('face','jaw'))
    cheeks:FloatProperty(name='Щёки',min=-1,max=1,get=group_get('face','cheeks',0),set=group_set('face','cheeks'))
    chin:FloatProperty(name='Длина подбородка',min=-1,max=1,get=group_get('face','chin',0),set=group_set('face','chin'))
    eye_size:FloatProperty(name='Размер глаз',min=0.86,max=1.14,get=group_get('face','eye_size',1),set=group_set('face','eye_size'))
    eye_spacing:FloatProperty(name='Расстояние между глазами',min=-1,max=1,get=group_get('face','eye_spacing',0),set=group_set('face','eye_spacing'))
    eye_tilt:FloatProperty(name='Наклон глаз',min=-1,max=1,get=group_get('face','eye_tilt',0),set=group_set('face','eye_tilt'))
    nose_width:FloatProperty(name='Ширина носа',min=-1,max=1,get=group_get('face','nose_width',0),set=group_set('face','nose_width'))
    nose_projection:FloatProperty(name='Выступ носа',min=-1,max=1,get=group_get('face','nose_projection',0),set=group_set('face','nose_projection'))
    mouth_width:FloatProperty(name='Ширина рта',min=-1,max=1,get=group_get('face','mouth_width',0),set=group_set('face','mouth_width'))
    lip_fullness:FloatProperty(name='Полнота губ',min=-1,max=1,get=group_get('face','lip_fullness',0),set=group_set('face','lip_fullness'))
    brow_height:FloatProperty(name='Высота бровей',min=-1,max=1,get=group_get('face','brow_height',0),set=group_set('face','brow_height'))
    brow_arch:FloatProperty(name='Изгиб бровей',min=-1,max=1,get=group_get('face','brow_arch',0),set=group_set('face','brow_arch'))
    makeup_intensity:FloatProperty(name='Интенсивность',min=0,max=1,get=group_get('makeup','intensity',1),set=group_set('makeup','intensity'))
    freckles:FloatProperty(name='Веснушки',min=0,max=1,get=group_get('makeup','freckles',0),set=group_set('makeup','freckles'))

class CharacterOperator:
    @classmethod
    def poll(cls,context):return current(context) is not None
    def fail(self,error):self.report({'ERROR'},str(error));return {'CANCELLED'}

class CHIBI_OT_generate(bpy.types.Operator):
    bl_idname='chibi.generate';bl_label='Создать ещё персонажа';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        s=context.scene.chibi_settings
        try:
            c=focus(context,scene.generate_character(seed=s.seed,curvature_probability=s.curve_chance/100,style_mix=selected_style(s)));studio.set_view(context,c)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}

class CHIBI_OT_random_all(bpy.types.Operator):
    bl_idname='chibi.random_all';bl_label='Случайная альтушка';bl_description='Собрать новый образ, сохраняя закреплённые части';bl_options={'REGISTER','UNDO'}
    use_seed:BoolProperty(default=False,options={'HIDDEN'})
    def execute(self,context):
        s=context.scene.chibi_settings;c=current(context);seed=s.seed if self.use_seed else secrets.randbelow(2**31)
        try:
            if c:
                locked=[g for g in model.GROUPS if getattr(s,'lock_'+g)]
                if len(locked)==len(model.GROUPS):self.report({'INFO'},'Все части закреплены. Снимите хотя бы один замок.');return {'CANCELLED'}
                remember(c);spec=c.parameters;spec['curvature_probability']=s.curve_chance/100;c.apply(model.randomize_spec(spec,seed,locked))
            else:c=scene.generate_character(seed=seed,curvature_probability=s.curve_chance/100,style_mix=selected_style(s))
            focus(context,c);s.seed=seed;studio.set_view(context,c,context.scene.get('chibi_view','hero'))
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}

class CHIBI_OT_regenerate(bpy.types.Operator):
    bl_idname='chibi.regenerate';bl_label='Повторить по номеру';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        s=context.scene.chibi_settings;c=current(context)
        try:
            if c:
                remember(c);spec=model.generate_spec(s.seed,s.curve_chance/100,style_mix=c.parameters['style'])
                spec['pose']=c.parameters['pose'];c.apply(spec);focus(context,c)
            else:c=focus(context,scene.generate_character(s.seed,s.curve_chance/100,style_mix=selected_style(s)))
            studio.set_view(context,c,context.scene.get('chibi_view','hero'))
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}

class CHIBI_OT_randomize(CharacterOperator,bpy.types.Operator):
    bl_idname='chibi.randomize';bl_label='Случайное тело';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        s=context.scene.chibi_settings;c=current(context);seed=secrets.randbelow(2**31)
        try:remember(c);c.randomize_body(seed,s.curve_chance/100);s.seed=seed;focus(context,c)
        except Exception as e:return self.fail(e)
        return {'FINISHED'}
class CHIBI_OT_randomize_face(CharacterOperator,bpy.types.Operator):
    bl_idname='chibi.randomize_face';bl_label='Случайное лицо';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        c=current(context)
        try:remember(c);c.randomize_face();focus(context,c)
        except Exception as e:return self.fail(e)
        return {'FINISHED'}
class CHIBI_OT_randomize_makeup(CharacterOperator,bpy.types.Operator):
    bl_idname='chibi.randomize_makeup';bl_label='Случайный макияж';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        c=current(context)
        try:remember(c);c.randomize_makeup();focus(context,c)
        except Exception as e:return self.fail(e)
        return {'FINISHED'}

class CHIBI_OT_randomize_outfit(CharacterOperator,bpy.types.Operator):
    bl_idname='chibi.randomize_outfit';bl_label='Случайная одежда';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        c=current(context)
        try:remember(c);c.randomize_outfit();focus(context,c)
        except Exception as e:return self.fail(e)
        return {'FINISHED'}

class CHIBI_OT_style(CharacterOperator,bpy.types.Operator):
    bl_idname='chibi.apply_style';bl_label='Собрать образ по стилю';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        c=current(context);s=context.scene.chibi_settings
        try:remember(c);c.apply(model.apply_style(c.parameters,selected_style(s),secrets.randbelow(2**31),s.style_makeup,s.style_hair));focus(context,c)
        except Exception as e:return self.fail(e)
        return {'FINISHED'}
class CHIBI_OT_accessories(CharacterOperator,bpy.types.Operator):
    bl_idname='chibi.randomize_accessories';bl_label='Случайные аксессуары';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        c=current(context)
        try:remember(c);c.randomize_accessories();focus(context,c)
        except Exception as e:return self.fail(e)
        return {'FINISHED'}

class CHIBI_OT_hair(CharacterOperator,bpy.types.Operator):
    bl_idname='chibi.randomize_hair';bl_label='Случайные волосы';bl_options={'REGISTER','UNDO'}
    color_only:BoolProperty(default=False,options={'HIDDEN'})
    def execute(self,context):
        c=current(context)
        try:remember(c);c.randomize_hair(color_only=self.color_only);focus(context,c)
        except Exception as e:return self.fail(e)
        return {'FINISHED'}
class CHIBI_OT_skin(CharacterOperator,bpy.types.Operator):
    bl_idname='chibi.randomize_skin';bl_label='Случайный оттенок кожи';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        c=current(context)
        try:remember(c);c.randomize_skin();focus(context,c)
        except Exception as e:return self.fail(e)
        return {'FINISHED'}

class CHIBI_OT_pose_reset(CharacterOperator,bpy.types.Operator):
    bl_idname='chibi.pose_reset';bl_label='Сбросить позу и жесты';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        c=current(context)
        try:remember(c);c.set_pose(**model.default_pose());focus(context,c)
        except Exception as e:return self.fail(e)
        return {'FINISHED'}
class CHIBI_OT_pose_random(CharacterOperator,bpy.types.Operator):
    bl_idname='chibi.pose_random';bl_label='Случайная поза';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        c=current(context)
        try:remember(c);c.set_pose(preset=secrets.choice(list(model.POSE_PRESETS)),mirror=bool(secrets.randbelow(2)),left='auto',right='auto');focus(context,c)
        except Exception as e:return self.fail(e)
        return {'FINISHED'}

class CHIBI_OT_snapshot(CharacterOperator,bpy.types.Operator):
    bl_idname='chibi.snapshot';bl_label='Запомнить образ';bl_description='Сохранить точку возврата перед ручными изменениями';bl_options={'UNDO'}
    def execute(self,context):remember(current(context));self.report({'INFO'},'Образ запомнен');return {'FINISHED'}
class CHIBI_OT_previous(CharacterOperator,bpy.types.Operator):
    bl_idname='chibi.previous';bl_label='Вернуть предыдущий';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return current(context) is not None and 'chibi_previous_spec' in current(context).rig
    def execute(self,context):
        c=current(context)
        try:
            previous=json.loads(c.rig['chibi_previous_spec']);remember(c);c.apply(previous);focus(context,c);context.scene.chibi_settings.seed=c.parameters['seed']
        except Exception as e:return self.fail(e)
        return {'FINISHED'}

class CHIBI_OT_view(CharacterOperator,bpy.types.Operator):
    bl_idname='chibi.view';bl_label='Ракурс';bl_options={'REGISTER','UNDO'}
    view:EnumProperty(items=[(key,key,'') for key in studio.VIEWS],default='hero')
    def execute(self,context):
        try:studio.set_view(context,current(context),self.view)
        except Exception as e:return self.fail(e)
        return {'FINISHED'}
class CHIBI_OT_workspace(CharacterOperator,bpy.types.Operator):
    bl_idname='chibi.workspace';bl_label='Развернуть студию';bl_description='Увеличить окно персонажа и включить цветной предпросмотр'
    def execute(self,context):
        try:studio.open_workspace(context,current(context))
        except Exception as e:return self.fail(e)
        return {'FINISHED'}

class CHIBI_OT_favourite_save(CharacterOperator,bpy.types.Operator):
    bl_idname='chibi.favourite_save';bl_label='В избранное';bl_description='Сохранить все параметры без замены существующих персонажей'
    def execute(self,context):
        s=context.scene.chibi_settings
        try:
            if not s.library_path:s.library_path=default_library()
            library.save(current(context).parameters,bpy.path.abspath(s.library_path),s.character_name);refresh_library(s)
        except Exception as e:return self.fail(e)
        self.report({'INFO'},'Персонаж добавлен в избранное');return {'FINISHED'}
class CHIBI_OT_favourite_refresh(bpy.types.Operator):
    bl_idname='chibi.favourite_refresh';bl_label='Обновить избранное'
    def execute(self,context):
        try:refresh_library(context.scene.chibi_settings)
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}
class CHIBI_OT_favourite_load(bpy.types.Operator):
    bl_idname='chibi.favourite_load';bl_label='Открыть персонажа';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):
        s=context.scene.chibi_settings;return len(s.favourites)>0 and s.favourite_index<len(s.favourites)
    def execute(self,context):
        s=context.scene.chibi_settings
        try:
            item=s.favourites[s.favourite_index];spec=model.load_preset(item.filepath);c=current(context)
            if c:remember(c);c.apply(spec)
            else:c=scene.generate_character(spec=spec)
            focus(context,c);s.seed=spec['seed'];s.character_name=item.name;studio.set_view(context,c,context.scene.get('chibi_view','hero'))
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}

class CHIBI_OT_save(CharacterOperator,bpy.types.Operator,ExportHelper):
    bl_idname='chibi.save_preset';bl_label='Сохранить настройки…';filename_ext='.json'
    filter_glob:StringProperty(default='*.json',options={'HIDDEN'})
    def execute(self,context):
        try:current(context).save_preset(self.filepath)
        except Exception as e:return self.fail(e)
        return {'FINISHED'}
class CHIBI_OT_load(bpy.types.Operator,ImportHelper):
    bl_idname='chibi.load_preset';bl_label='Загрузить настройки…';filename_ext='.json'
    filter_glob:StringProperty(default='*.json',options={'HIDDEN'})
    def execute(self,context):
        try:
            spec=model.load_preset(self.filepath);c=current(context)
            if c:remember(c);c.apply(spec)
            else:c=scene.generate_character(spec=spec)
            focus(context,c);context.scene.chibi_settings.seed=c.parameters['seed']
            studio.set_view(context,c,context.scene.get('chibi_view','hero'))
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'FINISHED'}
class CHIBI_OT_save_scene(CharacterOperator,bpy.types.Operator,ExportHelper):
    bl_idname='chibi.save_scene';bl_label='Сохранить сцену Blender…';filename_ext='.blend'
    filter_glob:StringProperty(default='*.blend',options={'HIDDEN'})
    def execute(self,context):
        try:bpy.ops.wm.save_as_mainfile(filepath=self.filepath)
        except Exception as e:return self.fail(e)
        return {'FINISHED'}
class CHIBI_OT_render(CharacterOperator,bpy.types.Operator,ExportHelper):
    bl_idname='chibi.render_portrait';bl_label='Сохранить картинку…';bl_description='Рендер выбранного ракурса в PNG';filename_ext='.png'
    filter_glob:StringProperty(default='*.png',options={'HIDDEN'})
    def execute(self,context):
        try:
            if not context.scene.camera:studio.set_view(context,current(context))
            context.scene.render.filepath=self.filepath;context.scene.render.image_settings.file_format='PNG'
            bpy.ops.render.render('INVOKE_DEFAULT',write_still=True)
        except Exception as e:return self.fail(e)
        return {'FINISHED'}

class CHIBI_UL_favourites(bpy.types.UIList):
    def draw_item(self,context,layout,data,item,icon,active_data,active_propname,index):layout.label(text=item.name,icon='HEART')

class CHIBI_PT_main(bpy.types.Panel):
    bl_label='АЛЬТУШКА';bl_idname='CHIBI_PT_main';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='АЛЬТУШКА'
    def draw(self,context):
        l=self.layout;l.use_property_split=False;s=context.scene.chibi_settings;c=current(context)
        l.label(text='Студия chibi-персонажей')
        row=l.row();row.scale_y=1.65;row.operator('chibi.random_all',icon='FILE_REFRESH')
        if not c:
            l.label(text='Начните со случайного образа',icon='INFO');return
        box=l.box();box.label(text='Закрепить при случайной сборке',icon='LOCKED');row=box.grid_flow(row_major=True,columns=2,even_columns=True,align=True)
        for group in model.GROUPS:row.prop(s,'lock_'+group,toggle=True,icon='LOCKED' if getattr(s,'lock_'+group) else 'UNLOCKED')
        row=l.row(align=True);row.operator('chibi.snapshot',text='Запомнить',icon='BOOKMARKS');row.operator('chibi.previous',text='Вернуть',icon='LOOP_BACK')
        l.separator();l.label(text='Собрать вручную');row=l.grid_flow(row_major=True,columns=3,even_columns=True,align=True);row.prop(s,'tab',expand=True)
        l.separator()
        if s.tab=='BODY':
            l.operator('chibi.randomize',icon='FILE_REFRESH')
            for key in ('height','breast','glute','thigh','calf','asymmetry','shoulder'):l.prop(s,key,slider=True)
            box=l.box();box.prop(s,'curve')
            if s.curve:box.prop(s,'severity',slider=True)
        elif s.tab=='POSE':
            l.operator('chibi.pose_random',icon='FILE_REFRESH');row=l.row();row.alignment='CENTER';row.template_icon_view(s,'pose_preset',show_labels=True,scale=5,scale_popup=5)
            l.prop(s,'pose_preset',text='');l.prop(s,'pose_mirror');l.prop(s,'gesture_left');l.prop(s,'gesture_right');l.operator('chibi.pose_reset',icon='LOOP_BACK')
            l.label(text='Поза сохраняется при смене образа')
        elif s.tab=='HAIR':
            l.operator('chibi.randomize_hair',icon='FILE_REFRESH');row=l.row();row.alignment='CENTER';row.template_icon_view(s,'hair_preset',show_labels=True,scale=5,scale_popup=5)
            l.prop(s,'hair_preset',text='');l.prop(s,'hair_pattern');l.prop(s,'hair_color')
            if c.parameters['hair']['pattern']!='solid':l.prop(s,'hair_secondary')
            l.operator('chibi.randomize_hair',text='Случайное окрашивание',icon='COLOR').color_only=True
        elif s.tab=='SKIN':
            l.operator('chibi.randomize_skin',icon='FILE_REFRESH');l.prop(s,'skin_preset');l.prop(s,'skin_shade',slider=True);l.prop(s,'skin_undertone',slider=True)
            l.label(text='Оттенок общий для лица и тела')
        elif s.tab=='FACE':
            l.operator('chibi.randomize_face',icon='FILE_REFRESH');row=l.row();row.alignment='CENTER';row.template_icon_view(s,'face_preset',show_labels=True,scale=5,scale_popup=5)
            l.prop(s,'face_preset',text='');l.prop(s,'expression');l.prop(s,'eye_color')
            for key in ('face_width','jaw','cheeks','chin','eye_size','eye_spacing','eye_tilt'):l.prop(s,key,slider=True)
            box=l.box();box.label(text='Нос, губы и брови')
            for key in model.FACE_DETAIL_DEFAULTS:box.prop(s,key,slider=True)
        elif s.tab=='OUTFIT':
            l.operator('chibi.randomize_outfit',icon='FILE_REFRESH')
            l.prop(s,'outfit_dress')
            box=l.column();box.enabled=c.parameters['outfit']['dress']=='none'
            for key in ('outfit_top','outfit_bottom'):box.prop(s,key)
            if c.parameters['outfit']['dress']!='none':l.label(text='Платье заменяет верх и низ')
            for key in ('outfit_shoes','outfit_legwear','outfit_palette'):l.prop(s,key)
        elif s.tab=='STYLE':
            l.prop(s,'style_primary');l.prop(s,'style_mixing')
            if s.style_mixing:
                l.prop(s,'style_secondary');l.prop(s,'mix_secondary',slider=True);l.prop(s,'style_tertiary');l.prop(s,'mix_tertiary',slider=True)
            l.prop(s,'style_makeup');l.prop(s,'style_hair');l.operator('chibi.apply_style',icon='FILE_REFRESH')
            active=c.parameters['style']
            for key,share in active.items():l.label(text=model.STYLES[key]['label']+' — '+str(round(share*100))+'%')
        elif s.tab=='ACCESSORIES':
            l.operator('chibi.randomize_accessories',icon='FILE_REFRESH');grid=l.grid_flow(row_major=True,columns=2,even_columns=True,align=True)
            for key in model.ACCESSORY_CATALOG:grid.prop(s,'accessory_'+key,toggle=True)
        elif s.tab=='MAKEUP':
            l.operator('chibi.randomize_makeup',icon='FILE_REFRESH');row=l.row();row.alignment='CENTER';row.template_icon_view(s,'makeup_preset',show_labels=True,scale=5,scale_popup=5)
            l.prop(s,'makeup_preset',text='');l.prop(s,'makeup_intensity',slider=True);l.prop(s,'freckles',slider=True)
        else:
            l.prop(s,'character_name');row=l.row();row.scale_y=1.3;row.operator('chibi.favourite_save',icon='HEART')
            l.template_list('CHIBI_UL_favourites','',s,'favourites',s,'favourite_index',rows=4)
            row=l.row(align=True);row.operator('chibi.favourite_load',icon='IMPORT');row.operator('chibi.favourite_refresh',text='',icon='FILE_REFRESH')
            l.separator();l.operator('chibi.save_scene',icon='FILE_BLEND');l.operator('chibi.render_portrait',icon='RENDER_STILL')
            row=l.row(align=True);row.operator('chibi.save_preset',text='Настройки: сохранить');row.operator('chibi.load_preset',text='Открыть')
            l.prop(s,'library_path')
        l.separator();box=l.box();box.label(text='Посмотреть персонажа',icon='VIEW_CAMERA');row=box.row(align=True)
        for key,label in [('hero','¾'),('front','Спереди'),('side','Сбоку'),('back','Сзади')]:row.operator('chibi.view',text=label).view=key
        row=box.row(align=True);row.operator('chibi.view',text='Лицо крупно',icon='ZOOM_IN').view='face';row.operator('chibi.workspace',text='Студия',icon='FULLSCREEN_ENTER')
        l.prop(s,'advanced',icon='TRIA_DOWN' if s.advanced else 'TRIA_RIGHT',emboss=False)
        if s.advanced:
            box=l.box();box.prop(s,'seed');box.prop(s,'curve_chance');box.operator('chibi.regenerate',icon='FILE_REFRESH');box.operator('chibi.generate',icon='ADD')
            box.label(text='Номер текущего образа: '+str(c.parameters['seed']))

for key in model.ACCESSORY_CATALOG:
    ChibiSettings.__annotations__['accessory_'+key]=BoolProperty(name=model.ASSETS['accessories'][key]['label'],get=accessory_get(key),set=accessory_set(key))

CLASSES=[ChibiFavourite,ChibiSettings,CHIBI_OT_generate,CHIBI_OT_random_all,CHIBI_OT_regenerate,CHIBI_OT_randomize,CHIBI_OT_randomize_face,CHIBI_OT_randomize_makeup,CHIBI_OT_randomize_outfit,CHIBI_OT_style,CHIBI_OT_accessories,CHIBI_OT_hair,CHIBI_OT_skin,CHIBI_OT_pose_reset,CHIBI_OT_pose_random,CHIBI_OT_snapshot,CHIBI_OT_previous,CHIBI_OT_view,CHIBI_OT_workspace,CHIBI_OT_favourite_save,CHIBI_OT_favourite_refresh,CHIBI_OT_favourite_load,CHIBI_OT_save,CHIBI_OT_load,CHIBI_OT_save_scene,CHIBI_OT_render,CHIBI_UL_favourites,CHIBI_PT_main]

def register():
    global _PREVIEWS
    _PREVIEWS=bpy.utils.previews.new();folder=Path(__file__).parent/'assets/previews'
    for path in folder.glob('*.png'):_PREVIEWS.load(path.stem,str(path),'IMAGE')
    FACE_ITEMS[:]=[(key,label,label,_PREVIEWS['face_'+key].icon_id if 'face_'+key in _PREVIEWS else 0,i) for i,(key,label) in enumerate(FACE_LABELS.items())]
    MAKEUP_ITEMS[:]=[(key,label,label,_PREVIEWS['makeup_'+key].icon_id if 'makeup_'+key in _PREVIEWS else 0,i) for i,(key,label) in enumerate(MAKEUP_LABELS.items())]
    HAIR_ITEMS[:]=[(key,cfg['label'],cfg['label'],_PREVIEWS['hair_'+key].icon_id if 'hair_'+key in _PREVIEWS else 0,i) for i,(key,cfg) in enumerate(model.HAIR_PRESETS.items())]
    POSE_ITEMS[:]=[(k,v['label'],v['label'],_PREVIEWS['pose_'+k].icon_id if 'pose_'+k in _PREVIEWS else 0,i) for i,(k,v) in enumerate(model.POSE_PRESETS.items())]
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.chibi_settings=PointerProperty(type=ChibiSettings)

def unregister():
    global _PREVIEWS
    if hasattr(bpy.types.Scene,'chibi_settings'):del bpy.types.Scene.chibi_settings
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
    if _PREVIEWS:bpy.utils.previews.remove(_PREVIEWS);_PREVIEWS=None
