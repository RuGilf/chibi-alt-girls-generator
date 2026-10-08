"""Deterministic adult chibi body, face and cosmetics; no Blender dependency."""
import copy,hashlib,json,math,random,secrets
from pathlib import Path
BODY_KEYS=('height','thigh_size','calf_size','leg_asymmetry','shoulder_tilt','curve_severity','curve_direction','breast_size','glute_size')
CURVATURE_CHANCE=.04
CONFIG=Path(__file__).resolve().parent/'config'
ASSETS=json.loads((CONFIG/'assets.json').read_text(encoding='utf8'))
STYLES=json.loads((CONFIG/'styles.json').read_text(encoding='utf8'))
PALETTES=('default','black','burgundy','pastel','neon','earthy')
OUTFIT_CATALOG={key:tuple(ASSETS[key]) for key in ('top','bottom','shoes','dress','legwear')}
OUTFIT_CATALOG['palette']=PALETTES
ACCESSORY_CATALOG=tuple(ASSETS['accessories'])
GROUPS=('body','face','makeup','outfit','accessories','hair','skin')

HAIR_CONFIG=json.loads((CONFIG/'hair.json').read_text(encoding='utf8'))
HAIR_PRESETS=HAIR_CONFIG['presets']
HAIR_COLORS={
 'ink':('Чернильный',(.021,.017,.039)), 'black':('Чёрный',(.009,.007,.013)),
 'chestnut':('Каштановый',(.12,.045,.025)), 'auburn':('Рыжеватый',(.30,.075,.025)),
 'copper':('Медный',(.50,.16,.055)), 'honey':('Медовый',(.57,.35,.12)),
 'blonde':('Блонд',(.75,.60,.36)), 'silver':('Серебристый',(.42,.46,.52)),
 'white':('Белый',(.78,.80,.82)), 'burgundy':('Бордовый',(.16,.012,.035)),
 'red':('Красный',(.50,.025,.045)), 'pink':('Розовый',(.65,.13,.30)),
 'lilac':('Лиловый',(.36,.17,.55)), 'orchid':('Орхидея',(.27,.085,.39)),
 'cyan':('Голубой',(.025,.40,.52)), 'teal':('Изумрудный',(.016,.28,.19)),
 'acid':('Кислотный',(.28,.60,.03)), 'blue':('Синий',(.035,.09,.43))}
HAIR_PATTERNS={'solid':'Однотонные','streaks':'Цветные пряди','split':'Split-dye','ombre':'Омбре','dipped':'Цветные кончики'}
SKIN_TONES={
 'porcelain':('Фарфоровый',(.86,.67,.59)), 'ivory':('Светлый',(.76,.51,.40)),
 'peach':('Персиковый',(.66,.36,.265)), 'sand':('Песочный',(.57,.335,.205)),
 'honey':('Медовый',(.48,.275,.13)), 'olive':('Оливковый',(.39,.285,.155)),
 'tan':('Загорелый',(.34,.165,.085)), 'caramel':('Карамельный',(.265,.115,.055)),
 'copper':('Тёплый коричневый',(.205,.080,.040)), 'umber':('Коричневый',(.135,.052,.030)),
 'espresso':('Глубокий коричневый',(.080,.029,.019)), 'ebony':('Тёмный',(.045,.018,.012))}

def default_hair():return dict(preset='bob',color='ink',secondary='orchid',pattern='streaks')
def default_skin():return dict(preset='peach',shade=0.,undertone=0.)
def skin_rgb(skin):
    rgb=SKIN_TONES[skin['preset']][1];light=2**(skin['shade']*1.2);warm=skin['undertone']
    return tuple(max(.001,min(.98,v*light*f)) for v,f in zip(rgb,(1+.20*warm,1+.025*warm,1-.22*warm)))
def hair_weights(style):
    style=validate_style(style or {})
    if not style:return {key:1 for key in HAIR_PRESETS}
    out={}
    for key,share in style.items():
        weights=HAIR_CONFIG['style_weights'][key];total=sum(weights.values())
        for name,w in weights.items():out[name]=out.get(name,0)+share*w/total
    return out

def sample_hair(seed,style=None):
    r=group_rng(seed,'Hair');weights=hair_weights(style);preset=r.choices(list(weights),weights=list(weights.values()))[0]
    natural=['black','ink','chestnut','auburn','copper','honey','blonde','silver']
    bright=['pink','lilac','cyan','red','teal','acid','blue','white','orchid']
    style=validate_style(style or {});neon=sum(v for k,v in style.items() if k in ('cyber','scene','pastel','egirl','yami','visual'))
    color=r.choice(bright if r.random()<.20+.50*neon else natural)
    secondary=r.choice([k for k in HAIR_COLORS if k!=color]);pattern=r.choices(list(HAIR_PATTERNS),weights=[4,4,2,3,2])[0]
    return dict(preset=preset,color=color,secondary=secondary,pattern=pattern)
def sample_skin(seed):
    r=group_rng(seed,'Skin');return dict(preset=r.choice(list(SKIN_TONES)),shade=r.uniform(-.08,.08),undertone=r.uniform(-.18,.18))
def update_hair(spec,**values):
    out=validate(spec)
    if set(values)-set(default_hair()):raise ValueError('Unknown hair parameter')
    out['hair'].update(values);return validate(out)
def update_skin(spec,**values):
    out=validate(spec)
    if set(values)-set(default_skin()):raise ValueError('Unknown skin parameter')
    out['skin'].update(values);return validate(out)

def default_outfit():return dict(top='classic',bottom='pleated',shoes='boots',dress='none',legwear='tights',palette='default')
def default_accessories():return ['choker','earring','hairclip','waistchain']
def validate_style(style):
    if not isinstance(style,dict) or set(style)-set(STYLES):raise ValueError('Unknown style')
    if not style:return {}
    if any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or v<0 for v in style.values()) or sum(style.values())<=0:raise ValueError('Invalid style weights')
    total=sum(style.values());return {k:v/total for k,v in style.items() if v>0}
def style_weights(style,slot):
    style=validate_style(style)
    if not style:
        if slot=='dress':return {'none':20,**{k:1 for k in ASSETS['dress'] if k!='none'}}
        return {k:1 for k in OUTFIT_CATALOG[slot]}
    out={}
    for key,share in style.items():
        weights=STYLES[key]['weights'][slot];total=sum(weights.values())
        for asset,w in weights.items():out[asset]=out.get(asset,0)+share*w/total
    return out

def sample_outfit(seed,style=None):
    r=group_rng(seed,'OutfitV2');style=style or {}
    return {slot:r.choices(list(w),weights=list(w.values()))[0] for slot in OUTFIT_CATALOG for w in [style_weights(style,slot)]}
def sample_accessories(seed,style=None):
    r=group_rng(seed,'Accessories');style=validate_style(style or {})
    probs={k:.22 for k in ACCESSORY_CATALOG} if not style else {k:sum(share*STYLES[s]['accessories'].get(k,0) for s,share in style.items()) for k in ACCESSORY_CATALOG}
    out=[k for k,p in probs.items() if r.random()<p]
    # Avoid overlapping pendants and masks over glasses in automatic combinations.
    pendants=[k for k in out if k in ('cross','cameo','moon','crystal')]
    if len(pendants)>1:
        chosen=r.choice(pendants);out=[k for k in out if k not in pendants or k==chosen]
    if 'mask' in out and 'glasses' in out:out.remove('glasses')
    return out

def update_outfit(spec,**values):
    out=validate(spec)
    if set(values)-set(OUTFIT_CATALOG):raise ValueError('Unknown outfit slot')
    out['outfit'].update(values);return validate(out)
def update_accessories(spec,values):
    out=validate(spec);out['accessories']=list(values);return validate(out)
def apply_style(spec,style,seed=None,include_makeup=False,include_hair=False):
    out=validate(spec);style=validate_style(style);seed=out['seed'] if seed is None else seed
    out['style']=style;out['outfit']=sample_outfit(seed,style);out['accessories']=sample_accessories(seed,style)
    out['outfit_seed']=seed;out['accessories_seed']=seed
    if include_makeup:out['makeup']=sample_style_makeup(seed,style)
    if include_hair:out['hair']=sample_hair(seed,style);out['hair_seed']=seed
    return validate(out)
def sample_style_makeup(seed,style):
    if not style:return sample_makeup(seed)
    r=group_rng(seed,'StyleMakeup');weights={}
    for key,share in validate_style(style).items():
        for makeup in STYLES[key]['makeup']:weights[makeup]=weights.get(makeup,0)+share/len(STYLES[key]['makeup'])
    name=r.choices(list(weights),weights=list(weights.values()))[0]
    return dict(preset=name,intensity=r.uniform(.82,1),freckles=MAKEUP_PRESETS[name][-1])


FACE_PRESETS={
 'classic':('Classic',dict(width=0,jaw=0,cheeks=0,chin=0,eye_size=1,eye_spacing=0,eye_tilt=0)),
 'round':('Round',dict(width=.35,jaw=.30,cheeks=.65,chin=-.55,eye_size=1.07,eye_spacing=.20,eye_tilt=-.12)),
 'oval':('Oval',dict(width=-.40,jaw=-.20,cheeks=-.15,chin=.65,eye_size=.94,eye_spacing=-.12,eye_tilt=.12)),
 'heart':('Heart',dict(width=.12,jaw=-.65,cheeks=.25,chin=.35,eye_size=1.04,eye_spacing=.12,eye_tilt=.28)),
 'soft_square':('Soft square',dict(width=.15,jaw=.75,cheeks=-.20,chin=.20,eye_size=.96,eye_spacing=.10,eye_tilt=-.08)),
 'elfin':('Elfin',dict(width=-.20,jaw=-.40,cheeks=.50,chin=.15,eye_size=1.02,eye_spacing=-.25,eye_tilt=.65)),
}
# Colours are linear RGB, matching the approved Blender asset.
MAKEUP_PRESETS={
 'natural':('Natural',(.32,.16,.13),.08,(.70,.22,.20),.14,(.40,.11,.12),.20,.75,0),
 'rose':('Rose',(.48,.12,.22),.32,(.84,.16,.22),.36,(.55,.055,.12),.65,1,.15),
 'peach':('Peach',(.65,.25,.09),.30,(.92,.24,.12),.28,(.66,.15,.10),.52,.65,.25),
 'lavender':('Lavender',(.28,.075,.48),.44,(.77,.12,.29),.24,(.39,.055,.27),.60,1.3,0),
 'smoky':('Smoky',(.035,.018,.065),.64,(.55,.13,.18),.16,(.22,.035,.11),.75,1.6,0),
 'graphic':('Graphic',(.24,.055,.39),.20,(.70,.15,.29),.20,(.43,.035,.23),.72,2.1,0),
 'berry':('Berry',(.30,.035,.13),.40,(.65,.055,.17),.30,(.19,.012,.055),.90,1.25,.1),
 'teal':('Teal',(.025,.31,.28),.52,(.70,.18,.17),.18,(.38,.10,.11),.48,1.5,0),
 'sunset':('Sunset',(.72,.15,.05),.42,(.91,.18,.12),.30,(.61,.055,.06),.72,1.2,.1),
 'freckles':('Freckles',(.42,.22,.12),.08,(.84,.22,.14),.26,(.49,.16,.12),.26,.45,1),
}
EYE_COLORS={'violet':(.49,.14,.65),'blue':(.055,.29,.62),'jade':(.045,.42,.25),'amber':(.60,.28,.035),'brown':(.23,.10,.045),'rose':(.58,.10,.28)}
EXPRESSIONS=('calm','cheerful','serious','dreamy','wink')
FACE_DETAIL_DEFAULTS=dict(nose_width=0.,nose_projection=0.,mouth_width=0.,lip_fullness=0.,brow_height=0.,brow_arch=0.)
FACE_DETAILS={
 'classic':(0,0,0,0,0,0), 'round':(-.25,-.20,.10,.40,.18,-.20),
 'oval':(-.20,.32,-.05,.05,.10,.35), 'heart':(-.12,.08,.22,.30,.16,.28),
 'soft_square':(.40,.20,.30,-.12,-.08,-.20), 'elfin':(-.35,.25,-.20,.12,.22,.50)}
for _key,_values in FACE_DETAILS.items():
    FACE_PRESETS[_key][1].update(dict(zip(FACE_DETAIL_DEFAULTS,_values)))
FACE_LIMITS={'width':(-1,1),'jaw':(-1,1),'cheeks':(-1,1),'chin':(-1,1),'eye_size':(.86,1.14),'eye_spacing':(-1,1),'eye_tilt':(-1,1),**{k:(-1,1) for k in FACE_DETAIL_DEFAULTS}}

def default_face():
    return dict(FACE_PRESETS['classic'][1],preset='classic',expression='calm',eye_color='violet')
def default_makeup():
    return dict(preset='natural',intensity=1.0,freckles=0.0)
def group_rng(seed,group):
    sample_body(seed,0) # Validate with the same seed contract.
    return random.Random(int.from_bytes(hashlib.sha256(f'Chibi{group}V1:{seed}'.encode()).digest()[:8],'big'))
def sample_face(seed):
    r=group_rng(seed,'Face');name=r.choice(list(FACE_PRESETS));out=dict(FACE_PRESETS[name][1])
    for k in FACE_LIMITS:
        if k in FACE_DETAIL_DEFAULTS:continue
        lo,hi=FACE_LIMITS[k];out[k]=max(lo,min(hi,out[k]+r.uniform(-.055,.055)))
    # Keep old seeded eye colors and expressions stable; new details have their own stream.
    expression=r.choice(EXPRESSIONS[:4]);eye_color=r.choice(list(EYE_COLORS));detail=group_rng(seed,'FaceDetails')
    for k in FACE_DETAIL_DEFAULTS:out[k]=max(-1,min(1,out[k]+detail.uniform(-.18,.18)))
    return dict(out,preset=name,expression=expression,eye_color=eye_color)
def sample_makeup(seed):
    r=group_rng(seed,'Makeup');name=r.choice(list(MAKEUP_PRESETS))
    return dict(preset=name,intensity=r.uniform(.82,1),freckles=MAKEUP_PRESETS[name][-1])
def update_face(spec,preset=None,**values):
    out=validate(copy.deepcopy(spec))
    if preset is not None:
        if preset not in FACE_PRESETS:raise ValueError('Unknown face preset')
        out['face'].update(FACE_PRESETS[preset][1]);out['face']['preset']=preset
    if set(values)-set(FACE_LIMITS)-{'expression','eye_color'}:raise ValueError('Unknown face parameter')
    out['face'].update(values);return validate(out)
def update_makeup(spec,preset=None,**values):
    out=validate(copy.deepcopy(spec))
    if preset is not None:
        if preset not in MAKEUP_PRESETS:raise ValueError('Unknown makeup preset')
        out['makeup'].update(preset=preset,intensity=1.0,freckles=MAKEUP_PRESETS[preset][-1])
    if set(values)-{'intensity','freckles'}:raise ValueError('Unknown makeup parameter')
    out['makeup'].update(values);return validate(out)

def _rng(seed):
    value=int.from_bytes(hashlib.sha256(f'ChibiBodyV1:{seed}'.encode()).digest()[:8],'big')
    return random.Random(value)

def sample_body(seed,curvature_probability=CURVATURE_CHANCE):
    if isinstance(seed,bool) or not isinstance(seed,int) or not 0<=seed<2**31:raise ValueError('Seed must be an integer between 0 and 2147483647')
    if not isinstance(curvature_probability,(int,float)) or not math.isfinite(curvature_probability) or not 0<=curvature_probability<=1:raise ValueError('Curvature probability must be 0..1')
    r=_rng(seed)
    def bounded(mean,sd,lo,hi):return max(lo,min(hi,r.gauss(mean,sd)))
    height=bounded(.5,.19,.05,.95);thigh=bounded(.5,.19,.05,.95)
    calf=max(.10,min(.90,.5+.32*(thigh-.5)+r.gauss(0,.12)))
    asymmetry=bounded(0,.032,-.085,.085)
    # A minute but nonzero visual asymmetry is normal; the direction is seeded.
    if abs(asymmetry)<.006:asymmetry=.006 if asymmetry>=0 else -.006
    shoulder=bounded(0,.006,-.014,.014)
    curved=r.random()<curvature_probability
    severity=r.uniform(.48,.85) if curved else 0.0
    direction=r.choice([-1,1])
    breast=bounded(.5,.18,.05,.95);glute=bounded(.5,.18,.05,.95)
    return {'height':height,'thigh_size':thigh,'calf_size':calf,'leg_asymmetry':asymmetry,'shoulder_tilt':shoulder,'curve_severity':severity,'curve_direction':direction,'breast_size':breast,'glute_size':glute}

def generate_spec(seed=None,curvature_probability=CURVATURE_CHANCE,style=None,style_mix=None):
    if seed is None:seed=secrets.randbelow(2**31)
    style=validate_style(style_mix if style_mix is not None else ({style:1} if style else {}))
    return {'schema_version':1,'generator_version':'0.9.1','seed':seed,'age':25,'curvature_probability':curvature_probability,'body':sample_body(seed,curvature_probability),'appearance':'approved_orchid_bob_v1','face':sample_face(seed),'makeup':sample_style_makeup(seed,style),'outfit':sample_outfit(seed,style),'accessories':sample_accessories(seed,style),'style':style,'hair':sample_hair(seed,style),'skin':sample_skin(seed),'pose':default_pose()}

def validate(spec):
    if not isinstance(spec,dict) or spec.get('schema_version')!=1:raise ValueError('Unsupported chibi preset version')
    seed=spec.get('seed')
    if isinstance(seed,bool) or not isinstance(seed,int) or not 0<=seed<2**31:raise ValueError('Invalid seed')
    age=spec.get('age')
    if not isinstance(age,(int,float)) or not math.isfinite(age) or age<18:raise ValueError('Adult characters only')
    probability=spec.get('curvature_probability')
    if not isinstance(probability,(int,float)) or not math.isfinite(probability) or not 0<=probability<=1:raise ValueError('Invalid curvature probability')
    spec=copy.deepcopy(spec)
    body=spec.get('body',{})
    if not isinstance(body,dict):raise ValueError('Invalid body group')
    body.setdefault('breast_size',0.0);body.setdefault('glute_size',.5)
    limits={'height':(0,1),'thigh_size':(0,1),'calf_size':(0,1),'leg_asymmetry':(-.10,.10),'shoulder_tilt':(-.02,.02),'curve_severity':(0,1),'curve_direction':(-1,1),'breast_size':(0,1),'glute_size':(0,1)}
    for k,(lo,hi) in limits.items():
        v=body.get(k)
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError(f'Invalid body parameter: {k}')
    if body['curve_direction'] not in (-1,1):raise ValueError('curve_direction must be -1 or 1')
    spec=copy.deepcopy(spec)
    spec.setdefault('face',default_face());spec.setdefault('makeup',default_makeup())
    face=spec['face'];makeup=spec['makeup']
    if not isinstance(face,dict) or not isinstance(makeup,dict):raise ValueError('Invalid face or makeup group')
    for key,value in FACE_DETAIL_DEFAULTS.items():face.setdefault(key,value)
    for key,(lo,hi) in FACE_LIMITS.items():
        value=face.get(key)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not lo<=value<=hi:raise ValueError('Invalid face parameter: '+key)
    if face.get('preset') not in FACE_PRESETS or face.get('expression') not in EXPRESSIONS or face.get('eye_color') not in EYE_COLORS:raise ValueError('Invalid face selection')
    if makeup.get('preset') not in MAKEUP_PRESETS:raise ValueError('Invalid makeup selection')
    for key in ('intensity','freckles'):
        value=makeup.get(key)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=1:raise ValueError('Invalid makeup parameter: '+key)
    spec.setdefault('outfit',default_outfit())
    if not isinstance(spec['outfit'],dict):raise ValueError('Invalid outfit group')
    for k,v in default_outfit().items():spec['outfit'].setdefault(k,v)
    if set(spec['outfit'])!=set(OUTFIT_CATALOG):raise ValueError('Invalid outfit slots')
    for slot,options in OUTFIT_CATALOG.items():
        if spec['outfit'][slot] not in options:raise ValueError('Invalid outfit selection: '+slot)
    spec.setdefault('accessories',default_accessories());spec.setdefault('style',{})
    if not isinstance(spec['accessories'],list) or any(k not in ACCESSORY_CATALOG for k in spec['accessories']) or len(set(spec['accessories']))!=len(spec['accessories']):raise ValueError('Invalid accessories')
    spec.setdefault('hair',default_hair());spec.setdefault('skin',default_skin())
    hair=spec['hair'];skin=spec['skin']
    if not isinstance(hair,dict) or set(hair)!=set(default_hair()):raise ValueError('Invalid hair group')
    for k,options in [('preset',HAIR_PRESETS),('color',HAIR_COLORS),('secondary',HAIR_COLORS),('pattern',HAIR_PATTERNS)]:
        if not isinstance(hair[k],str) or hair[k] not in options:raise ValueError('Invalid hair '+k)
    if not isinstance(skin,dict) or set(skin)!=set(default_skin()) or not isinstance(skin['preset'],str) or skin['preset'] not in SKIN_TONES:raise ValueError('Invalid skin group')
    for k in ('shade','undertone'):
        v=skin[k]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not -.25<=v<=.25:raise ValueError('Invalid skin '+k)
    spec.setdefault('pose',default_pose());pose=spec['pose']
    if not isinstance(pose,dict) or set(pose)!=set(default_pose()):raise ValueError('Invalid pose group')
    if not isinstance(pose['preset'],str) or pose['preset'] not in POSE_PRESETS or not isinstance(pose['mirror'],bool):raise ValueError('Invalid pose selection')
    if any(not isinstance(pose[k],str) or pose[k] not in GESTURES for k in ('left','right')):raise ValueError('Invalid hand gesture')
    spec['style']=validate_style(spec['style'])
    return spec

def update_body(spec,**values):
    out=copy.deepcopy(spec)
    for k,v in values.items():
        if k not in BODY_KEYS:raise ValueError(k)
        out['body'][k]=v
    return validate(out)

def save_preset(spec,path):
    spec=validate(spec);p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf8')
def load_preset(path):
    p=Path(path)
    if p.stat().st_size>1024*1024:raise ValueError('Preset is too large')
    return validate(json.loads(p.read_text(encoding='utf8')))


def randomize_spec(spec,seed=None,locked=()):
    """Randomize unlocked groups while preserving the others byte for byte."""
    out=validate(spec);locked=set(locked)
    if locked-set(GROUPS):raise ValueError('Unknown locked group')
    if len(locked)==len(GROUPS):return out
    fresh=generate_spec(seed,out['curvature_probability'],style_mix=out['style'])
    for group in GROUPS:
        if group not in locked:out[group]=fresh[group];out[group+'_seed']=fresh['seed']
    out['seed']=fresh['seed'];out['generator_version']='0.9.1';return validate(out)


POSE_PRESETS=json.loads((Path(__file__).parent/'config/poses.json').read_text(encoding='utf8'))['presets']
GESTURES={'auto':'По позе','open':'Открытая ладонь','relaxed':'Расслабленная','fist':'Кулак','peace':'Победа ✌','rock':'Рок-жест','point':'Указать пальцем'}
def default_pose():return dict(preset='neutral',mirror=False,left='auto',right='auto')
def update_pose(spec,**values):
    out=validate(spec)
    if set(values)-set(default_pose()):raise ValueError('Unknown pose parameter')
    out['pose'].update(values);return validate(out)
