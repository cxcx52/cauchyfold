#!/usr/bin/env python3
"""Run the unmodified pinned upstream under Sage. Never substitutes a proxy.
Usage: sage -python run_official_estimator.py --upstream /path/lattice-estimator
"""
import argparse, contextlib, hashlib, io, json, math, platform, subprocess, sys, time, traceback
from pathlib import Path
from cf_profile import ROOT, PIN, build, dump

def run(upstream):
 out=ROOT/'evidence'/'official_estimator';out.mkdir(parents=True,exist_ok=True)
 inputs=build()['roles'];dump(out/'inputs.json',{'pin':PIN,'roles':inputs})
 env=dict(python=sys.version,platform=platform.platform(),pin=PIN,roles=17,cost_models=2)
 try:
  import sage.all as sa
  import sage.version
 except ImportError:
  env.update(status='BLOCKED_MISSING_SAGEMATH',attempted_import='sage.all',
   numerical_estimates_produced=False,error=traceback.format_exc())
  dump(out/'status.json',env);print(json.dumps(env,indent=2));return 2
 try:
  if not upstream: raise ValueError('--upstream is required')
  path=Path(upstream).resolve()
  def git(*a):return subprocess.check_output(['git','-C',str(path),*a],text=True).strip()
  if git('rev-parse','HEAD')!=PIN:raise ValueError('upstream commit mismatch')
  if git('status','--porcelain'):raise ValueError('upstream working tree is not clean')
  env.update(sage=sage.version.version,upstream=str(path),upstream_unmodified=True)
  sys.path.insert(0,str(path))
  from estimator import SIS
  from estimator.reduction import MATZOV
  def estimate(role,model):
   t=time.perf_counter();capture=io.StringIO()
   params=SIS.Parameters(n=sa.ZZ(role['d']*role['rows']),q=sa.ZZ(role['q']),
    m=sa.ZZ(role['d']*role['columns']),length_bound=sa.ZZ(role['beta']),norm=2,tag=role['matrix_id'])
   with contextlib.redirect_stdout(capture),contextlib.redirect_stderr(capture):
    costs=SIS.estimate(params,red_cost_model=MATZOV(nn=model),jobs=1,catch_exceptions=False,quiet=True)
   attacks=[]
   for name,cost in costs.items():
    rop=cost.get('rop',sa.oo);finite=rop!=sa.oo and rop>0
    exponent=float(sa.log(rop,2)) if finite else None
    finite=finite and math.isfinite(exponent)
    block=int(cost['beta']) if finite and 'beta' in cost else None
    attacks.append(dict(attack=name,fields={str(k):str(v) for k,v in cost.items()},
      log2_rop=exponent,finite=bool(finite),block_size=block,
      fit_status='EXTRAPOLATED_ABOVE_1024' if block and block>1024 else 'WITHIN_FIT_OR_UNKNOWN'))
   return dict(role=role,model=model,pin=PIN,attacks=attacks,elapsed_seconds=time.perf_counter()-t,
               captured_output=capture.getvalue(),scope='heuristic coefficient-expanded SIS attacks; not a full-node security certificate')
  reference=dict(matrix_id='original_A0_regression',q=2**48-59,d=64,rows=24,columns=1821,beta=4567851477)
  for model,expected in [('classical',255.490229),('quantum',238.730181)]:
   rec=estimate(reference,model);dump(out/f'regression_{model}.json',rec)
   finite=[a for a in rec['attacks'] if a['finite']]
   if not finite or abs(min(a['log2_rop'] for a in finite)-expected)>1e-4:
    raise ValueError('original A0 regression did not reproduce')
  results=[]
  for role in inputs:
   for model in ('classical','quantum'):
    rec=estimate(role,model);dump(out/f"{role['matrix_id']}_{model}.json",rec);results.append(rec)
  finite=all(r['attacks'] and all(a['finite'] for a in r['attacks']) for r in results)
  env.update(status='OFFICIAL_RUN_FINISHED' if finite else 'OFFICIAL_RUN_NONFINITE',numerical_estimates_produced=True,
   completed_jobs=len(results),full_computational_security_certified=False)
  dump(out/'summary.json',{'environment':env,'results':results})
 except Exception:
  env.update(status='OFFICIAL_RUN_FAILED',error=traceback.format_exc());dump(out/'status.json',env);return 1
 dump(out/'status.json',env);print(json.dumps(env,indent=2));return 0
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--upstream');a=p.parse_args();sys.exit(run(a.upstream))
