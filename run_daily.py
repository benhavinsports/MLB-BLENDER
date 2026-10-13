import argparse,datetime,json
from pathlib import Path
from nhl_data import get_schedule,get_bundle
from engine import run_slate
p=argparse.ArgumentParser();p.add_argument('--date',default=datetime.datetime.now(datetime.timezone.utc).date().isoformat());p.add_argument('--mode',choices=['projected','confirmed'],default='projected');p.add_argument('--history',type=int,default=8);p.add_argument('--out',default='runs');a=p.parse_args()
games=get_schedule(a.date);bundles=[get_bundle(g) for g in games];report=run_slate(bundles,a.mode,a.history);report['slateDate']=a.date
out=Path(a.out);out.mkdir(parents=True,exist_ok=True);path=out/f'nhl_blender_{a.date}_{a.mode}.json';path.write_text(json.dumps(report,indent=2),encoding='utf-8');print(f'{path} | games={len(games)} | run={report["runId"]}')
