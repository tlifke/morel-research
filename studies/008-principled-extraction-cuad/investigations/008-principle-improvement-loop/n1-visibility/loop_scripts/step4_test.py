"""Step 4: parameterized test via loop/run_slice.py; outputs to --results-dir."""
import subprocess,sys,os,argparse

def test(contract_ids, principle_path, results_dir, run_id="principle-test", model="Qwen/Qwen3.5-9B"):
    os.makedirs(results_dir, exist_ok=True)
    cmd=[sys.executable,"studies/008-principled-extraction-cuad/investigations/008-principle-improvement-loop/loop/run_slice.py",
         "--run-id",run_id,"--arm","principle-test","--contracts"]+(contract_ids if isinstance(contract_ids,list) else [contract_ids])+[
         "--repeats","1","--principles",principle_path,"--model",model,"--run-dir",os.path.join(args.results_dir,"final")]
    env=os.environ.copy(); env["PYTHONPATH"]="studies/008-principled-extraction-cuad:studies/008-principled-extraction-cuad/investigations/008-principle-improvement-loop"
    res=subprocess.run(cmd, capture_output=True, text=True, env=env)
    return res.returncode==0, res.stdout+res.stderr, os.path.join(results_dir, run_id)

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--contract-id",required=True); ap.add_argument("--principle",required=True); ap.add_argument("--results-dir",required=True); ap.add_argument("--run-id",default="principle-test")
    args=ap.parse_args()
    ok,out,run_path=test([args.contract_id],args.principle,args.results_dir,args.run_id)
    # Move loop output into results-dir so everything stays co-located
    import shutil
    if ok and run_path and os.path.exists(run_path):
        dest = os.path.join(args.results_dir, os.path.basename(run_path))
        shutil.copytree(run_path, dest, dirs_exist_ok=True)
    print("OK:",ok,"| copied to:", dest if ok else "none", "| stderr snippet:", out[:200])
