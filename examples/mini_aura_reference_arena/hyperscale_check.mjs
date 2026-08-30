import fs from 'fs';
const S=[1,2,3,4,5,12,16,48];
const gcd=(a,b)=>{while(b){[a,b]=[b,a%b]}return a};
function omega(n){let c=0;for(let d=2;d*d<=n;d++){while(n%d===0){n/=d;c++}}if(n>1)c++;return c}
const dist=(a,b)=>{const g=gcd(a,b);return omega(a/g)+omega(b/g)};
function* perms(a,n=a.length){if(n<=1){yield a.slice();return;}for(let i=0;i<n;i++){yield* perms(a,n-1);const j=n%2?0:i;[a[j],a[n-1]]=[a[n-1],a[j]];}}
let tr=new Set(), count=0;
for(const p of perms(S.slice())){count++;let g=0,t=[];for(const x of p){g=gcd(g,x);t.push(g)}tr.add(t.join(','));}
let sub=0;for(let m=1;m<(1<<S.length);m++){let g=0;for(let i=0;i<S.length;i++)if(m>>i&1)g=gcd(g,S[i]);if(g===1)sub++;}
let ecc={};for(const a of S)ecc[a]=Math.max(...S.map(b=>dist(a,b)));
const min=Math.min(...Object.values(ecc));
const out={permutations:count,unique_running_gcd_trajectories:tr.size,subsets_with_gcd_1:sub,nonempty_subsets:255,minimax_centers:S.filter(s=>ecc[s]===min)};
const outIndex=process.argv.indexOf('--out'); if(outIndex>=0) fs.writeFileSync(process.argv[outIndex+1],JSON.stringify(out,null,2)); console.log(JSON.stringify(out));
