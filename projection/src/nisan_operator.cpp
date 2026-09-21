// Fixed-law Nisan projection cost kernel. No protocol or PRG proof is implemented.
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <wmmintrin.h>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <bcrypt.h>
#else
#include <sys/random.h>
#endif
using U=std::uint64_t;
using Bytes=std::vector<std::uint8_t>;
using Words=std::vector<U>;
using Clock=std::chrono::steady_clock;
constexpr U Q=(U(1)<<48)-59;
constexpr unsigned MAX_BLOCK=2048, MAX_WORDS=(MAX_BLOCK+63)/64;
const std::array<U,6> NS={1048896,412800,243840,182016,155648,142464};
const std::array<unsigned,6> NB={1186,1226,1218,1212,1206,1204}, KS={21,20,19,18,18,18};
void require(bool b,const std::string& s){if(!b)throw std::runtime_error(s);}
U ceiling(U a,U b){return a/b+(a%b!=0);}
double seconds(Clock::time_point t){return std::chrono::duration<double>(Clock::now()-t).count();}
unsigned bit(const Words& a,U i){return unsigned((a.at(i/64)>>(i%64))&1);}
unsigned bit(const Bytes& a,U i){return unsigned((a.at(i/8)>>(i%8))&1);}
void mask(Words& a,unsigned n){if(n%64)a.back()&=(U(1)<<(n%64))-1;}
std::string quote(const std::string& s){
    std::string o="\"";for(char c:s){if(c=='"'||c=='\\')o+='\\';require(c>=32,"control character in JSON string");o+=c;}return o+'"';
}
struct Json{
    std::ostringstream out;bool comma=false;
    Json(){out<<std::setprecision(12)<<"{";}
    void key(const std::string& k){if(comma)out<<",";comma=true;out<<quote(k)<<":";}
    template<class T>void number(const std::string& k,T x){key(k);out<<x;}
    void text(const std::string& k,const std::string& x){key(k);out<<quote(x);}
    void boolean(const std::string& k,bool x){key(k);out<<(x?"true":"false");}
    void raw(const std::string& k,const std::string& x){key(k);out<<x;}
    std::string str(){return out.str()+"}";}
};
template<class T>std::string array_json(const std::vector<T>& a){
    std::ostringstream o;o<<"[";for(std::size_t i=0;i<a.size();++i){if(i)o<<",";o<<a[i];}return o.str()+"]";
}
struct Counters{
    U hashes=0,dfs=0,leaves=0,bits=0,entries=0,nonzero=0,field_ops=0;
    U and_words=0,parities=0,clmul=0,clmul_xor_words=0,input_words=0,output_words=0;
    std::array<U,64> by_level{};
};
std::string count_json(const Counters& c,unsigned n,unsigned k,U entries,unsigned actions){
    Json j;j.number("hash_calls",c.hashes);j.number("dfs_calls",c.dfs);j.number("leaf_blocks",c.leaves);
    j.number("consumed_bits",c.bits);j.number("entries",c.entries);j.number("nonzero_entries",c.nonzero);
    j.number("field_addsub_calls",c.field_ops);j.number("worst_case_field_addsub_calls",entries*actions);
    j.number("scalar_and_words",c.and_words);j.number("scalar_parity_calls",c.parities);
    j.number("clmul64_products",c.clmul);j.number("clmul_product_word_xors",c.clmul_xor_words);
    j.number("hash_input_words",c.input_words);j.number("hash_output_words",c.output_words);
    j.number("reference_bit_convolution_products",U(n)*n*c.hashes);
    std::vector<U> levels;for(unsigned h=1;h<=k;++h)levels.push_back(c.by_level[h]);
    j.raw("hash_by_level",array_json(levels));return j.str();
}
U fixture_word(U& state){
    // SplitMix64 is ONLY a labelled deterministic fixture, never production Gen.
    U z=(state+=0x9e3779b97f4a7c15ULL);z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL;
    z=(z^(z>>27))*0x94d049bb133111ebULL;return z^(z>>31);
}
U fill_random(Bytes& bytes,bool fixture,U seed){
    if(fixture){U v=0;for(std::size_t i=0;i<bytes.size();++i){if(i%8==0)v=fixture_word(seed);bytes[i]=std::uint8_t(v>>(8*(i%8)));}return 0;}
    U calls=0;
    for(std::size_t at=0;at<bytes.size();){
        std::size_t amount=std::min<std::size_t>(bytes.size()-at,1u<<20);
#ifdef _WIN32
        auto status=BCryptGenRandom(nullptr,bytes.data()+at,ULONG(amount),BCRYPT_USE_SYSTEM_PREFERRED_RNG);
        require(status==0,"BCryptGenRandom failed; no fallback randomness");
#else
        auto got=getrandom(bytes.data()+at,amount,0);require(got>0,"getrandom failed");amount=std::size_t(got);
#endif
        at+=amount;++calls;
    }return calls;
}
Bytes unhex(const std::string& s){
    require(s.size()%2==0,"hex string must have even length");Bytes out;
    auto digit=[](char c)->unsigned{if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;if(c>='A'&&c<='F')return c-'A'+10;throw std::runtime_error("invalid hex");};
    for(std::size_t i=0;i<s.size();i+=2)out.push_back(std::uint8_t(16*digit(s[i])+digit(s[i+1])));
    return out;
}
U reverse64(U x){
    x=((x>>1)&0x5555555555555555ULL)|((x&0x5555555555555555ULL)<<1);
    x=((x>>2)&0x3333333333333333ULL)|((x&0x3333333333333333ULL)<<2);
    x=((x>>4)&0x0f0f0f0f0f0f0f0fULL)|((x&0x0f0f0f0f0f0f0f0fULL)<<4);
    x=((x>>8)&0x00ff00ff00ff00ffULL)|((x&0x00ff00ff00ff00ffULL)<<8);
    x=((x>>16)&0x0000ffff0000ffffULL)|((x&0x0000ffff0000ffffULL)<<16);return(x>>32)|(x<<32);
}
struct Hash{Words a,b;};
struct Descriptor{
    unsigned n,k;Bytes packed;Words x;std::vector<Hash> hashes;
    static U bit_size(unsigned n,unsigned k){return n+U(k)*(3*n-1);}
    Descriptor(unsigned nn,unsigned kk,Bytes bytes):n(nn),k(kk),packed(std::move(bytes)){
        require(n>=1&&n<=MAX_BLOCK&&k<63,"block/depth outside implementation caps");
        U size=bit_size(n,k);require(packed.size()==ceiling(size,8),"descriptor byte count");
        if(size%8)require((packed.back()>>(size%8))==0,"noncanonical descriptor padding");
        U at=0;auto read=[&](unsigned len){Words out(ceiling(len,64));for(unsigned i=0;i<len;++i)out[i/64]|=U(bit(packed,at++))<<(i%64);return out;};
        x=read(n);for(unsigned i=0;i<k;++i)hashes.push_back({read(2*n-1),read(n)});
        require(at==size,"descriptor parser internal length");
    }
};
Bytes gen_descriptor(unsigned n,unsigned k,bool fixture,U seed,U& calls){
    U bits=Descriptor::bit_size(n,k);Bytes out(ceiling(bits,8));calls=fill_random(out,fixture,seed);
    if(bits%8)out.back()&=std::uint8_t((1u<<(bits%8))-1);
    return out;
}
void scalar_hash(const Hash& h,const Words& x,unsigned n,Words& out,Counters& c){
    std::fill(out.begin(),out.end(),0);unsigned nw=(n+63)/64;
    for(unsigned j=0;j<n;++j){
        U accum=0;unsigned shift=j%64,base=j/64;
        for(unsigned i=0;i<nw;++i){
            U segment=h.a[base+i]>>shift;
            if(shift&&base+i+1<h.a.size())segment|=h.a[base+i+1]<<(64-shift);
            accum^=segment&x[i];
        }
        out[j/64]|=U(unsigned(__builtin_parityll(accum))^bit(h.b,j))<<(j%64);
    }
    c.and_words+=U(n)*nw;c.parities+=n;
}
__attribute__((target("pclmul,sse2")))
void pclmul_hash(const Hash& h,const Words& x,unsigned n,Words& out,Counters& c){
    unsigned nw=(n+63)/64,aw=unsigned(h.a.size()),padding=64*nw-n;
    std::array<U,MAX_WORDS+1> rev{},wide_rev{};
    std::array<U,3*MAX_WORDS+2> product{};
    for(unsigned i=0;i<nw;++i)wide_rev[i]=reverse64(x[nw-1-i]);
    for(unsigned i=0;i<nw;++i){rev[i]=wide_rev[i]>>padding;if(padding)rev[i]|=wide_rev[i+1]<<(64-padding);}
    for(unsigned i=0;i<nw;++i){
        auto a=_mm_set_epi64x(0,static_cast<long long>(rev[i]));
        for(unsigned j=0;j<aw;++j){
            auto b=_mm_set_epi64x(0,static_cast<long long>(h.a[j]));
            auto p=_mm_clmulepi64_si128(a,b,0);
            product[i+j]^=U(_mm_cvtsi128_si64(p));
            product[i+j+1]^=U(_mm_cvtsi128_si64(_mm_unpackhi_epi64(p,p)));
        }
    }
    unsigned base=(n-1)/64,shift=(n-1)%64;
    for(unsigned j=0;j<nw;++j){
        U value=product[base+j]>>shift;if(shift)value|=product[base+j+1]<<(64-shift);
        out[j]=value^h.b[j];
    }mask(out,n);c.clmul+=U(nw)*aw;c.clmul_xor_words+=2*U(nw)*aw;
}
bool pclmul_available(){__builtin_cpu_init();return __builtin_cpu_supports("pclmul");}
using HashFn=void(*)(const Hash&,const Words&,unsigned,Words&,Counters&);
HashFn select_hash(const std::string& wanted,std::string& selected){
    if(wanted=="scalar"){selected="scalar_packed_parity";return scalar_hash;}
    require(wanted=="auto"||wanted=="pclmul","hash must be auto, scalar, pclmul");
    if(pclmul_available()){selected="pclmul64_same_convolution";return pclmul_hash;}
    require(wanted!="pclmul","PCLMUL absent");selected="scalar_packed_parity";return scalar_hash;
}
std::array<U,64> prefix_hash_counts(U leaves,unsigned k){
    std::array<U,64> out{};for(unsigned h=1;h<=k;++h)out[h]=(leaves-1+(U(1)<<(h-1)))/(U(1)<<h);return out;
}
struct Stream{
    const Descriptor& d;HashFn fn;Counters& c;U remaining;std::vector<Words> temp;
    Stream(const Descriptor& dd,HashFn ff,Counters& cc,U bits):d(dd),fn(ff),c(cc),remaining(bits){
        require(bits>=1&&bits<=U(d.n)*(U(1)<<d.k),"prefix exceeds generator output");temp.assign(d.k+1,Words(ceiling(d.n,64)));
    }
    template<class Callback>void dfs(unsigned level,const Words& x,Callback& take){
        if(!remaining)return;
        ++c.dfs;
        if(level==0){unsigned amount=unsigned(std::min<U>(remaining,d.n));take(x,amount);remaining-=amount;++c.leaves;c.bits+=amount;return;}
        dfs(level-1,x,take);if(!remaining)return;
        fn(d.hashes[level-1],x,d.n,temp[level],c);++c.hashes;++c.by_level[level];
        c.input_words+=x.size();c.output_words+=temp[level].size();dfs(level-1,temp[level],take);
    }
    template<class Callback>void run(Callback take){
        U leaves=ceiling(remaining,d.n);auto expected=prefix_hash_counts(leaves,d.k);dfs(d.k,d.x,take);
        require(remaining==0&&c.hashes==leaves-1,"DFS prefix hash count mismatch");require(c.by_level==expected,"per-level hash count mismatch");
    }
};
inline U add_trit(U total,U value,int t){
    if(t==1){U out=total+value;return out>=Q?out-Q:out;}
    return total>=value?total-value:total+Q-value;
}
struct Action{
    U N,m,row=0,col=0;unsigned adj_count;bool eval_on,collect,digest_on;
    const Words& w;const std::vector<Words>& alpha;Counters& c;
    Words eval;std::vector<Words> adj;std::vector<int> trits;int pending=-1;U digest=1469598103934665603ULL;
    Action(U n,U mm,unsigned ac,bool e,bool keep,const Words& ww,const std::vector<Words>& aa,Counters& cc):
        N(n),m(mm),adj_count(ac),eval_on(e),collect(keep),digest_on(!e&&ac==0),w(ww),alpha(aa),c(cc),eval(e?mm:0),adj(ac,Words(n)){}
    void trit(int t){
        ++c.entries;if(collect)trits.push_back(t);
        if(digest_on)digest=(digest^U(t+1))*1099511628211ULL;
        if(t){++c.nonzero;if(eval_on)eval[row]=add_trit(eval[row],w[col],t);
            for(unsigned a=0;a<adj_count;++a)adj[a][col]=add_trit(adj[a][col],alpha[a][row],t);
            c.field_ops+=U(eval_on)+adj_count;
        }
        if(++col==N){col=0;++row;}
    }
    void words(const Words& b,unsigned size){
        unsigned at=0;if(pending>=0&&size){trit(pending-int(bit(b,0)));pending=-1;at=1;}
        for(;at+1<size;at+=2)trit(int(bit(b,at))-int(bit(b,at+1)));
        if(at<size)pending=int(bit(b,at));
    }
    void bytes(const Bytes& b,U size){
        for(U at=0;at<size;at+=2)trit(int(bit(b,at))-int(bit(b,at+1)));
        c.bits=size;
    }
    void finish(){require(row==m&&col==0&&pending<0&&c.entries==N*m,"action consumption mismatch");}
};
U digest_words(const Words& a){U x=1469598103934665603ULL;for(U v:a)x=(x^v)*1099511628211ULL;return x;}
Words csv(const std::string& s){
    std::stringstream ss(s);std::string t;Words out;while(std::getline(ss,t,',')){
        require(!t.empty(),"empty vector coefficient");std::size_t used=0;long long x=std::stoll(t,&used);
        require(used==t.size(),"trailing text in field coefficient");
        require(x>=-static_cast<long long>(Q/2)&&x<static_cast<long long>(Q),"coefficient neither centered nor canonical");
        out.push_back(x<0?U(static_cast<long long>(Q)+x):U(x));
    }return out;
}
std::vector<Words> alphas(const std::string& s){
    std::stringstream ss(s);std::string t;std::vector<Words> out;while(std::getline(ss,t,';'))out.push_back(csv(t));require(out.size()<=3,"at most three alpha arrays");return out;
}
using Args=std::map<std::string,std::string>;
Args args_read(int argc,char**argv){Args a;for(int i=2;i<argc;i+=2){require(i+1<argc&&std::string(argv[i]).rfind("--",0)==0,"options require --name value");require(!a.count(argv[i]),"duplicate option");a[argv[i]]=argv[i+1];}return a;}
std::string get(const Args& a,const std::string& k,const std::string& fallback=""){auto i=a.find(k);return i==a.end()?fallback:i->second;}
void emit(const std::string& s,const Args& a){
    auto path=get(a,"--json");if(!path.empty()){std::ofstream f(path,std::ios::binary);require(bool(f),"cannot open JSON");f<<s<<"\n";require(bool(f),"JSON write failed");}std::cout<<s<<"\n";
}
std::string vector_run(const Args& a){
    U N=std::stoull(get(a,"--N")),m=std::stoull(get(a,"--m"));unsigned n=std::stoul(get(a,"--block")),k=std::stoul(get(a,"--depth"));
    require(N>=1&&m>=1&&N<=4096&&m<=4096/N,"vector mode capped at 4096 entries");
    Descriptor d(n,k,unhex(get(a,"--descriptor-hex")));Words w=csv(get(a,"--w"));auto aa=alphas(get(a,"--alpha"));
    require(w.size()==N,"w length mismatch");for(auto& v:aa)require(v.size()==m,"alpha length mismatch");
    std::string selected;auto fn=select_hash(get(a,"--hash","auto"),selected);Counters c;Action act(N,m,unsigned(aa.size()),true,true,w,aa,c);
    Stream st(d,fn,c,2*N*m);st.run([&](const Words& b,unsigned sz){act.words(b,sz);});act.finish();
    Json j;j.text("command","vector");j.number("q",Q);j.text("hash",selected);j.raw("trits",array_json(act.trits));j.raw("eval",array_json(act.eval));
    std::string arrays="[";for(std::size_t i=0;i<act.adj.size();++i){if(i)arrays+=",";arrays+=array_json(act.adj[i]);}arrays+="]";
    j.raw("adj",arrays);j.raw("counts",count_json(c,n,k,N*m,1+unsigned(aa.size())));return j.str();
}
std::string selftest(){
    bool pcl=pclmul_available();U seed=17,hcases=0,pcases=0,fcases=0,rejects=0;
    for(unsigned n:{1u,2u,3u,7u,31u,63u,64u,65u,127u,129u,1186u,1204u,1212u,1218u,1226u}){
        for(unsigned repeat=0;repeat<8;++repeat){
            U calls=0;Descriptor d(n,4,gen_descriptor(n,4,true,fixture_word(seed),calls));Words left(ceiling(n,64)),right(left.size());Counters c1,c2;
            for(auto& h:d.hashes){
                scalar_hash(h,d.x,n,left,c1);if(pcl){pclmul_hash(h,d.x,n,right,c2);require(left==right,"PCLMUL/scalar mismatch");}
                for(unsigned j=0;j<n;++j){unsigned v=bit(h.b,j);for(unsigned i=0;i<n;++i)v^=bit(h.a,i+j)&bit(d.x,i);require(v==bit(left,j),"direct bit/scalar mismatch");}
                ++hcases;
            }
        }
    }
    for(unsigned n:{1u,3u,8u,65u})for(unsigned k=0;k<=5;++k){
        U calls=0;Descriptor d(n,k,gen_descriptor(n,k,true,fixture_word(seed),calls));Words full(ceiling(U(n)*(U(1)<<k),64));U at=0;Counters c;
        Stream all(d,scalar_hash,c,U(n)*(U(1)<<k));all.run([&](const Words& w,unsigned sz){for(unsigned i=0;i<sz;++i)full[(at+i)/64]|=U(bit(w,i))<<((at+i)%64);at+=sz;});
        for(U prefix=1;prefix<=U(n)*(U(1)<<k);prefix+=std::max<U>(1,n/2)){
            Counters cc;U pos=0;Stream part(d,pcl?pclmul_hash:scalar_hash,cc,prefix);
            part.run([&](const Words& w,unsigned sz){for(unsigned i=0;i<sz;++i)require(bit(w,i)==bit(full,pos+i),"prefix replay mismatch");pos+=sz;});
            require(pos==prefix,"prefix length mismatch");++pcases;
        }
    }
    for(U x:{U(0),U(1),Q/2,Q-2,Q-1})for(U y:{U(0),U(1),Q/2,Q-2,Q-1})for(int t:{-1,1}){
        require(add_trit(x,y,t)==(t==1?(x+y)%Q:(x+Q-y)%Q),"field arithmetic mismatch");++fcases;
    }
    {U calls=0;Bytes b=gen_descriptor(7,3,true,1,calls);b.back()|=128;try{Descriptor bad(7,3,b);}catch(const std::exception&){++rejects;}require(rejects==1,"bad padding accepted");}
    Json j;j.text("command","selftest");j.boolean("passed",true);j.boolean("pclmul_available",pcl);
    j.number("direct_scalar_optimized_hash_cases",hcases);j.number("prefix_replay_count_cases",pcases);j.number("field_cases",fcases);j.number("padding_rejections",rejects);return j.str();
}
std::string bench(const Args& a){
    unsigned layer=std::stoul(get(a,"--layer","0"));require(layer<6,"layer out of range");
    U N=NS[layer],rows=std::stoull(get(a,"--rows","4"));require(rows>=1&&rows<=864,"rows must be 1..864");
    unsigned n=NB[layer],k=KS[layer];U entries=N*rows,bits=2*entries;
    std::string source=get(a,"--source","nisan"),op=get(a,"--operation","combined");
    require(source=="nisan"||source=="iid","source must be nisan or iid");
    require(op=="expand"||op=="eval"||op=="adj3"||op=="combined","invalid operation");
    bool fixture=a.count("--test-seed"),ev=op=="eval"||op=="combined";unsigned ac=op=="adj3"||op=="combined"?3:0;
    U seed=fixture?std::stoull(get(a,"--test-seed")):0,calls=0;std::string selected;auto fn=select_hash(get(a,"--hash","auto"),selected);
    auto start=Clock::now();Words w(N);for(U j=0;j<N;++j)w[j]=(j*65537+19)%Q;
    std::vector<Words> alpha(3,Words(rows));for(unsigned v=0;v<3;++v)for(U i=0;i<rows;++i)alpha[v][i]=((i+1)*104729+17*v+1)%Q;
    double inputs_time=seconds(start);start=Clock::now();Bytes raw;
    if(source=="nisan")raw=gen_descriptor(n,k,fixture,seed,calls);
    else {raw.resize(ceiling(bits,8));calls=fill_random(raw,fixture,seed);}
    double gen_time=seconds(start),canonical_time=0;U canonical_bytes=0;
    if(source=="iid"){
        // Canonical baseline map, declared explicitly: 00=0, 01=+1,
        // 10=-1, 11=invalid. Raw fair-bit pair 11 is changed to 00.
        // The source grammar does not assign numeric codes; no wire claim
        // depends on this harmless explicit choice of its three symbols.
        start=Clock::now();
        for(auto& b:raw){unsigned lows=b&0x55,highs=(b>>1)&0x55,both=lows&highs;b=std::uint8_t(b&~(both|(both<<1)));}
        if(bits%8)raw.back()&=std::uint8_t((1u<<(bits%8))-1);
        canonical_time=seconds(start);canonical_bytes=raw.size();
    }
    start=Clock::now();std::unique_ptr<Descriptor> d;
    if(source=="nisan")d=std::make_unique<Descriptor>(n,k,raw);
    else {unsigned invalid=0;for(auto b:raw)invalid|=(b&(b>>1))&0x55;require(invalid==0,"invalid iid canonical symbol");}
    double parse_time=seconds(start);Counters c;start=Clock::now();Action act(N,rows,ac,ev,false,w,alpha,c);
    double alloc_time=seconds(start),eval_time=0,adj_time=0,work_time=0;
    Counters eval_counts,adj_counts;
    auto run_pass=[&](){
        auto begin=Clock::now();
        if(d){Stream st(*d,fn,c,bits);st.run([&](const Words& b,unsigned size){act.words(b,size);});}
        else act.bytes(raw,bits);
        act.finish();return seconds(begin);
    };
    if(op=="combined"){
        act.adj_count=0;eval_time=run_pass();eval_counts=c;
        c=Counters{};act.row=act.col=0;act.pending=-1;act.digest=1469598103934665603ULL;
        act.eval_on=false;act.adj_count=3;adj_time=run_pass();adj_counts=c;
        c.hashes+=eval_counts.hashes;c.dfs+=eval_counts.dfs;c.leaves+=eval_counts.leaves;
        c.bits+=eval_counts.bits;c.entries+=eval_counts.entries;c.nonzero+=eval_counts.nonzero;
        c.field_ops+=eval_counts.field_ops;c.and_words+=eval_counts.and_words;c.parities+=eval_counts.parities;
        c.clmul+=eval_counts.clmul;c.clmul_xor_words+=eval_counts.clmul_xor_words;
        c.input_words+=eval_counts.input_words;c.output_words+=eval_counts.output_words;
        for(unsigned h=0;h<64;++h)c.by_level[h]+=eval_counts.by_level[h];
        work_time=eval_time+adj_time;
    }else{
        work_time=run_pass();
        if(op=="eval"){eval_time=work_time;eval_counts=c;}
        if(op=="adj3"){adj_time=work_time;adj_counts=c;}
    }
    start=Clock::now();U edigest=digest_words(act.eval);std::vector<U> adigests;for(auto& v:act.adj)adigests.push_back(digest_words(v));double digest_time=seconds(start);
    U parsed_words=ceiling(n,64)+U(k)*(ceiling(2*n-1,64)+ceiling(n,64));
    Json mem;mem.number("input_field_bytes",(N+3*rows)*8);mem.number("result_field_bytes",(act.eval.size()+U(ac)*N)*8);
    mem.number("raw_bytes",raw.size());mem.number("descriptor_copy_bytes",d?d->packed.size():0);
    mem.number("parsed_descriptor_word_bytes",d?parsed_words*8:0);mem.number("DFS_word_bytes",d?U(k+1)*ceiling(n,64)*8:0);
    mem.number("hash_fixed_stack_scratch_bound_bytes",d?(5*MAX_WORDS+4)*8:0);
    mem.text("excludes","allocator metadata, vector objects, call frames, runtime, OS RSS");
    Json timing;timing.number("synthetic_inputs",inputs_time);timing.number("Gen_random_bytes",gen_time);timing.number("iid_canonicalization",canonical_time);
    timing.number("descriptor_or_iid_validation",parse_time);timing.number("result_allocation_zeroing",alloc_time);
    timing.number("stream_decode_and_action",work_time);timing.number("output_digest",digest_time);
    timing.number("expand_decode_and_Eval",eval_time);timing.number("expand_decode_and_Adj3",adj_time);
    Json j;j.text("command","bench");j.number("layer",layer);j.number("N",N);j.number("rows_measured",rows);j.boolean("full_864_rows",rows==864);
    j.number("q",Q);j.text("source",source);j.text("operation",op);
    j.text("randomness",fixture?"splitmix64_reproducible_fixture_NOT_production":"fresh_OS_random_bits");
    j.number("test_seed",seed);j.text("hash",selected);j.boolean("pclmul_available",pclmul_available());
    j.text("synthetic_w_rule","(j*65537+19) mod q");j.text("synthetic_alpha_rule","((i+1)*104729+17*a+1) mod q");
    j.text("packed_iid_layout","canonical: pair integer 0=zero,1=plus,2=minus,3=reject; raw 3 mapped to0 in separately timed pass");
    j.number("descriptor_bits",d?Descriptor::bit_size(n,k):0);j.number("random_bytes_sampled",raw.size());j.number("OS_random_calls",calls);
    j.number("iid_canonicalization_byte_visits",canonical_bytes);j.number("iid_validation_byte_visits",d?0:raw.size());
    j.boolean("matrix_materialized",!d);j.number("explicit_matrix_payload_bytes",d?0:raw.size());
    j.number("single_threaded_kernel",1);j.number("matrix_passes",op=="combined"?2:1);
    j.boolean("trit_digest_enabled",act.digest_on);
    j.boolean("same_matrix_replay_digest_verified",false);
    j.boolean("same_descriptor_or_payload_replayed",op=="combined");
    j.raw("owned_buffer_accounting",mem.str());j.raw("timing_seconds",timing.str());j.number("trit_digest",act.digest);j.number("eval_digest",edigest);
    j.raw("adj_digests",array_json(adigests));j.raw("counts",count_json(c,n,k,entries,unsigned(ev)+ac));
    if(op=="combined"||op=="eval")j.raw("counts_Eval",count_json(eval_counts,n,k,entries,1));
    if(op=="combined"||op=="adj3")j.raw("counts_Adj3",count_json(adj_counts,n,k,entries,3));
    return j.str();
}
int main(int argc,char**argv){
    try{
        require(argc>=2,"usage: nisan_operator selftest|vector|bench [--name value ...]");
        Args a=args_read(argc,argv);std::string command=argv[1],result;
        if(command=="selftest")result=selftest();else if(command=="vector")result=vector_run(a);else if(command=="bench")result=bench(a);else throw std::runtime_error("unknown command");
        emit(result,a);return 0;
    }catch(const std::exception& e){std::cerr<<"error: "<<e.what()<<"\n";return 1;}
}
