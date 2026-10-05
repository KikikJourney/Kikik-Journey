#!/usr/bin/env python3
import argparse,json,os,urllib.request
PROMPT="""You are Prospect Worker v1. Qualify public buyer/request evidence and match it to one supplied offer. Never invent facts. Public request is evidence, not consent. Return ONLY JSON with keys: decision,confidence,problem,buyer_type,matched_offer,priority,evidence,missing_information,reason,next_validation. decision is QUALIFIED/WATCH/REJECT; confidence and priority are 0-100 integers; matched_offer must be null or an exact supplied offer name."""
def validate_result(r,p):
 required={"decision","confidence","problem","buyer_type","matched_offer","priority","evidence","missing_information","reason","next_validation"}
 if set(r)!=required: raise ValueError("worker output keys do not match contract")
 if r["decision"] not in {"QUALIFIED","WATCH","REJECT"}: raise ValueError("invalid decision")
 for k in ("confidence","priority"):
  if not isinstance(r[k],int) or not 0<=r[k]<=100: raise ValueError("invalid "+k)
 if not isinstance(r["evidence"],list) or not isinstance(r["missing_information"],list): raise ValueError("arrays required")
 offers={x["name"] for x in p.get("offers",[])}
 if r["matched_offer"] is not None and r["matched_offer"] not in offers: raise ValueError("unknown offer")
 if r["decision"]=="QUALIFIED" and r["matched_offer"] is None: raise ValueError("qualified requires offer")
def main():
 p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output",required=True); p.add_argument("--base-url",default=os.getenv("WORKER_BASE_URL","http://127.0.0.1:8080")); p.add_argument("--model",default=os.getenv("WORKER_MODEL","ggml-org/Qwen3-1.7B-GGUF:Q4_K_M")); a=p.parse_args()
 payload=json.load(open(a.input,encoding="utf-8"))
 body={"model":a.model,"temperature":0,"max_tokens":700,"messages":[{"role":"system","content":PROMPT},{"role":"user","content":json.dumps(payload,ensure_ascii=False)}]}
 req=urllib.request.Request(a.base_url.rstrip("/")+"/v1/chat/completions",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=180) as resp: data=json.load(resp)
 content=data["choices"][0]["message"]["content"].strip()
 if content.startswith("```"): content=content.split("\n",1)[1].rsplit("```",1)[0].strip()
 result=json.loads(content); validate_result(result,payload)
 with open(a.output,"w",encoding="utf-8") as f: json.dump(result,f,ensure_ascii=False,indent=2); f.write("\n")
 print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__": main()