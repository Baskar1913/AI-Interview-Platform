const BASE=import.meta.env.VITE_API_URL||'http://127.0.0.1:8000';
export const token=()=>localStorage.getItem('token')||'';
export async function api(path:string, options:RequestInit={}){
  const h=new Headers(options.headers);
  const t=token(); if(t) h.set('Authorization',`Bearer ${t}`);
  if(!(options.body instanceof FormData)) h.set('Content-Type','application/json');
  let r:Response;
  try{r=await fetch(BASE+path,{...options,headers:h})}catch{throw new Error(`Cannot reach the backend at ${BASE}. Start FastAPI and check VITE_API_URL.`)}
  const d=await r.json().catch(()=>({detail:r.statusText}));
  if(!r.ok) throw new Error(d.detail||`Request failed (${r.status})`);
  return d;
}
export {BASE};
