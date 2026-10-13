#!/usr/bin/env python3
"""CPU-only, train-only feasibility audit. Not the full thesis method.

No remote model calls; gold audit labels are only consumed by evaluation.
Run command is recorded in 预实验协议.md. Third-party wheels stay local.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "vendor"))
import argparse
import bisect
import csv
import hashlib
import io
import json
import math
import platform
import resource
import signal
import time
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import product
import numpy as np
import scipy
import sklearn
from sklearn.feature_extraction import FeatureHasher
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import average_precision_score, roc_auc_score, log_loss
from sklearn.preprocessing import normalize
from threadpoolctl import threadpool_limits
import re

SEED = 920
TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)
OUT = ROOT / "results"
LOG = None
T0 = time.monotonic()


def emit(message):
    line = f"[{time.monotonic()-T0:.1f}s] {message}"
    print(line, flush=True)
    if LOG:
        LOG.write(line + "\n")
        LOG.flush()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


@dataclass
class Doc:
    ident: str
    text: str
    tokens: list
    offsets: list
    gold: list
    # Native relations: (tuple(source component indices), target index, label).
    edges: list
    issues: list


def document(ident, text, spans, edges):
    matches = list(TOKEN.finditer(text))
    offsets = [(m.start(), m.end()) for m in matches]
    starts = {s: i for i, (s, e) in enumerate(offsets)}
    ends = {e: i+1 for i, (s, e) in enumerate(offsets)}
    gold, issues = [], []
    for k, (s, e, kind) in enumerate(spans):
        if not (0 <= s < e <= len(text)):
            raise ValueError(f"Invalid raw span {ident}: {s},{e}")
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e-1].isspace():
            e -= 1
        if s not in starts or e not in ends:
            # Unique impossible coordinates keep inaccessible gold in denominators.
            gold.append((-k-1, -k-1, kind))
            issues.append({"kind": "unaligned_gold", "component": k, "start": s, "end": e})
        else:
            gold.append((starts[s], ends[e], kind))
    if len(set(gold)) != len(gold):
        issues.append({"kind": "duplicate_gold_component"})
    for srcs, dst, label in edges:
        if not srcs or any(i < 0 or i >= len(gold) for i in (*srcs, dst)):
            raise ValueError(f"Invalid native edge {ident}")
    return Doc(ident, text, [m.group() for m in matches], offsets, gold, edges, issues)


def load_data(name):
    docs, provenance = [], {"official_test_content_read": False, "excluded": []}
    if name == "aaec":
        path = ROOT / "data/aaec_brat.zip"
        split_path = ROOT / "data/aaec_split.csv"
        split = list(csv.DictReader(io.StringIO(split_path.read_text()), delimiter=";"))
        ids = sorted(x["ID"] for x in split if x["SET"] == "TRAIN")
        provenance.update(source="ArneBinder/pie-datasets@83fb46f904b13f335b6da3cce2fc7004d802ce4e",
                          split_sha256=sha(split_path.read_bytes()), official_train_count=len(ids))
        with zipfile.ZipFile(path) as z:
            for ident in ids:
                prefix = "brat-project-final/" + ident
                text = z.read(prefix + ".txt").decode("utf-8")
                ann = z.read(prefix + ".ann").decode("utf-8")
                spans, ids_map, rels, issues = [], {}, [], []
                for line in ann.splitlines():
                    if line.startswith("T"):
                        pieces = line.split("\t")
                        typ, start, end = pieces[1].split()
                        start, end = int(start), int(end)
                        ids_map[pieces[0]] = len(spans)
                        spans.append((start, end, typ))
                        if len(pieces) > 2 and text[start:end] != pieces[2]:
                            issues.append({"kind": "annotation_surface_mismatch", "id": pieces[0]})
                    elif line.startswith("R"):
                        label, a, b = line.split("\t")[1].split()
                        rels.append((a.split(":")[1], b.split(":")[1], label))
                edges = [((ids_map[a],), ids_map[b], lab) for a,b,lab in rels]
                d = document(ident, text, spans, edges)
                d.issues.extend(issues)
                docs.append(d)
    else:
        path = ROOT / "data/cdcp_acl17.zip"
        provenance.update(source="https://facultystaff.richmond.edu/~jpark/data/cdcp_acl17.zip")
        with zipfile.ZipFile(path) as z:
            names = sorted(n for n in z.namelist() if n.startswith("cdcp/train/") and n.endswith(".ann.json"))
            provenance["official_train_count"] = len(names)
            for name_ann in names:
                ident = Path(name_ann).name.split(".")[0]
                if ident == "00411":
                    provenance["excluded"].append({"id": ident, "reason": "documented duplicate/incomplete annotations; DFKI-SLT loader"})
                    continue
                a = json.loads(z.read(name_ann))
                text = z.read(name_ann.replace(".ann.json", ".txt")).decode("utf-8")
                spans = [(s, e, typ) for (s,e),typ in zip(a["prop_offsets"], a["prop_labels"])]
                edges = []
                for key, lab in [("reasons", "reason"), ("evidences", "evidence")]:
                    for (lo,hi), dst in a[key]:
                        edges.append((tuple(range(lo, hi+1)), dst, lab))
                docs.append(document(ident, text, spans, edges))
    provenance["archive_sha256"] = sha(path.read_bytes())
    provenance["archive_bytes"] = path.stat().st_size
    provenance["included_count"] = len(docs)
    provenance["issues"] = [{"id": d.ident, "issues": d.issues} for d in docs if d.issues]
    provenance["native_relations"] = sum(len(d.edges) for d in docs)
    provenance["native_multi_premise_relations"] = sum(len(src)>1 for d in docs for src,t,l in d.edges)
    groups = defaultdict(list)
    for d in docs:
        groups[sha(d.text.encode())].append(d.ident)
    provenance["duplicate_text_groups"] = [v for v in groups.values() if len(v)>1]
    return docs, provenance


def split_docs(docs):
    groups = defaultdict(list)
    for d in docs:
        groups[sha(d.text.encode())].append(d)
    keys = sorted(groups)
    np.random.default_rng(SEED).shuffle(keys)
    n = len(keys)
    # Grouped split guarantees identical raw texts never cross partitions.
    bounds = [0, round(n*.6), round(n*.8), n]
    return [[d for key in keys[bounds[i]:bounds[i+1]] for d in groups[key]] for i in range(3)]


HASHER = FeatureHasher(n_features=2**17, input_type="dict", alternate_sign=False)


def matrix(features):
    return normalize(HASHER.transform(features), norm="l2", copy=False)


def fit_model(x, y, balanced=False):
    if len(set(y)) < 2:
        raise ValueError("Only one training class; cannot fit diagnostic")
    model = SGDClassifier(loss="log_loss", alpha=1e-5, max_iter=35, tol=1e-4,
                          random_state=SEED, average=True,
                          class_weight="balanced" if balanced else None)
    model.fit(x, y)
    return model


def token_features(d, i):
    words = d.tokens
    f = {"bias": 1., "position": str(min(9, i*10//max(len(words),1)))}
    out = {"bias": 1., "position="+f["position"]: 1.}
    for delta in range(-2,3):
        w = words[i+delta] if 0 <= i+delta < len(words) else "<EDGE>"
        p = str(delta)
        out[p+"w="+w.lower()] = 1.
        out[p+"upper="+str(w[:1].isupper())] = 1.
        out[p+"suffix="+w[-3:].lower()] = 1.
    if i > 0:
        gap = d.text[d.offsets[i-1][1]:d.offsets[i][0]]
        out["linebreak="+str("\n" in gap)] = 1.
    if i+1 < len(words):
        gap = d.text[d.offsets[i][1]:d.offsets[i+1][0]]
        out["nextlinebreak="+str("\n" in gap)] = 1.
    return out


def token_targets(d):
    tags = ["O"]*len(d.tokens)
    start, end = np.zeros(len(tags), dtype=int), np.zeros(len(tags), dtype=int)
    for s,e,t in d.gold:
        if s < 0:
            continue
        if any(v != "O" for v in tags[s:e]):
            # Gold remains evaluable; record nonrepresentability of BIO training.
            continue
        tags[s] = "B-"+t
        for k in range(s+1,e):
            tags[k] = "I-"+t
        start[s] = 1
        end[e-1] = 1
    return tags, start.tolist(), end.tolist()


class Proposer:
    def fit(self, docs):
        x = matrix(token_features(d,i) for d in docs for i in range(len(d.tokens)))
        targets = [token_targets(d) for d in docs]
        self.bio = fit_model(x, [t for a,b,c in targets for t in a])
        self.start = fit_model(x, [t for a,b,c in targets for t in b], True)
        self.end = fit_model(x, [t for a,b,c in targets for t in c], True)
        lengths = [e-s for d in docs for s,e,t in d.gold if s>=0]
        self.maxlen = max(32, int(np.quantile(lengths,.995)))
        self.medlen = float(np.median(lengths))
        return self

    def predict(self, d):
        # This method must not read d.gold or d.edges.
        x = matrix(token_features(d,i) for i in range(len(d.tokens)))
        prob = self.bio.predict_proba(x)
        labels = self.bio.classes_[prob.argmax(axis=1)]
        initial = []
        s, kind = None, None
        for i, lab in enumerate([*labels, "O"]):
            typ = lab[2:] if lab != "O" else None
            if s is not None and (lab == "O" or lab.startswith("B-") or typ != kind):
                initial.append((s,i,kind))
                s, kind = None, None
            if lab != "O" and s is None:
                s, kind = i, typ
        pstart = self.start.predict_proba(x)[:,list(self.start.classes_).index(1)]
        pend = self.end.predict_proba(x)[:,list(self.end.classes_).index(1)]
        active = 1-prob[:,list(self.bio.classes_).index("O")] if "O" in self.bio.classes_ else np.ones(len(labels))
        prefix = np.r_[0., np.cumsum(np.log(np.maximum(active,1e-6)))]
        n = len(labels)
        k = min(n, max(64, min(256, n//2)))
        starts = sorted(np.argsort(-pstart, kind="stable")[:k].tolist())
        ends = sorted((np.argsort(-pend, kind="stable")[:k]+1).tolist())
        spans = {(s,e) for s in starts for e in ends if s < e <= s+self.maxlen}
        for s,e,t in initial:
            for ds,de in product(range(-2,3),repeat=2):
                if 0<=s+ds<e+de<=n:
                    spans.add((s+ds,e+de))
        def rank(span):
            s,e = span
            return (math.log(max(pstart[s],1e-9))+math.log(max(pend[e-1],1e-9))
                    +.15*(prefix[e]-prefix[s])/(e-s)
                    -.03*abs(math.log((e-s)/self.medlen)))
        base_spans = {(s,e) for s,e,t in initial}
        ranked = sorted(spans-base_spans, key=lambda v:(-rank(v),v))[:512]
        return {"initial": initial, "base": sorted(base_spans), "extra": ranked}


def pool(pred, budget=128):
    return sorted(set(pred["base"]) | set(pred["extra"][:budget]))


def span_features(d, s, e):
    out = {"bias":1., "length="+str(min(12,int(math.log2(e-s+1)*2))):1.,
           "position="+str(min(9, s*10//max(1,len(d.tokens)))):1.}
    for w, cnt in Counter(w.lower() for w in d.tokens[s:e]).items():
        out["bag="+w] = math.sqrt(cnt)
    for k in range(3):
        if s+k < e:
            out["first"+str(k)+"="+d.tokens[s+k].lower()] = 1.
            out["last"+str(k)+"="+d.tokens[e-k-1].lower()] = 1.
    for prefix, pos in [("S",s),("E",e-1)]:
        out.update({prefix+key:val for key,val in token_features(d,pos).items()})
    return out


def span_training(d, pred):
    gold = {(s,e):t for s,e,t in d.gold if s>=0}
    spans = pool(pred)
    return [span_features(d,s,e) for s,e in spans], [gold.get((s,e),"NULL") for s,e in spans]


def temperature(probs, temp):
    logp = np.log(np.clip(probs,1e-12,1))/temp
    logp -= logp.max(axis=1,keepdims=True)
    p = np.exp(logp)
    return p/p.sum(axis=1,keepdims=True)


def count_match(pred, gold):
    p, g = set(pred), set(gold)
    return [len(p&g),len(p-g),len(g-p)]


def f1(counts):
    tp,fp,fn = counts
    return 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.


def overlap(a,b):
    return a[0] < b[1] and b[0] < a[1]


def enumerate_edits(d, pred, model, temp):
    spans = pool(pred)
    classes = list(model.classes_)
    types = [t for t in classes if t != "NULL"]
    prob = temperature(model.predict_proba(matrix(span_features(d,s,e) for s,e in spans)),temp)
    idx = {sp:i for i,sp in enumerate(spans)}
    null = classes.index("NULL")
    unary = {(s,e,t):float(math.log(max(prob[i,classes.index(t)],1e-12)/max(prob[i,null],1e-12)))
             for i,(s,e) in enumerate(spans) for t in types}
    old = set(tuple(c) for c in pred["initial"])
    gold = set(d.gold)
    base = count_match(old,gold)
    old_f1 = f1(base)
    candidates = []
    def add(op, remove, new):
        remove, new = set(remove), set(new)
        if new == remove:
            return
        gain = sum(unary[c] for c in new)-sum(unary.get(c,-30.) for c in remove)-.05*len(new^remove)
        after = (old-remove)|new
        counts = count_match(after,gold)
        delta = f1(counts)-old_f1
        candidates.append({"doc":d.ident, "op":op, "remove":sorted(remove), "add":sorted(new),
                           "score":gain, "delta_f1":delta,
                           "truth":"good" if delta>1e-12 else "bad" if delta < -1e-12 else "neutral",
                           "counts":counts})
    for c in sorted(old):
        add("delete", [c], [])
        for t in types:
            if t != c[2]:
                add("retype", [c], [(c[0],c[1],t)])
    old_spans = {(s,e) for s,e,t in old}
    for s,e in spans:
        if (s,e) in old_spans:
            continue
        conflicts = [c for c in old if overlap((s,e),c)]
        if len(conflicts)>1:
            continue
        for t in types:
            add("respan" if conflicts else "insert", conflicts, [(s,e,t)])
    return {"doc":d.ident,"base_counts":base,"edits":candidates,"initial":sorted(old), "gold_n":len(gold)}


def selected_counts(rows, threshold, allow_delete=True):
    counts, chosen = [], []
    for row in rows:
        options = [c for c in row["edits"] if (allow_delete or c["op"] != "delete")]
        c = max(options,key=lambda x:x["score"],default=None)
        if c is not None and c["score"]>threshold:
            counts.append(c["counts"])
            chosen.append(c)
        else:
            counts.append(row["base_counts"])
    return counts, chosen


def diagnostic(rows):
    result = {}
    for op in ["all","insert","delete","retype","respan"]:
        a = [e for r in rows for e in r["edits"] if op == "all" or e["op"] == op]
        counts = Counter(e["truth"] for e in a)
        good_bad = [e for e in a if e["truth"] != "neutral"]
        y = [int(e["truth"]=="good") for e in good_bad]
        scores = [e["score"] for e in good_bad]
        roc = float(roc_auc_score(y,scores)) if len(set(y))==2 else None
        yall = [int(e["truth"]=="good") for e in a]
        ap = float(average_precision_score(yall,[e["score"] for e in a])) if sum(yall) else None
        result[op] = {"n":len(a),"truth_counts":dict(counts), "good_base_rate":sum(yall)/len(a) if a else None,
                      "good_vs_bad_auc_excludes_neutral":roc,"good_vs_rest_average_precision":ap}
    return result


def edit_policy(rows, threshold, allow_delete=True):
    before = np.array([r["base_counts"] for r in rows])
    after, chosen = selected_counts(rows,threshold,allow_delete)
    after = np.array(after)
    rng = np.random.default_rng(SEED)
    deltas = []
    for _ in range(1000):
        ix = rng.integers(0,len(rows),len(rows))
        deltas.append(f1(after[ix].sum(axis=0))-f1(before[ix].sum(axis=0)))
    totals = Counter(e["truth"] for e in chosen)
    return {"threshold":None if math.isinf(threshold) else threshold,"threshold_is_infinite":math.isinf(threshold),
            "allow_delete":allow_delete,"documents":len(rows),"accepted":len(chosen),
            "accepted_truth":dict(totals),"accepted_actions":dict(Counter(e["op"] for e in chosen)),
            "before_counts":before.sum(axis=0).tolist(),"after_counts":after.sum(axis=0).tolist(),
            "before_micro_f1":f1(before.sum(axis=0)),"after_micro_f1":f1(after.sum(axis=0)),
            "delta_micro_f1":f1(after.sum(axis=0))-f1(before.sum(axis=0)),
            "paired_document_bootstrap95":np.quantile(deltas,[.025,.975]).tolist(),
            "selected_edits":chosen}


def recoverability(docs, preds):
    results = []
    for budget in [0,64,128,256,512]:
        hit,total,ehit,etotal = 0,0,0,0
        missing,recovered=0,0
        types = defaultdict(lambda:[0,0])
        sizes=[]
        for d,p in zip(docs,preds):
            u=set(pool(p,budget)); base=set(p["base"])
            sizes.append(len(u))
            for s,e,t in d.gold:
                total+=1; hit+=int((s,e) in u)
                types[t][1]+=1; types[t][0]+=int((s,e) in u)
                if (s,e) not in base:
                    missing+=1; recovered+=int((s,e) in u)
            for src,dst,label in d.edges:
                etotal+=1
                ehit+=int(all(d.gold[i][:2] in u for i in (*src,dst)))
        results.append({"extra_budget":budget,"gold_components":total,"covered_components":hit,
                        "exact_span_recall":hit/total,"mean_candidates":float(np.mean(sizes)),
                        "p95_candidates":float(np.quantile(sizes,.95)),"native_relations":etotal,
                        "native_relation_endpoint_covered":ehit,"native_endpoint_recall":ehit/etotal if etotal else None,
                        "initial_missing":missing,"recovered_missing":recovered,
                        "missing_recovery_rate":recovered/missing if missing else None,
                        "by_type":{k:{"hit":v[0],"gold":v[1],"recall":v[0]/v[1]} for k,v in types.items()}})
    return results


def relation_instances(d):
    # Supplement only: gold endpoints/types. Native multi-premise cases excluded,
    # and their projected pairs are masked, not mislabeled NONE.
    positive=defaultdict(set); masked=set()
    for src,dst,lab in d.edges:
        if len(src)>1:
            masked.update((s,dst) for s in src)
        else:
            positive[src[0],dst].add(lab)
    for (s,t),labs in positive.items():
        if len(labs)>1:
            masked.add((s,t))
    for a,b in product(range(len(d.gold)),repeat=2):
        if a==b or (a,b) in masked:
            continue
        sa,ea,ta=d.gold[a]; sb,eb,tb=d.gold[b]
        if min(sa,sb)<0:
            continue
        # Original AAEC R annotations exclude MajorClaim endpoints.
        if ta=="MajorClaim" or tb=="MajorClaim":
            continue
        f={"bias":1.,"types="+ta+":"+tb:1.,"direction="+str(a<b):1.,
           "indexgap="+str(min(abs(a-b),10)):1., "tokgap="+str(min(abs(sa-sb)//20,20)):1.}
        for prefix,s,e in [("A",sa,ea),("B",sb,eb)]:
            for k,w in enumerate(d.tokens[s:min(e,s+5)]):
                f[prefix+"first"+str(k)+"="+w.lower()]=1.
            for w in set(w.lower() for w in d.tokens[s:e]):
                f[prefix+"bag="+w]=1.
        wa=set(w.lower() for w in d.tokens[sa:ea]); wb=set(w.lower() for w in d.tokens[sb:eb])
        f["overlap="+str(min(5,len(wa&wb)))]=1.
        labs=positive.get((a,b),set())
        yield f,next(iter(labs)) if labs else "NONE"


def fit_relation(train,calib,audit):
    tr=[item for d in train for item in relation_instances(d)]
    ca=[item for d in calib for item in relation_instances(d)]
    ev=[item for d in audit for item in relation_instances(d)]
    model=fit_model(matrix(f for f,y in tr),[y for f,y in tr])
    cp=model.predict_proba(matrix(f for f,y in ca)); classes=list(model.classes_)
    # Ignore no data classes only for temperature loss; record unseen labels below.
    cy=[y for f,y in ca]; known=np.array([y in classes for y in cy])
    temp=min([.5,1.,2.,4.], key=lambda t:log_loss(np.array(cy)[known],temperature(cp[known],t),labels=classes))
    p=temperature(model.predict_proba(matrix(f for f,y in ev)),temp)
    y=[y for f,y in ev]; pred=model.classes_[p.argmax(axis=1)]
    null=classes.index("NONE"); existence=1-p[:,null]; binary=np.array([v!="NONE" for v in y])
    tp=sum(a==b and a!="NONE" for a,b in zip(y,pred))
    fp=sum(b!="NONE" and a!=b for a,b in zip(y,pred))
    fn=sum(a!="NONE" and a!=b for a,b in zip(y,pred))
    return {"setting":"gold span + gold type, single-premise native relations only; not end-to-end",
            "train_pairs":len(tr),"calibration_pairs":len(ca),"audit_pairs":len(ev),
            "positive_base_rate":float(binary.mean()),"positive_count":int(binary.sum()),
            "link_average_precision":float(average_precision_score(binary,existence)) if binary.sum() else None,
            "link_auc":float(roc_auc_score(binary,existence)) if len(set(binary))==2 else None,
            "argmax_positive_typed_micro_f1":f1([tp,fp,fn]),"counts":[tp,fp,fn],
            "temperature":temp,"classes":classes,"unseen_audit_labels":dict(Counter(v for v in y if v not in classes))}


def run_dataset(name):
    emit(f"{name}: load official train only")
    docs, provenance=load_data(name)
    train,calib,audit=split_docs(docs)
    save(name+"_data_manifest.json",provenance)
    save(name+"_split.json",{k:[{"id":d.ident,"text_sha256":sha(d.text.encode())} for d in part]
                            for k,part in [("fit",train),("calibration",calib),("audit",audit)]})
    emit(f"{name}: fit/calibration/audit = {len(train)}/{len(calib)}/{len(audit)}; 3-fold OOF candidates")
    # Cross fitting is grouped by text too, never per component.
    oof_features,oof_labels=[],[]
    groupkeys=sorted({sha(d.text.encode()) for d in train})
    foldmap={key:i%3 for i,key in enumerate(groupkeys)}
    for fold in range(3):
        fitting=[d for d in train if foldmap[sha(d.text.encode())]!=fold]
        held=[d for d in train if foldmap[sha(d.text.encode())]==fold]
        proposer=Proposer().fit(fitting)
        for d in held:
            f,y=span_training(d,proposer.predict(d))
            oof_features.extend(f); oof_labels.extend(y)
        emit(f"{name}: OOF fold {fold+1}/3 finished, accumulated spans={len(oof_labels)}")
    scorer=fit_model(matrix(oof_features),oof_labels)
    del oof_features
    emit(f"{name}: fit full proposer and frozen span scorer")
    proposer=Proposer().fit(train)
    cp=[proposer.predict(d) for d in calib]
    ap=[proposer.predict(d) for d in audit]
    cf,cy=[],[]
    for d,p in zip(calib,cp):
        f,y=span_training(d,p); cf.extend(f); cy.extend(y)
    raw=scorer.predict_proba(matrix(cf)); classes=list(scorer.classes_)
    known=np.array([v in classes for v in cy])
    temps=[.5,1.,2.,4.]
    loss={t:float(log_loss(np.array(cy)[known],temperature(raw[known],t),labels=classes)) for t in temps}
    temp=min(temps,key=lambda t:loss[t])
    emit(f"{name}: calibrate edits (temperature={temp}); audit once")
    cr=[enumerate_edits(d,p,scorer,temp) for d,p in zip(calib,cp)]
    ar=[enumerate_edits(d,p,scorer,temp) for d,p in zip(audit,ap)]
    thresholds=[0.,.25,.5,1.,2.,4.,float("inf")]
    calibration=[]
    for t in thresholds:
        counts,chosen=selected_counts(cr,t)
        calibration.append((f1(np.sum(counts,axis=0)),t,len(chosen)))
    # Conservative tie breaking prefers higher threshold, including no-edit.
    _,chosen_threshold,_=max(calibration,key=lambda v:(v[0],v[1]))
    policy=edit_policy(ar,chosen_threshold)
    no_delete=edit_policy(ar,chosen_threshold,False)
    # Fixed threshold=0 is a prespecified reference, not an audit-tuned alternative.
    zero_policy=edit_policy(ar,0.)
    result={"dataset":name,"split_counts":{"fit":len(train),"calibration":len(calib),"audit":len(audit)},
            "oof_span_class_counts":dict(Counter(oof_labels)),"scorer_classes":classes,
            "span_temperature":temp,"calibration_temperature_losses":loss,
            "calibration_thresholds":[{"threshold":None if math.isinf(t) else t,"infinite":math.isinf(t),
                                         "micro_f1":v,"accepted":n} for v,t,n in calibration],
            "recoverability":recoverability(audit,ap),"edit_discrimination":diagnostic(ar),
            "calibrated_policy":policy,"same_threshold_without_deletion":no_delete,
            "prespecified_zero_threshold_policy":zero_policy}
    with (OUT/(name+"_audit_edits.jsonl")).open("w",encoding="utf-8") as f:
        for row in ar:
            f.write(json.dumps(row,ensure_ascii=False)+"\n")
    save(name+"_candidate_predictions.json",[{"id":d.ident,**p} for d,p in zip(audit,ap)])
    save(name+"_summary.json",result)
    emit(f"{name}: supplementary gold-endpoint relation scoring")
    result["conditional_relation_scoring"]=fit_relation(train,calib,audit)
    # First-contribution motivation audit: training-only class / incidence data.
    class_stats=defaultdict(lambda:Counter())
    for d in train:
        for i,(s,e,typ) in enumerate(d.gold):
            class_stats[typ]["components"]+=1
            class_stats[typ]["incident_native_relations"]+=sum(i==dst or i in src for src,dst,l in d.edges)
    result["training_class_incidence"]={k:dict(v) for k,v in class_stats.items()}
    save(name+"_summary.json",result)
    emit(f"{name}: DONE recall(+128)={result['recoverability'][2]['exact_span_recall']:.4f}, "
         f"component delta={policy['delta_micro_f1']:.6f}")
    return result


def sanity():
    assert f1([1,1,1]) == .5
    assert count_match([(0,2,"A")],[(0,2,"B")]) == [0,1,1]
    assert overlap((0,3),(2,4)) and not overlap((0,2),(2,4))
    d=document("unit","A B. ",[(0,2,"X"),(2,4,"Y")],[((0,),1,"r")])
    assert d.gold==[(0,1,"X"),(1,3,"Y")]
    p={"base":[(0,1)],"extra":[(1,3)],"initial":[(0,1,"X")]}
    r=recoverability([d],[p])
    assert r[0]["covered_components"]==1 and r[1]["native_relation_endpoint_covered"]==1
    hidden=Doc(d.ident,d.text,d.tokens,d.offsets,[],[],[])
    assert token_features(d,0)==token_features(hidden,0)
    assert span_features(d,0,1)==span_features(hidden,0,1)
    assert pool(p,0)==[(0,1)]
    assert np.allclose(temperature(np.array([[.2,.8]]),1),[[.2,.8]])


def main():
    global LOG
    parser=argparse.ArgumentParser()
    parser.add_argument("--datasets",nargs="+",choices=["aaec","cdcp"],required=True)
    parser.add_argument("--split",choices=["train-dev"],required=True)
    parser.add_argument("--max-minutes",type=int,default=20)
    args=parser.parse_args()
    OUT.mkdir(exist_ok=True)
    # Do not silently overwrite a completed run.
    if (OUT/"run_manifest.json").exists():
        raise RuntimeError("Existing run manifest: choose an explicitly approved new run location")
    LOG=(OUT/"run.log").open("x",encoding="utf-8")
    def timeout(signum,frame):
        emit("HARD TIMEOUT: stopping at user-approved time limit; partial outputs retained")
        raise TimeoutError("Hard timeout")
    signal.signal(signal.SIGALRM,timeout)
    signal.alarm(args.max_minutes*60)
    manifest={"started_utc":datetime.now(timezone.utc).isoformat(),"command":"python3 "+" ".join(sys.argv),
              "pid":os.getpid(),"initial_maxrss":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              "python":sys.version,"platform":platform.platform(),"machine":platform.machine(),
              "libraries":{"numpy":np.__version__,"scipy":scipy.__version__,"sklearn":sklearn.__version__},
              "seed":SEED,"max_minutes":args.max_minutes,"script_sha256":sha(Path(__file__).read_bytes()),
              "status":"running","completed_datasets":[],"test_data_used":False,
              "protocol_sha256":sha((ROOT/"预实验协议.md").read_bytes())}
    save("run_manifest.json",manifest)
    try:
        sanity()
        emit("Internal invariants passed; models single-thread CPU; no test data read")
        with threadpool_limits(limits=1):
            for name in args.datasets:
                run_dataset(name)
                manifest["completed_datasets"].append(name)
                save("run_manifest.json",manifest)
        manifest["status"]="completed"
    except BaseException as exc:
        manifest["status"]="timeout" if isinstance(exc,TimeoutError) else "crashed"
        manifest["error"]=repr(exc)
        raise
    finally:
        manifest["duration_seconds"]=time.monotonic()-T0
        manifest["maxrss"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        save("run_manifest.json",manifest)
        signal.alarm(0)
        LOG.close()


if __name__ == "__main__":
    main()
