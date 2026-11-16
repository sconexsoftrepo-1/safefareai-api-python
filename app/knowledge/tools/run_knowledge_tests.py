"""Knowledge-base tests: (1) grounding — every must_mention term is in the expected document; (2) retrieval — BM25 over ##-chunks ranks the expected document in the top 3; (3) answerable — some top-3 document contains all must_mention terms. Usage: python run_knowledge_tests.py <knowledge_dir> [cases.json] [results.json]"""
import glob,os,re,json,math,collections,sys
import sys
KB=sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','documents')
CASES=sys.argv[2] if len(sys.argv)>2 else os.path.join(KB,'knowledge_test_cases.json')
OUT=sys.argv[3] if len(sys.argv)>3 else os.path.join(KB,'..','knowledge_test_results.json')
STOP=set("a an the is are was were be been do does did how can i my me we our you your of to in on for with and or what which why where when who show tell this that it its there their from by at as not no yes any all".split())
def stem(w):
    for suf in ('ing','es','s'):
        if len(w)>4 and w.endswith(suf): return w[:-len(suf)]
    return w
def tok(t): return [stem(w) for w in re.findall(r'[a-z0-9]+',t.lower()) if w not in STOP and len(w)>1]
chunks=[]
for f in glob.glob(KB+'/**/*.md',recursive=True):
    rel=os.path.relpath(f,KB); s=open(f).read()
    fm,body=(s.split('---\n',2)[1],s.split('---\n',2)[2]) if s.startswith('---\n') else ('',s)
    title=(re.search(r'^# (.+)$',body,re.M) or [None,''])[1]
    for part in re.split(r'\n(?=##? )',body):
        chunks.append((rel,tok(fm+' '+title+' '+part)))
N=len(chunks); avg=sum(len(c[1]) for c in chunks)/N
df=collections.Counter(w for _,t in chunks for w in set(t))
tfs=[collections.Counter(t) for _,t in chunks]
def bm25(q,k1=1.2,b=0.75):
    qt=tok(q); scores=collections.defaultdict(float)
    for i,(rel,t) in enumerate(chunks):
        sc=0
        for w in qt:
            if w in tfs[i]:
                idf=math.log(1+(N-df[w]+.5)/(df[w]+.5)); f=tfs[i][w]
                sc+=idf*f*(k1+1)/(f+k1*(1-b+b*len(t)/avg))
        scores[rel]=max(scores[rel],sc)
    return sorted(scores,key=scores.get,reverse=True)
cases=json.load(open(CASES))['cases']
res=[];g_fail=[];r_fail=[]
for c in cases:
    doc=open(os.path.join(KB,c['expected_document'])).read().lower()
    missing=[m for m in c['must_mention'] if m.lower() not in doc]
    rank=bm25(c['question']); pos=rank.index(c['expected_document'])+1 if c['expected_document'] in rank else 999
    ok_g=not missing; ok_r=pos<=3
    answerable=any(all(m.lower() in open(os.path.join(KB,d)).read().lower() for m in c['must_mention']) for d in rank[:3])
    res.append({**{k:c[k] for k in('id','module','question','expected_document')},'grounding':'PASS' if ok_g else 'FAIL','missing_terms':missing,'retrieval_rank':pos,'retrieval_top3':'PASS' if ok_r else 'FAIL','top3':rank[:3],'answerable_in_top3':'PASS' if answerable else 'FAIL'})
    if not ok_g: g_fail.append((c['id'],c['expected_document'],missing))
    if not ok_r: r_fail.append((c['id'],c['question'],pos,rank[:3]))
json.dump(res,open(OUT,'w'),indent=1)
print(f'answerable-in-top3 PASS {sum(r["answerable_in_top3"]=="PASS" for r in res)}'); print(f'cases {len(cases)} | grounding PASS {len(cases)-len(g_fail)} | retrieval top-3 PASS {len(cases)-len(r_fail)} | top-1 {sum(r["retrieval_rank"]==1 for r in res)}')
for x in g_fail: print('G',x)
for x in r_fail:
    r=[y for y in res if y['id']==x[0]][0]
    print('R',x[0],x[1],x[2],r['answerable_in_top3'],x[3])
