"""Temporary encrypted browser-inventory handoff. Never stores plaintext inventory."""
import json,re,secrets,time,threading
from collections import defaultdict,deque
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
LOCK=threading.Lock();DATA={};RATES=defaultdict(deque)
ORIGINS={'https://68.168.30.142','https://pantriportal.com','https://www.pantriportal.com'}
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def answer(self,status,data):
  body=json.dumps(data).encode();self.send_response(status)
  for k,v in {'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Length':str(len(body))}.items():self.send_header(k,v)
  self.end_headers();self.wfile.write(body)
 def dispatch(self):
  now=time.time();path=self.path
  with LOCK:
   for token in list(DATA):
    if DATA[token]['expires']<now:del DATA[token]
   for ip in list(RATES):
    if not RATES[ip] or RATES[ip][-1]<now-600:del RATES[ip]
   if self.command=='POST' and self.headers.get('Origin') not in ORIGINS:return self.answer(403,{'error':'Transfer origin was not accepted.'})
   if self.command=='POST' and path=='/migration/transfer':
    ip=self.headers.get('X-Real-IP',self.client_address[0]);q=RATES[ip]
    while q and q[0]<now-600:q.popleft()
    if len(q)>=20 or len(DATA)>=64 or len(RATES)>4096:return self.answer(429,{'error':'Please wait before trying another transfer.'})
    q.append(now)
    try:
     n=int(self.headers.get('Content-Length','0'))
     if not 1<=n<=1000000:raise ValueError()
     if 'application/json' not in self.headers.get('Content-Type',''):raise ValueError()
     d=json.loads(self.rfile.read(n))
     if not re.fullmatch('[A-Za-z0-9_-]{16}',d['iv']) or not re.fullmatch('[A-Za-z0-9_-]{22,950000}',d['ciphertext']):raise ValueError()
    except (ValueError,KeyError,TypeError):return self.answer(400,{'error':'Invalid transfer. No inventory was changed.'})
    token=secrets.token_urlsafe(32);DATA[token]={'expires':now+900,'iv':d['iv'],'ciphertext':d['ciphertext'],'complete':False};return self.answer(201,{'token':token})
   m=re.fullmatch('/migration/(transfer|status|complete)/([A-Za-z0-9_-]{43})',path)
   if m:
    operation,token=m.groups();d=DATA.get(token)
    if not d:return self.answer(404,{'error':'The transfer expired. Open the old address in the original browser to retry.'})
    if self.command=='GET' and operation=='status':return self.answer(200,{'complete':d['complete']})
    if self.command=='GET' and operation=='transfer':
     if d['complete']:return self.answer(410,{'error':'This transfer was already completed. Open www.pantriportal.com to see your inventory.'})
     return self.answer(200,{'iv':d['iv'],'ciphertext':d['ciphertext']})
    if self.command=='POST' and operation=='complete':
     d['complete']=True;d.pop('ciphertext',None);return self.answer(200,{'ok':True})
   return self.answer(404,{'error':'Transfer route not found.'})
 def handle_request(self):
  try:self.dispatch()
  except (BrokenPipeError,ConnectionResetError):pass
  except Exception:self.answer(500,{'error':'The transfer service is unavailable. Your original inventory remains saved.'})
 do_GET=do_POST=handle_request
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',8766),Handler).serve_forever()
