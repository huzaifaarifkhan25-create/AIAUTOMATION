import {NextRequest,NextResponse} from 'next/server';
import {BackendAuthError,backendAuthHeaders,backendURL} from '@/lib/session';
import {sameOrigin} from '@/lib/request-origin';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const id='[A-Za-z0-9_-]+',safePart=/^[A-Za-z0-9_-]{1,120}$/;
const patterns:Record<string,RegExp[]>={
 GET:[
 /^(capabilities|ready|prospects|opportunities|tasks|appointments|analyses|businesses|workflows|workflow-runs|workflow-outbox|clients|deployments)$/,
 new RegExp('^(businesses|analyses|tasks|workflows|appointments|workflow-runs|clients|deployments)/'+id+'$'),
 new RegExp('^businesses/'+id+'/(activities|contact|qualification|outreach-draft)$'),
 new RegExp('^workflows/'+id+'/export$'),new RegExp('^clients/'+id+'/(history|handoff)$'),new RegExp('^deployments/'+id+'/preflight$'),
 new RegExp('^ai/businesses/'+id+'/insights$'),/^discovery\/(collector-status|jobs)$/,new RegExp('^discovery/jobs/'+id+'(/(csv|spreadsheet.csv))?$'),
 /^agent\/(status|conversations)$/,new RegExp('^agent/conversations/'+id+'$'),/^n8n\/(status|deployments|runs|template)$/,
 /^(inquiry-sources|inquiries)$/,new RegExp('^(inquiry-sources|inquiries)/'+id+'$'),/^(outcomes|operations)\/summary$/,
 ],
 POST:[
 /^businesses$/,new RegExp('^businesses/'+id+'/(analyze|tasks|activities)$'),/^businesses\/import-csv$/,
 /^discovery\/jobs$/,new RegExp('^discovery/jobs/'+id+'/(preview|import)$'),new RegExp('^ai/businesses/'+id+'/(analysis|pitch|call-script)$'),
 /^ai\/chat$/,/^workflows$/,new RegExp('^workflows/'+id+'/(archive|runs)$'),new RegExp('^workflow-runs/'+id+'/cancel$'),
 new RegExp('^workflow-outbox/'+id+'/reconcile$'),new RegExp('^businesses/'+id+'/automation-contacts/'+id+'/opt-out$'),
 /^demo\/reminder-workflow$/,/^appointments$/,new RegExp('^appointments/'+id+'/cancel$'),
 /^clients$/,new RegExp('^clients/'+id+'/(activate|pause|archive|deployments)$'),new RegExp('^deployments/'+id+'/(validate|activate|pause|archive|runs|appointments)$'),
 /^agent\/(connection|verify|conversations)$/,new RegExp('^agent/conversations/'+id+'/messages$'),new RegExp('^agent/actions/'+id+'/review$'),
 /^n8n\/(connection|demo|deployments)$/,new RegExp('^n8n/deployments/'+id+'/(pause|inquiries)$'),
 /^inquiry-sources$/,new RegExp('^inquiry-sources/'+id+'/(pause|rotate-key)$'),new RegExp('^inquiries/'+id+'/retry$'),
 ],
 PATCH:[new RegExp('^tasks/'+id+'$'),new RegExp('^businesses/'+id+'/contact$')],
 DELETE:[/^(agent|n8n)\/connection$/],
};
async function boundedBody(request:NextRequest){
 if(!request.body)return undefined;
 const reader=request.body.getReader(),chunks:Uint8Array[]=[];let total=0;
 while(true){const{done,value}=await reader.read();if(done)break;total+=value.byteLength;
  if(total>2*1024*1024){await reader.cancel();throw new BackendAuthError('Request exceeds 2 MB',413);}chunks.push(value);}
 return Buffer.concat(chunks);
}
async function forward(request:NextRequest,context:{params:Promise<{path:string[]}>}){
 const{path}=await context.params;
 if(!path.length||path.length>6||path.some(p=>!safePart.test(p)))return NextResponse.json({error:'Unsupported API path'},{status:404});
 const joined=path.join('/');
 if(!(patterns[request.method]||[]).some(re=>re.test(joined)))return NextResponse.json({error:'API operation is not exposed in this workspace'},{status:405});
 if(request.method!=='GET'&&!sameOrigin(request))return NextResponse.json({error:'Cross-origin request refused'},{status:403});
 try{
  const headers:Record<string,string>={Accept:'application/json',...await backendAuthHeaders(request.method)};
  const target=backendURL(joined);target.search=request.nextUrl.search;
  if(request.headers.get('content-type'))headers['Content-Type']=request.headers.get('content-type')!;
  const body=request.method==='GET'?undefined:await boundedBody(request);
  const timeout=/^(agent|n8n|inquiries)\//.test(joined)?180000:35000;
  const response=await fetch(target,{method:request.method,headers,body,cache:'no-store',redirect:'manual',signal:AbortSignal.timeout(timeout)});
  const data=await response.arrayBuffer();
  return new NextResponse(data,{status:response.status,headers:{'Content-Type':response.headers.get('content-type')||'application/json','Cache-Control':'no-store','Content-Disposition':response.headers.get('content-disposition')||'inline'}});
 }catch(error){return NextResponse.json({error:error instanceof BackendAuthError?error.message:'Backend did not return a confirmed response. Inspect saved action/run status before retrying.'},{status:error instanceof BackendAuthError?error.status:502});}
}
export{forward as GET,forward as POST,forward as PATCH,forward as DELETE};
