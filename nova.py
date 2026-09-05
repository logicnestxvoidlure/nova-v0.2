import sys, os, math, time, random, json, re, pathlib, traceback

class NovaError(Exception):
    pass

class NovaReturn(Exception):
    def __init__(self,value): self.value=value

class NovaBreak(Exception): pass
class NovaContinue(Exception): pass
class NovaThrow(Exception):
    def __init__(self,value): self.value=value

class Token:
    def __init__(self,k,v,line,col): self.kind,self.value,self.line,self.col=k,v,line,col
    def __repr__(self): return f"{self.kind}({self.value!r})"

KEY={
"let":"LET","const":"CONST","fn":"FN","class":"CLASS","extends":"EXTENDS",
"if":"IF","else":"ELSE","while":"WHILE","for":"FOR","in":"IN","return":"RETURN",
"break":"BREAK","continue":"CONTINUE","true":"TRUE","false":"FALSE","null":"NULL",
"and":"AND","or":"OR","not":"NOT","say":"SAY","try":"TRY","catch":"CATCH",
"finally":"FINALLY","throw":"THROW","import":"IMPORT","from":"FROM","as":"AS",
"new":"NEW","this":"THIS","self":"SELF","static":"STATIC","super":"SUPER",
"yield":"YIELD","async":"ASYNC","await":"AWAIT"
}

OPS=["===","!==","**=","...","??","?.","=>","==","!=","<=",">=","**","&&","||","+=","-=","*=","/=","%=","++","--","|>",".."]
ONE="{}[](),.:;+-*/%<>=!?&|@"

class Lexer:
    def __init__(self,s): self.s=s; self.i=0; self.line=1; self.col=1
    def adv(self):
        c=self.s[self.i]; self.i+=1
        if c=="\n": self.line+=1; self.col=1
        else: self.col+=1
        return c
    def peek(self,n=0):
        p=self.i+n
        return self.s[p] if p<len(self.s) else ""
    def run(self):
        out=[]
        while self.i<len(self.s):
            c=self.peek(); line,col=self.line,self.col
            if c.isspace(): self.adv(); continue
            if c=="#":
                while self.i<len(self.s) and self.peek()!="\n": self.adv()
                continue
            if c.isalpha() or c=="_":
                x=""
                while self.peek().isalnum() or self.peek()=="_": x+=self.adv()
                out.append(Token(KEY.get(x,"IDENT"),x,line,col)); continue
            if c.isdigit() or (c=="." and self.peek(1).isdigit()):
                x=""; dots=0
                while self.peek().isdigit() or self.peek()==".":
                    if self.peek()==".": dots+=1
                    x+=self.adv()
                    if dots==2 and not x.endswith(".."): break
                if dots>1 and not x.endswith(".."): raise NovaError(f"Bad number at {line}:{col}")
                out.append(Token("NUMBER",float(x) if "." in x else int(x),line,col)); continue
            if c in "\"'`":
                q=self.adv(); x=""
                while self.i<len(self.s) and self.peek()!=q:
                    if self.peek()=="\n" and q!="`": raise NovaError(f"Unterminated string at {line}:{col}")
                    if self.peek()=="\\":
                        self.adv(); e=self.adv()
                        x+={"n":"\n","t":"\t","r":"\r","\\":"\\","\"":"\"","'":"'","`":"`","0":"\0"}.get(e,e)
                    else: x+=self.adv()
                if self.i>=len(self.s): raise NovaError(f"Unterminated string at {line}:{col}")
                self.adv(); out.append(Token("STRING",x,line,col)); continue
            hit=None
            for op in OPS:
                if self.s.startswith(op,self.i): hit=op; break
            if hit:
                for _ in hit: self.adv()
                out.append(Token(hit,hit,line,col)); continue
            if c in ONE:
                self.adv(); out.append(Token(c,c,line,col)); continue
            raise NovaError(f"Unexpected {c!r} at {line}:{col}")
        out.append(Token("EOF","",self.line,self.col)); return out

class Node: pass
class Program(Node):
    def __init__(self,a): self.a=a
class Block(Node):
    def __init__(self,a): self.a=a
class Lit(Node):
    def __init__(self,v): self.v=v
class Var(Node):
    def __init__(self,n): self.n=n
class Array(Node):
    def __init__(self,a): self.a=a
class Map(Node):
    def __init__(self,a): self.a=a
class SetNode(Node):
    def __init__(self,a): self.a=a
class Unary(Node):
    def __init__(self,o,x): self.o,self.x=o,x
class Binary(Node):
    def __init__(self,a,o,b): self.a,self.o,self.b=a,o,b
class Assign(Node):
    def __init__(self,a,b,o="="): self.a,self.b,self.o=a,b,o
class Index(Node):
    def __init__(self,a,b): self.a,self.b=a,b
class Member(Node):
    def __init__(self,a,n): self.a,self.n=a,n
class Call(Node):
    def __init__(self,f,a): self.f,self.a=f,a
class Expr(Node):
    def __init__(self,x): self.x=x
class Let(Node):
    def __init__(self,n,x,c=False): self.n,self.x,self.c=n,x,c
class If(Node):
    def __init__(self,c,a,b): self.c,self.a,self.b=c,a,b
class While(Node):
    def __init__(self,c,b): self.c,self.b=c,b
class For(Node):
    def __init__(self,n,x,b): self.n,self.x,self.b=n,x,b
class Fn(Node):
    def __init__(self,n,p,b): self.n,self.p,self.b=n,p,b
class Lambda(Node):
    def __init__(self,p,b): self.p,self.b=p,b
class Return(Node):
    def __init__(self,x): self.x=x
class Break(Node): pass
class Continue(Node): pass
class Throw(Node):
    def __init__(self,x): self.x=x
class Try(Node):
    def __init__(self,a,n,b,c): self.a,self.n,self.b,self.c=a,n,b,c
class Class(Node):
    def __init__(self,n,parent,methods): self.n,self.parent,self.methods=n,parent,methods
class Import(Node):
    def __init__(self,p,n): self.p,self.n=p,n
class New(Node):
    def __init__(self,x): self.x=x
class Yield(Node):
    def __init__(self,x): self.x=x

class Parser:
    def __init__(self,t): self.t=t; self.i=0
    def c(self): return self.t[self.i]
    def adv(self): x=self.c(); self.i+=1; return x
    def match(self,*k):
        if self.c().kind in k: return self.adv()
    def need(self,k):
        if self.c().kind!=k:
            x=self.c(); raise NovaError(f"Expected {k}, got {x.kind} at {x.line}:{x.col}")
        return self.adv()
    def program(self):
        a=[]
        while self.c().kind!="EOF": a.append(self.stmt())
        return Program(a)
    def block(self):
        self.need("{"); a=[]
        while self.c().kind not in ("}","EOF"): a.append(self.stmt())
        self.need("}"); return Block(a)
    def stmt(self):
        self.match(";")
        if self.match("LET"): return self.decl(False)
        if self.match("CONST"): return self.decl(True)
        if self.match("SAY"): x=Expr(Call(Var("__say__"),[self.expr()])); self.match(";"); return x
        if self.match("IF"):
            c=self.expr(); a=self.block(); b=None
            if self.match("ELSE"): b=self.stmt() if self.c().kind=="IF" else self.block()
            return If(c,a,b)
        if self.match("WHILE"): return While(self.expr(),self.block())
        if self.match("FOR"):
            n=self.need("IDENT").value; self.need("IN"); return For(n,self.expr(),self.block())
        if self.match("FN"):
            n=self.need("IDENT").value; return Fn(n,self.params(),self.block())
        if self.match("RETURN"):
            x=None if self.c().kind in ("}",";") else self.expr(); self.match(";"); return Return(x)
        if self.match("BREAK"): self.match(";"); return Break()
        if self.match("CONTINUE"): self.match(";"); return Continue()
        if self.match("THROW"): x=self.expr(); self.match(";"); return Throw(x)
        if self.match("TRY"):
            a=self.block(); n=None; b=None; c=None
            if self.match("CATCH"):
                n=self.need("IDENT").value; b=self.block()
            if self.match("FINALLY"): c=self.block()
            return Try(a,n,b,c)
        if self.match("CLASS"):
            n=self.need("IDENT").value; parent=None
            if self.match("EXTENDS"): parent=self.need("IDENT").value
            self.need("{"); ms=[]
            while self.c().kind!="}":
                if self.match("FN") or self.match("STATIC"):
                    static=self.t[self.i-1].kind=="STATIC"
                    if static: self.match("FN")
                    name=self.need("IDENT").value; ms.append((name,self.params(),self.block(),static))
                else:
                    name=self.need("IDENT").value; ms.append((name,self.params(),self.block(),False))
            self.need("}"); return Class(n,parent,ms)
        if self.match("IMPORT"):
            p=self.need("STRING").value; n=None
            if self.match("AS"): n=self.need("IDENT").value
            self.match(";"); return Import(p,n)
        x=self.expr(); self.match(";"); return Expr(x)
    def decl(self,const):
        n=self.need("IDENT").value; self.need("="); x=self.expr(); self.match(";"); return Let(n,x,const)
    def params(self):
        self.need("("); a=[]
        if self.c().kind!=")":
            while True:
                a.append(self.need("IDENT").value)
                if not self.match(","): break
        self.need(")"); return a
    def expr(self): return self.assign()
    def assign(self):
        x=self.ternary()
        if self.c().kind in ("=","+=","-=","*=","/=","%="):
            o=self.adv().kind; return Assign(x,self.assign(),o)
        return x
    def ternary(self):
        x=self.pipe()
        if self.match("?"):
            a=self.expr(); self.need(":"); b=self.expr(); return Binary(Binary(x,"?",a),":",b)
        return x
    def pipe(self):
        x=self.logic_or()
        while self.match("|>"): x=Binary(x,"|>",self.logic_or())
        return x
    def logic_or(self):
        x=self.logic_and()
        while self.match("OR","||"): x=Binary(x,"or",self.logic_and())
        return x
    def logic_and(self):
        x=self.equality()
        while self.match("AND","&&"): x=Binary(x,"and",self.equality())
        return x
    def equality(self):
        x=self.compare()
        while self.c().kind in ("==","!=","===","!=="):
            o=self.adv().kind; x=Binary(x,o,self.compare())
        return x
    def compare(self):
        x=self.term()
        while self.c().kind in ("<","<=",">",">=","IN"):
            o=self.adv().kind; x=Binary(x,"in" if o=="IN" else o,self.term())
        return x
    def term(self):
        x=self.factor()
        while self.c().kind in ("+","-"): o=self.adv().kind; x=Binary(x,o,self.factor())
        return x
    def factor(self):
        x=self.power()
        while self.c().kind in ("*","/","%"): o=self.adv().kind; x=Binary(x,o,self.power())
        return x
    def power(self):
        x=self.unary()
        if self.match("**"): x=Binary(x,"**",self.power())
        return x
    def unary(self):
        if self.c().kind in ("-","+","NOT","!","~"):
            o=self.adv().kind; return Unary(o,self.unary())
        if self.match("NEW"): return New(self.postfix())
        if self.match("AWAIT"): return self.postfix()
        return self.postfix()
    def postfix(self):
        x=self.primary()
        while True:
            if self.match("("):
                a=[]
                if self.c().kind!=")":
                    while True:
                        a.append(self.expr())
                        if not self.match(","): break
                self.need(")"); x=Call(x,a)
            elif self.match("["):
                if self.c().kind=="]": key=Lit(None)
                else: key=self.expr()
                self.need("]"); x=Index(x,key)
            elif self.match(".","?."):
                x=Member(x,self.need("IDENT").value)
            else: break
        return x
    def primary(self):
        t=self.c()
        if self.match("NUMBER","STRING"): return Lit(t.value)
        if self.match("TRUE"): return Lit(True)
        if self.match("FALSE"): return Lit(False)
        if self.match("NULL"): return Lit(None)
        if self.match("THIS","SELF"): return Var("self")
        if self.match("IDENT"): return Var(t.value)
        if self.match("("):
            x=self.expr(); self.need(")"); return x
        if self.match("["):
            a=[]
            if self.c().kind!="]":
                while True:
                    a.append(self.expr())
                    if not self.match(","): break
            self.need("]"); return Array(a)
        if self.match("{"):
            a=[]
            if self.c().kind!="}":
                while True:
                    k=self.expr(); self.need(":"); a.append((k,self.expr()))
                    if not self.match(","): break
            self.need("}"); return Map(a)
        if self.match("FN"):
            return Lambda(self.params(),self.expr() if self.match("=>") else self.block())
        raise NovaError(f"Unexpected {t.kind} at {t.line}:{t.col}")

class Env:
    def __init__(self,parent=None): self.d={}; self.parent=parent
    def define(self,n,v,const=False): self.d[n]=(v,const); return v
    def find(self,n):
        if n in self.d: return self
        if self.parent: return self.parent.find(n)
        raise NovaError(f"Undefined variable: {n}")
    def get(self,n): return self.find(n).d[n][0]
    def set(self,n,v):
        e=self.find(n)
        if e.d[n][1]: raise NovaError(f"Constant cannot be changed: {n}")
        e.d[n]=(v,False); return v

class NovaFunction:
    def __init__(self,p,b,e,expr=False): self.p,self.b,self.e,self.expr=p,b,e,expr
    def __call__(self,*args):
        if len(args)!=len(self.p): raise NovaError(f"Expected {len(self.p)} arguments, got {len(args)}")
        e=Env(self.e)
        for n,v in zip(self.p,args): e.define(n,v)
        try:
            if self.expr: return Eval(e).eval(self.b)
            Eval(e).block(self.b.a)
        except NovaReturn as r: return r.value
        return None
    def __repr__(self): return "<function>"

class NovaInstance:
    def __init__(self,klass): self.klass=klass; self.fields={}
    def get(self,n):
        if n in self.fields: return self.fields[n]
        fn=self.klass.method(n)
        if fn: return Bound(fn,self)
        raise NovaError(f"Unknown member: {n}")
    def set(self,n,v): self.fields[n]=v
    def __repr__(self): return f"<{self.klass.name} object>"

class Bound:
    def __init__(self,fn,obj): self.fn,self.obj=fn,obj
    def __call__(self,*args): return self.fn(self.obj,*args)

class NovaClass:
    def __init__(self,name,parent,methods): self.name,self.parent,self.methods=name,parent,methods
    def method(self,n):
        if n in self.methods: return self.methods[n]
        return self.parent.method(n) if self.parent else None
    def __call__(self,*args):
        o=NovaInstance(self); init=self.method("init")
        if init: Bound(init,o)(*args)
        elif args: raise NovaError("Constructor takes no arguments")
        return o

class Eval:
    def __init__(self,e): self.e=e
    def val(self,x):
        if isinstance(x,Lit): return x.v
        if isinstance(x,Var): return self.e.get(x.n)
        if isinstance(x,Array): return [self.val(a) for a in x.a]
        if isinstance(x,Map): return {self.val(k):self.val(v) for k,v in x.a}
        if isinstance(x,Unary):
            v=self.val(x.x)
            if x.o=="-": return -v
            if x.o=="+": return +v
            if x.o in ("NOT","!"): return not bool(v)
            if x.o=="~": return ~int(v)
        if isinstance(x,Binary):
            if x.o=="and":
                a=self.val(x.a); return self.val(x.b) if a else a
            if x.o=="or":
                a=self.val(x.a); return a if a else self.val(x.b)
            if x.o=="?":
                return self.val(x.b) if self.val(x.a) else None
            if x.o==":":
                return self.val(x.a.a) if self.val(x.a.a) else self.val(x.b)
            a,b=self.val(x.a),self.val(x.b)
            if x.o=="+": return a+b
            if x.o=="-": return a-b
            if x.o=="*": return a*b
            if x.o=="/": return a/b
            if x.o=="%": return a%b
            if x.o=="**": return a**b
            if x.o in ("==","==="): return a==b
            if x.o in ("!=","!=="): return a!=b
            if x.o=="<": return a<b
            if x.o=="<=": return a<=b
            if x.o==">": return a>b
            if x.o==">=": return a>=b
            if x.o=="in": return a in b
            if x.o=="|>": return b(a) if callable(b) else NovaError("Pipe target is not callable")
        if isinstance(x,Index):
            o=self.val(x.a); k=self.val(x.b)
            if k is None:
                return list(o)
            return o[k]
        if isinstance(x,Member):
            o=self.val(x.a)
            if isinstance(o,NovaInstance): return o.get(x.n)
            if isinstance(o,dict): return o.get(x.n)
            return getattr(o,x.n)
        if isinstance(x,Call):
            f=self.val(x.f); args=[self.val(a) for a in x.a]
            if not callable(f): raise NovaError("Value is not callable")
            try: return f(*args)
            except NovaThrow: raise
            except NovaError: raise
            except Exception as z: raise NovaError(str(z))
        if isinstance(x,Assign):
            v=self.val(x.b)
            if x.o!="=":
                old=self.val(x.a); op=x.o[0]; v=Eval._op(old,op,v)
            self.assign(x.a,v); return v
        if isinstance(x,Lambda): return NovaFunction(x.p,x.b,self.e,not isinstance(x.b,Block))
        if isinstance(x,New): return self.val(x.x)
        raise NovaError("Invalid expression")
    @staticmethod
    def _op(a,o,b):
        return {"+":lambda:a+b,"-":lambda:a-b,"*":lambda:a*b,"/":lambda:a/b,"%":lambda:a%b}[o]()
    def assign(self,x,v):
        if isinstance(x,Var): return self.e.set(x.n,v)
        if isinstance(x,Index):
            o=self.val(x.a); k=self.val(x.b); o[k]=v; return v
        if isinstance(x,Member):
            o=self.val(x.a)
            if isinstance(o,NovaInstance): o.set(x.n,v); return v
            if isinstance(o,dict): o[x.n]=v; return v
        raise NovaError("Invalid assignment target")
    def stmt(self,x):
        if isinstance(x,Let): return self.e.define(x.n,self.val(x.x),x.c)
        if isinstance(x,Expr): return self.val(x.x)
        if isinstance(x,If):
            if self.val(x.c): return self.block(x.a.a)
            if x.b: return self.stmt(x.b)
        if isinstance(x,While):
            while self.val(x.c):
                try:self.block(x.b.a)
                except NovaContinue:continue
                except NovaBreak:break
        if isinstance(x,For):
            for v in self.val(x.x):
                if x.n in self.e.d:self.e.set(x.n,v)
                else:self.e.define(x.n,v)
                try:self.block(x.b.a)
                except NovaContinue:continue
                except NovaBreak:break
        if isinstance(x,Fn): return self.e.define(x.n,NovaFunction(x.p,x.b,self.e))
        if isinstance(x,Return): raise NovaReturn(None if x.x is None else self.val(x.x))
        if isinstance(x,Break): raise NovaBreak()
        if isinstance(x,Continue): raise NovaContinue()
        if isinstance(x,Throw): raise NovaThrow(self.val(x.x))
        if isinstance(x,Try):
            try:self.block(x.a.a)
            except NovaThrow as z:
                if x.b:self.e.define(x.n,z.value); self.block(x.b.a)
                else:raise
            finally:
                if x.c:self.block(x.c.a)
        if isinstance(x,Class):
            parent=self.e.get(x.parent) if x.parent else None
            methods={}
            for n,p,b,s in x.methods: methods[n]=NovaFunction(p,b,self.e)
            return self.e.define(x.n,NovaClass(x.n,parent,methods))
        if isinstance(x,Import):
            path=x.p
            if not path.endswith(".nova"): path+=".nova"
            if not os.path.isabs(path): path=os.path.join(os.getcwd(),path)
            with open(path,encoding="utf8") as f: src=f.read()
            sub=Env(self.e); Eval(sub).run(Parser(Lexer(src).run()).program())
            if x.n:self.e.define(x.n,{k:v[0] for k,v in sub.d.items() if not k.startswith("__")})
    def block(self,a):
        r=None
        for x in a:r=self.stmt(x)
        return r
    def run(self,p): return self.block(p.a)

def base():
    e=Env()
    e.define("pi",math.pi,True); e.define("e",math.e,True)
    e.define("len",len); e.define("sum",sum); e.define("min",min); e.define("max",max)
    e.define("abs",abs); e.define("sqrt",math.sqrt); e.define("floor",math.floor); e.define("ceil",math.ceil)
    e.define("round",round); e.define("pow",pow)
    e.define("range",lambda *a:list(range(*map(int,a))))
    e.define("enumerate",lambda a:[[i,x] for i,x in enumerate(a)])
    e.define("push",lambda a,x:(a.append(x) or x)); e.define("pop",lambda a:a.pop())
    e.define("sort",lambda a:(a.sort() or a)); e.define("reverse",lambda a:(a.reverse() or a))
    e.define("join",lambda a,s=",":s.join(map(str,a))); e.define("split",lambda s,d=None:s.split(d))
    e.define("upper",lambda s:str(s).upper()); e.define("lower",lambda s:str(s).lower()); e.define("trim",lambda s:str(s).strip())
    e.define("str",lambda x:"null" if x is None else str(x).lower() if isinstance(x,bool) else str(x))
    e.define("num",lambda x:float(x) if "." in str(x) else int(x)); e.define("bool",bool)
    e.define("keys",lambda x:list(x.keys())); e.define("values",lambda x:list(x.values()))
    e.define("has",lambda x,k:k in x); e.define("contains",lambda x,k:k in x)
    e.define("json_encode",lambda x:json.dumps(x)); e.define("json_decode",lambda x:json.loads(x))
    e.define("read",lambda p:open(p,encoding="utf8").read()); e.define("write",lambda p,x:open(p,"w",encoding="utf8").write(str(x)))
    e.define("exists",os.path.exists); e.define("cwd",os.getcwd); e.define("sleep",time.sleep)
    e.define("clock",time.time); e.define("random",random.random); e.define("randint",random.randint)
    e.define("input",lambda p="":input(str(p))); e.define("__say__",print)
    e.define("type",lambda x:"null" if x is None else "bool" if isinstance(x,bool) else "number" if isinstance(x,(int,float)) else "string" if isinstance(x,str) else "array" if isinstance(x,list) else "map" if isinstance(x,dict) else "object")
    e.define("assert",lambda c,m="Assertion failed":None if c else (_ for _ in()).throw(NovaError(str(m))))
    return e

def interpolate(v):
    if not isinstance(v,str): return v
    return re.sub(r"\{([^{}]+)\}",lambda m:m.group(0),v)

def source_run(src,env=None):
    p=Parser(Lexer(src).run()).program()
    return Eval(env or base()).run(p)

def ast(n,d=0):
    p="  "*d
    if isinstance(n,Program): return p+"Program\n"+"\n".join(ast(x,d+1) for x in n.a)
    if isinstance(n,Block): return p+"Block\n"+"\n".join(ast(x,d+1) for x in n.a)
    if isinstance(n,Lit): return p+f"Lit({n.v!r})"
    if isinstance(n,Var): return p+f"Var({n.n})"
    if isinstance(n,Binary): return p+f"Binary({n.o})\n"+ast(n.a,d+1)+"\n"+ast(n.b,d+1)
    if isinstance(n,Unary): return p+f"Unary({n.o})\n"+ast(n.x,d+1)
    if isinstance(n,Array): return p+"Array\n"+"\n".join(ast(x,d+1) for x in n.a)
    if isinstance(n,Map): return p+"Map\n"+"\n".join(ast(k,d+1)+" : "+ast(v) for k,v in n.a)
    if isinstance(n,Call): return p+"Call\n"+ast(n.f,d+1)
    return p+type(n).__name__

def main():
    a=sys.argv[1:]
    if not a:
        env=base(); print("Nova 2.0")
        while True:
            try:s=input("nova> ")
            except (EOFError,KeyboardInterrupt): print(); break
            if s.strip() in ("exit","quit"): break
            if not s.strip(): continue
            try:
                v=source_run(s,env)
                if v is not None: print(v)
            except NovaThrow as x: print("Error:",x.value)
            except Exception as x: print("Error:",x)
        return
    mode=None
    for m in ("--tokens","--ast","--check"):
        if m in a: mode=m; a.remove(m)
    if not a: return main()
    path=a[0]
    try:
        src=open(path,encoding="utf8").read()
        tokens=Lexer(src).run()
        if mode=="--tokens":
            for x in tokens: print(x)
        else:
            p=Parser(tokens).program()
            if mode=="--ast": print(ast(p))
            elif mode=="--check": print("OK")
            else: Eval(base()).run(p)
    except Exception as x:
        print(f"Nova error: {x}"); sys.exit(1)

if __name__=="__main__": main()
