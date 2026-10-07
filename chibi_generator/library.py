"""User-owned JSON favourites, with non-overwriting filenames."""
import json,re,uuid
from datetime import datetime,timezone
from pathlib import Path
from . import model

def save(spec,folder,name):
    folder=Path(folder).expanduser();folder.mkdir(parents=True,exist_ok=True)
    name=name.strip() or 'Моя альтушка'
    if len(name)>120:raise ValueError('Название слишком длинное')
    safe=re.sub(r'[^\w-]+','_',name,flags=re.UNICODE).strip('_')[:48] or 'character'
    result=model.validate(spec);result['character_name']=name;result['saved_at']=datetime.now(timezone.utc).isoformat()
    path=folder/f'{safe}_{uuid.uuid4().hex[:10]}.json';model.save_preset(result,path);return path

def entries(folder):
    folder=Path(folder).expanduser()
    if not folder.exists():return []
    result=[]
    for path in sorted(folder.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True):
        try:
            spec=model.load_preset(path)
            result.append({'name':spec.get('character_name',path.stem),'path':str(path),'seed':spec['seed']})
        except (ValueError,TypeError,KeyError,OSError,json.JSONDecodeError):continue
    return result
