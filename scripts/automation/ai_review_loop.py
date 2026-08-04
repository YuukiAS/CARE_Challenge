#!/usr/bin/env python3
"""No-API ChatGPT review -> Codex repair loop helper."""
from __future__ import annotations

import argparse, fcntl, hashlib, json, os, re, shlex, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

SCHEMA = "AI_REVIEW_LOOP_V1"
KEYWORD = "AI_REVIEW_READY_V1"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TASK_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,79}$")
STATES = {
    "DISABLED", "AWAITING_IMPLEMENTATION", "WAITING_FOR_GPT_REVIEW",
    "GPT_REVIEW_REVISE", "CODEX_REPAIR_RUNNING", "GPT_REVIEW_PASS",
    "AWAIT_HUMAN_DECISION", "STOPPED_STUCK", "STOPPED_DEADLINE",
    "STOPPED_MAX_ROUNDS", "SMOKE_PASS"
}

class LoopError(RuntimeError):
    pass

def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LoopError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise LoopError(f"JSON root must be object: {path}")
    return data

def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True); f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)

def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""): h.update(block)
    return h.hexdigest()

def sha_json(data) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def git(repo: Path, *args: str, check: bool = True) -> str:
    p = subprocess.run(["git", *args], cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode:
        raise LoopError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout.strip()

def task_id(value: str) -> str:
    if not TASK_RE.fullmatch(value): raise LoopError("invalid task id")
    return value

def commit_sha(repo: Path, value: str) -> str:
    if not SHA_RE.fullmatch(value): raise LoopError(f"invalid commit SHA: {value}")
    git(repo, "cat-file", "-e", f"{value}^{{commit}}")
    return value

def rel(repo: Path, path: Path) -> str:
    try: return str(path.resolve().relative_to(repo.resolve()))
    except ValueError as exc: raise LoopError(f"path outside repo: {path}") from exc

def task_dir(repo: Path, tid: str) -> Path:
    return repo / "automation/ai_review_loop/tasks" / task_id(tid)

def round_dir(repo: Path, tid: str, rnd: int) -> Path:
    return repo / "results/ai_review_loop" / tid / f"round_{rnd:03d}"

def fingerprint(repo: Path, patterns: list[str]) -> tuple[str, list[dict[str, str]]]:
    rows, seen = [], set()
    for pattern in patterns:
        if pattern.startswith("/") or ".." in Path(pattern).parts: raise LoopError(f"unsafe pattern: {pattern}")
        matches = [p.resolve() for p in repo.glob(pattern) if p.is_file()]
        if not matches: raise LoopError(f"pattern matched nothing: {pattern}")
        for path in sorted(matches):
            if path not in seen:
                seen.add(path); rows.append({"path": rel(repo, path), "sha256": sha_file(path)})
    return sha_json(rows), rows

def request_errors(req: dict, repo: Path | None = None) -> list[str]:
    required = {"schema","enabled","mode","repository","branch","task_id","status","review_round","loop_nonce","implementation_sha","base_sha","contract_path","contract_sha256","critical_paths","critical_fingerprint_sha256","required_context_paths","review_profiles","max_review_rounds","human_gate_after_pass","created_utc"}
    errors = [f"missing:{x}" for x in sorted(required - set(req))]
    if errors: return errors
    if req["schema"] != SCHEMA: errors.append("schema")
    if req["status"] != "READY_FOR_GPT_REVIEW": errors.append("status")
    if req["mode"] not in {"LIVE","SMOKE"}: errors.append("mode")
    if not isinstance(req["enabled"], bool): errors.append("enabled")
    if not SHA_RE.fullmatch(str(req["implementation_sha"])): errors.append("implementation_sha")
    if not SHA_RE.fullmatch(str(req["base_sha"])): errors.append("base_sha")
    if int(req["review_round"]) < 1 or int(req["max_review_rounds"]) < 1: errors.append("round")
    if not isinstance(req["critical_paths"], list) or not req["critical_paths"]: errors.append("critical_paths")
    if repo:
        contract = repo / req["contract_path"]
        if not contract.is_file() or sha_file(contract) != req["contract_sha256"]: errors.append("contract_sha")
        try:
            fp, _ = fingerprint(repo, req["critical_paths"])
            if fp != req["critical_fingerprint_sha256"]: errors.append("critical_fingerprint")
        except LoopError as exc: errors.append(str(exc))
    return errors

def current_errors(cur: dict, req: dict) -> list[str]:
    required = {"schema","task_id","state","review_round","request_nonce","implementation_sha","updated_utc"}
    errors = [f"missing:{x}" for x in sorted(required - set(cur))]
    if errors: return errors
    if cur["schema"] != SCHEMA or cur["state"] not in STATES: errors.append("state")
    for a,b in (("task_id","task_id"),("review_round","review_round"),("request_nonce","loop_nonce"),("implementation_sha","implementation_sha")):
        if cur[a] != req[b]: errors.append(f"binding:{a}")
    return errors

def review_errors(review: dict, req: dict) -> list[str]:
    required = {"schema","task_id","review_round","request_nonce","reviewed_implementation_sha","reviewed_contract_sha256","decision","blocking_findings","nonblocking_findings","required_tests","review_profiles_completed","created_utc"}
    errors = [f"missing:{x}" for x in sorted(required - set(review))]
    if errors: return errors
    bindings = {"task_id":req["task_id"],"review_round":req["review_round"],"request_nonce":req["loop_nonce"],"reviewed_implementation_sha":req["implementation_sha"],"reviewed_contract_sha256":req["contract_sha256"]}
    if review["schema"] != SCHEMA or review["decision"] not in {"PASS","REVISE","SMOKE_PASS"}: errors.append("decision")
    for k,v in bindings.items():
        if review[k] != v: errors.append(f"binding:{k}")
    blockers = review["blocking_findings"]
    if not isinstance(blockers, list): errors.append("blocking_findings")
    elif review["decision"] == "PASS" and blockers: errors.append("pass_has_blockers")
    elif review["decision"] == "REVISE" and not blockers: errors.append("revise_without_blockers")
    return errors

def cmd_publish(a) -> int:
    repo, tid = a.repo_root.resolve(), task_id(a.task_id)
    contract = (repo / a.contract_path).resolve()
    if not contract.is_file(): raise LoopError(f"missing contract: {contract}")
    impl = commit_sha(repo, a.implementation_sha or git(repo,"rev-parse","HEAD"))
    base = commit_sha(repo, a.base_sha or git(repo,"rev-parse",f"{impl}^"))
    cur_path = task_dir(repo,tid)/"CURRENT.json"
    prior = load(cur_path) if cur_path.is_file() else {}
    rnd = a.review_round or int(prior.get("review_round",0))+1
    if rnd > a.max_review_rounds: raise LoopError("max review rounds exceeded")
    fp, files = fingerprint(repo,a.critical_path); nonce = uuid4().hex
    req = {"schema":SCHEMA,"enabled":bool(a.enabled),"mode":a.mode,"repository":a.repository,"branch":a.branch,"task_id":tid,"status":"READY_FOR_GPT_REVIEW","review_round":rnd,"loop_nonce":nonce,"implementation_sha":impl,"base_sha":base,"contract_path":rel(repo,contract),"contract_sha256":sha_file(contract),"critical_paths":a.critical_path,"critical_files":files,"critical_fingerprint_sha256":fp,"required_context_paths":a.context_path,"review_profiles":a.review_profile,"max_review_rounds":a.max_review_rounds,"deadline_utc":a.deadline_utc,"human_gate_after_pass":True,"training_or_deployment_authorized":False,"notification_keyword":KEYWORD,"created_utc":now()}
    errs = request_errors(req,repo)
    if errs: raise LoopError(";".join(errs))
    root = task_dir(repo,tid); write(root/"REQUEST.json",req)
    cur = {"schema":SCHEMA,"task_id":tid,"state":"WAITING_FOR_GPT_REVIEW" if a.enabled else "DISABLED","review_round":rnd,"request_nonce":nonce,"implementation_sha":impl,"request_path":rel(repo,root/"REQUEST.json"),"review_path":None,"repair_prompt_path":None,"next_action":"CHATGPT_HOURLY_REVIEW" if a.enabled else "ENABLE_AFTER_CURRENT_RUN_TERMINAL","updated_utc":now()}
    write(cur_path,cur); print(json.dumps({"request":req,"current":cur},indent=2)); return 0

def cmd_emit(a) -> int:
    repo,tid = a.repo_root.resolve(),task_id(a.task_id); req_path=task_dir(repo,tid)/"REQUEST.json"; req=load(req_path)
    errs=request_errors(req,repo)
    if errs: raise LoopError(";".join(errs))
    if not req["enabled"]: raise LoopError("request disabled")
    machine={"schema":SCHEMA,"keyword":KEYWORD,"repository":req["repository"],"branch":req["branch"],"task_id":tid,"request_path":rel(repo,req_path),"implementation_sha":req["implementation_sha"],"review_round":req["review_round"],"loop_nonce":req["loop_nonce"],"mode":req["mode"]}
    brief={"task_name":f"ai_review_{tid}_round_{req['review_round']:03d}","final_status":"complete","commit_status":a.commit_status,"push_status":a.push_status,"key_conclusion":f"{KEYWORD}: implementation is ready for independent ChatGPT review.","blocked_or_failure_reason":"","slurm_terminal_status":"not_applicable_code_review_round","evidence_paths":[rel(repo,req_path),req["contract_path"]],"next_step":KEYWORD+"\n"+json.dumps(machine,sort_keys=True)}
    root=round_dir(repo,tid,int(req["review_round"])); write(root/"notification_brief.json",brief); write(root/"review_trigger.json",machine); print(json.dumps(machine,indent=2)); return 0

def cmd_validate(a) -> int:
    repo=a.repo_root.resolve(); failures=[]; tasks=repo/"automation/ai_review_loop/tasks"
    if tasks.is_dir():
        for d in sorted(x for x in tasks.iterdir() if x.is_dir()):
            rp,cp=d/"REQUEST.json",d/"CURRENT.json"
            if not rp.exists() and not cp.exists(): continue
            if not rp.exists() or not cp.exists(): failures.append(f"{d}: request/current pair missing"); continue
            req,cur=load(rp),load(cp); failures += [f"{rp}:{e}" for e in request_errors(req,repo)]; failures += [f"{cp}:{e}" for e in current_errors(cur,req)]
            if cur.get("review_path"):
                p=repo/cur["review_path"]
                if not p.is_file(): failures.append(f"missing review:{p}")
                else: failures += [f"{p}:{e}" for e in review_errors(load(p),req)]
            if cur.get("state")=="GPT_REVIEW_REVISE" and not (cur.get("repair_prompt_path") and (repo/cur["repair_prompt_path"]).is_file()): failures.append(f"{cp}:missing repair prompt")
            if cur.get("state") in {"GPT_REVIEW_PASS","AWAIT_HUMAN_DECISION"} and cur.get("next_action")!="AWAIT_HUMAN_DECISION": failures.append(f"{cp}:PASS must stop at human")
    if failures: print("\n".join(failures),file=sys.stderr); return 1
    print("AI review loop validation: PASS"); return 0

def remote_json(repo: Path, branch: str, path: str) -> dict:
    data=json.loads(git(repo,"show",f"origin/{branch}:{path}"));
    if not isinstance(data,dict): raise LoopError(f"remote JSON not object:{path}")
    return data

def cmd_watch(a) -> int:
    repo,tid,state_root=a.repo_root.resolve(),task_id(a.task_id),a.state_root.resolve(); lock=state_root/tid/"watcher.lock"; lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open("a+") as fh:
        try: fcntl.flock(fh.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc: raise LoopError("watcher already active") from exc
        while True:
            git(repo,"fetch","origin",a.branch,"--prune")
            base=f"automation/ai_review_loop/tasks/{tid}"; req=remote_json(repo,a.branch,base+"/REQUEST.json"); cur=remote_json(repo,a.branch,base+"/CURRENT.json")
            errs=request_errors(req)+current_errors(cur,req)
            if errs: raise LoopError("remote state invalid:"+";".join(errs))
            lp=state_root/tid/"watcher_state.json"; local=load(lp) if lp.is_file() else {"schema":SCHEMA,"task_id":tid,"last_processed_review_round":0,"status":"INITIALIZED"}
            state,rnd=cur["state"],int(cur["review_round"])
            if state in {"GPT_REVIEW_PASS","AWAIT_HUMAN_DECISION","SMOKE_PASS"}:
                local.update(status="SMOKE_PASS" if state=="SMOKE_PASS" else "AWAIT_HUMAN_DECISION",last_processed_review_round=rnd,last_seen_remote_state=state,updated_utc=now()); write(lp,local); print(json.dumps(local,indent=2)); return 0
            if state=="GPT_REVIEW_REVISE" and rnd>int(local.get("last_processed_review_round",0)):
                if req["mode"]=="SMOKE" or not req["enabled"]: raise LoopError("request cannot wake Codex")
                if rnd>=int(req["max_review_rounds"]): local.update(status="STOPPED_MAX_ROUNDS",updated_utc=now()); write(lp,local); return 2
                reviewed=cur["implementation_sha"]
                if subprocess.run(["git","merge-base","--is-ancestor",reviewed,f"origin/{a.branch}"],cwd=repo).returncode: raise LoopError("reviewed SHA not on branch")
                prompt=cur.get("repair_prompt_path")
                if not prompt: raise LoopError("missing repair prompt")
                wt=a.worktree.resolve()
                if not wt.is_dir() or git(wt,"status","--porcelain"): raise LoopError("repair worktree missing or dirty")
                git(wt,"fetch","origin",a.branch,"--prune"); git(wt,"checkout",a.branch); git(wt,"merge","--ff-only",f"origin/{a.branch}")
                pp=wt/prompt
                if not pp.is_file(): raise LoopError("repair prompt missing after pull")
                thread=a.codex_thread_id_file.read_text().strip() if a.codex_thread_id_file else a.codex_thread_id
                if not thread: raise LoopError("missing Codex thread id")
                cmd=[a.codex_bin,"exec","-C",str(wt),"resume",thread,"-"]
                local.update(status="DRY_RUN_CODEX_REPAIR" if a.dry_run else "CODEX_REPAIR_RUNNING",last_processed_review_round=rnd,last_seen_remote_state=state,reviewed_implementation_sha=reviewed,repair_prompt_path=prompt,codex_command=shlex.join(cmd),updated_utc=now()); write(lp,local)
                if a.dry_run: print(json.dumps(local,indent=2)); return 0
                env=os.environ.copy(); env["CODEX_HOME"]=str(a.codex_home.resolve())
                with pp.open() as stdin: proc=subprocess.run(cmd,cwd=wt,env=env,stdin=stdin)
                local.update(status="WAITING_FOR_NEXT_GPT_REVIEW" if proc.returncode==0 else "CODEX_REPAIR_FAILED",codex_exit_code=proc.returncode,updated_utc=now()); write(lp,local)
                if proc.returncode: return proc.returncode
            if a.once: print(json.dumps(local,indent=2)); return 0
            time.sleep(a.poll_seconds)

def parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(description=__doc__); s=p.add_subparsers(dest="command",required=True)
    q=s.add_parser("publish-request"); q.add_argument("--repo-root",type=Path,default=Path.cwd()); q.add_argument("--task-id",required=True); q.add_argument("--repository",required=True); q.add_argument("--branch",required=True); q.add_argument("--contract-path",required=True); q.add_argument("--implementation-sha"); q.add_argument("--base-sha"); q.add_argument("--critical-path",action="append",required=True); q.add_argument("--context-path",action="append",default=[]); q.add_argument("--review-profile",action="append",default=["scientific_fidelity","runtime_fidelity","tests_and_known_bad"]); q.add_argument("--review-round",type=int); q.add_argument("--max-review-rounds",type=int,default=12); q.add_argument("--deadline-utc"); q.add_argument("--mode",choices=("LIVE","SMOKE"),default="LIVE"); q.add_argument("--enabled",action="store_true"); q.set_defaults(func=cmd_publish)
    q=s.add_parser("emit-notification-brief"); q.add_argument("--repo-root",type=Path,default=Path.cwd()); q.add_argument("--task-id",required=True); q.add_argument("--commit-status",default="implementation_and_request_committed"); q.add_argument("--push-status",default="origin_branch_confirmed"); q.set_defaults(func=cmd_emit)
    q=s.add_parser("validate"); q.add_argument("--repo-root",type=Path,default=Path.cwd()); q.set_defaults(func=cmd_validate)
    q=s.add_parser("watch"); q.add_argument("--repo-root",type=Path,required=True); q.add_argument("--task-id",required=True); q.add_argument("--branch",required=True); q.add_argument("--worktree",type=Path,required=True); q.add_argument("--codex-home",type=Path,required=True); q.add_argument("--codex-bin",default="codex"); q.add_argument("--codex-thread-id",default=""); q.add_argument("--codex-thread-id-file",type=Path); q.add_argument("--state-root",type=Path,default=Path("/users/a/e/aereinh/.ai-review-loop")); q.add_argument("--poll-seconds",type=int,default=60); q.add_argument("--once",action="store_true"); q.add_argument("--dry-run",action="store_true"); q.set_defaults(func=cmd_watch)
    return p

def main() -> int:
    a=parser().parse_args()
    try: return int(a.func(a))
    except LoopError as exc: print(f"AI review loop error: {exc}",file=sys.stderr); return 2

if __name__=="__main__": raise SystemExit(main())
