import base64,json,os,time
from datetime import datetime,timezone
import requests
API="https://api.github.com"; S=requests.Session()
S.headers.update({"Accept":"application/vnd.github+json","User-Agent":"KikikJourney-AI-Opportunity-Radar/1.0"})
if os.getenv("GITHUB_TOKEN"): S.headers["Authorization"]="Bearer "+os.environ["GITHUB_TOKEN"]
QUERIES=["topic:artificial-intelligence pushed:>2026-09-01 stars:>50","topic:llm pushed:>2026-09-01 stars:>50","topic:automation pushed:>2026-09-01 stars:>50","topic:ai-agents pushed:>2026-09-01 stars:>30"]
PAIN={"difficult":3,"hard":3,"broken":4,"error":2,"setup":2,"install":1,"deploy":3,"deployment":3,"integration":2,"documentation":2,"slow":2,"expensive":3,"alternative":2,"feature request":3}
def api(path,params=None):
 r=S.get(API+path,params=params or {},timeout=20); r.raise_for_status(); return r.json()
def pain(text):
 t=(text or "").lower(); return sum(v for k,v in PAIN.items() if k in t)
def license_state(r):
 spdx=(r.get("license") or {}).get("spdx")
 return "PERMISSIVE:"+spdx if spdx in {"MIT","Apache-2.0","BSD-2-Clause","BSD-3-Clause"} else "REVIEW_REQUIRED:"+str(spdx or "UNKNOWN")
def score(r,readme):
 stars=r.get("stargazers_count",0); forks=r.get("forks_count",0); issues=r.get("open_issues_count",0)
 interest=min(30,(stars**0.5)*1.8)+min(12,(forks**0.5)*1.2)
 return round(min(100,interest+min(25,issues*.7+pain(readme))+(15 if not r.get("homepage") else 7)+10+(8 if license_state(r).startswith("PERMISSIVE:") else 0)),2)
def main():
 repos={}
 for q in QUERIES:
  for r in api("/search/repositories",{"q":q,"sort":"updated","order":"desc","per_page":20}).get("items",[]): repos[r["full_name"]]=r
 out=[]
 for name,r in repos.items():
  readme=""
  try: readme=base64.b64decode(api(f"/repos/{name}/readme").get("content","")).decode("utf-8","ignore")[:12000]
  except Exception: pass
  out.append({"full_name":name,"url":r.get("html_url"),"description":r.get("description"),"stars":r.get("stargazers_count",0),"forks":r.get("forks_count",0),"open_issues":r.get("open_issues_count",0),"language":r.get("language"),"topics":r.get("topics",[]),"updated_at":r.get("pushed_at"),"license":license_state(r),"homepage":r.get("homepage"),"score":score(r,readme),"business_hypotheses":["Paid implementation/integration service","Audit or diagnostic around setup/workflow pain","Hosted convenience layer where licensing permits"]})
  time.sleep(.05)
 out.sort(key=lambda x:x["score"],reverse=True)
 report={"generated_at":datetime.now(timezone.utc).isoformat(),"method":"public GitHub metadata + README heuristics","warning":"Prioritization only; not proof of demand or revenue.","candidates":out[:30]}
 with open("opportunity_report.json","w",encoding="utf-8") as f: json.dump(report,f,indent=2,ensure_ascii=False)
 print(json.dumps({"candidates":len(out),"top":[(x["full_name"],x["score"]) for x in out[:10]]},indent=2))
if __name__=="__main__": main()
