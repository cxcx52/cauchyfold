#define main reference_main
#include "primitives.cpp"
#undef main

struct DirectFixture {
 int k;std::vector<State> states;std::vector<E> values,weights;E c;
 DirectFixture(int kk,int variant=0,bool invalid=false):k(kk){
  std::mt19937_64 rng(0xC0A1024);states.resize(k+2);
  for(int i=0;i<=k;i++){
   auto&s=states[i];s[0]=scalar(i?1:2);
   for(int j=0;j<4;j++){
    for(int l=0;l<8;l++){int t=ia(j,l);s[t]=scalar(rng()%q);s[t+1]=scalar(rng()%q);
     if(!i)for(int h=1;h<4;h++){s[t][h]=rng()%q;s[t+1][h]=rng()%q;}}
    if(!i)for(auto&x:s[1+j])x=rng()%q;
    else {E z=zero;for(int l=0;l<8;l++)z=ea(z,em(s[ia(j,l)],s[ia(j,l)+1]));s[1+j]=z;}
   }
   auto e=quadratic(s);for(int j=0;j<4;j++)s[69+j]=e[j];
  }
  if(invalid)states[1][1]=ea(states[1][1],one);
  c=variant?E{U(k+19),7,11,13}:E{U(k+17),3,4,5};
  std::vector<E>prefix(k+1,one),diff(k);for(int i=0;i<k;i++){diff[i]=es(c,scalar(i));prefix[i+1]=em(prefix[i],diff[i]);}
  E t=inv(prefix[k]);weights.resize(k);for(int i=k-1;i>=0;i--){weights[i]=em(t,prefix[i]);t=em(t,diff[i]);}
  auto&out=states[k+1];out=states[0];
  for(int i=0;i<k;i++)for(int j=0;j<69;j++)out[j]=ea(out[j],em(weights[i],states[i+1][j]));
  auto e=quadratic(out);for(int j=0;j<4;j++)out[69+j]=e[j];
  for(auto&s:states)for(auto&x:s)values.push_back(x);
 }
};

struct ActiveDirect {
 DirectFixture&f;size_t stride=60,free=0,onecol,used;std::vector<int64_t>index;std::vector<uint8_t>witness;
 bool isfixed(size_t g)const{size_t v=g/4,t=g%4,s=v/73,j=v%73;return s>=1&&s<=size_t(f.k)&&(j==0||j>=69||t>0);}
 U constant(size_t g)const{return (g/4)%73==0&&g%4==0?1:0;}
 ActiveDirect(DirectFixture&ff):f(ff){
  index.assign(4*f.values.size(),-1);for(size_t g=0;g<index.size();g++)if(!isfixed(g))index[g]=free++;
  ensure(free==68*U(f.k)+584,"active coefficients");onecol=60*free;used=onecol+1;witness.assign(used,0);witness[onecol]=1;
  for(size_t g=0;g<index.size();g++){
   U x=f.values[g/4][g%4];if(isfixed(g)){ensure(x==constant(g),"fixed coordinate");continue;}
   size_t b=60*index[g];for(int j=0;j<48;j++)witness[b+j]=(x>>j)&1;
   unsigned zeros=42-__builtin_popcountll(x>>6);for(int j=0;j<6;j++)witness[b+48+j]=(zeros>>j)&1;
   witness[b+54]=(1-witness[b+48])*(1-witness[b+49]);
   for(int j=2;j<6;j++)witness[b+53+j]=witness[b+52+j]*(1-witness[b+48+j]);
   witness[b+59]=witness[b+58]*witness[b+2];
  }
 }
};

struct PublicCoefficients {
 std::array<std::vector<E>,3>bank;
 PublicCoefficients(const DirectFixture&f){
  for(int i=1;i<=f.k;i++)ensure(f.states[i][0]==one,"invalid public fresh u");
  bank[0].resize(256);for(int t=0;t<4;t++)for(int b=0;b<48;b++){E x=zero;x[t]=U(1)<<b;bank[0][64*t+b]=x;}
  bank[1].resize(5*(f.k+2));for(int s=0;s<f.k+2;s++)for(int j=0;j<5;j++)bank[1][5*s+j]=f.states[s][j];
  bank[2].resize(256*f.k);for(int i=0;i<f.k;i++)for(int t=0;t<4;t++)for(int b=0;b<48;b++)bank[2][256*i+64*t+b]=em(f.weights[i],bank[0][64*t+b]);
 }
 E get(uint32_t x)const{
  unsigned kind=(x>>28)&7,i=(x>>8)&0xfffff,t=(x>>6)&3,b=x&63;ensure(kind<3&&b<48,"coefficient recipe");
  size_t pos=kind==1?i:256*size_t(i)+64*t+b;ensure(pos<bank[kind].size(),"coefficient index");
  E z=bank[kind][pos];return x>>31?es(zero,z):z;
 }
};

struct DirectCompiler {
 DirectFixture&f;ActiveDirect&a;PublicCoefficients cf;MatrixOut A,B,C;ByteOut groups,codes;fs::path out;
 std::map<E,uint32_t>dictionary;std::vector<E>values;size_t terms=0,ngroups=0;bool grouped=false;E residual=zero;
 std::map<std::string,size_t>cats;std::string category;
 DirectCompiler(DirectFixture&ff,ActiveDirect&aa,fs::path p):f(ff),a(aa),cf(ff),A(p/"A"),B(p/"B"),C(p/"C"),groups(p/"groups.u32"),codes(p/"evaluations.u32"),out(p){}
 Form sc(size_t x,bool neg=false,int bit=0){return Form{{uint32_t(x),key(0,0,0,bit,neg)}};}
 Form notbit(size_t x){auto z=sc(a.onecol);z.push_back({uint32_t(x),key(0,0,0,0,true)});return z;}
 E eval(const Form&v){E z=zero;for(auto e:v){ensure(e.col<a.used,"column");if(a.witness[e.col])z=ea(z,scale(cf.get(e.coef),a.witness[e.col]));}return z;}
 uint32_t code(E x){auto it=dictionary.find(x);if(it!=dictionary.end())return it->second;uint32_t i=values.size();values.push_back(x);dictionary[x]=i;return i;}
 void row(const Form&x={},const Form&y={},const Form&z={}){
  E ex=eval(x),ey=eval(y),ez=eval(z),v=es(em(ex,ey),ez);
  if(grouped)residual=ea(residual,v);else ensure(v==zero,"single constraint failed");
  A.row(x);B.row(y);C.row(z);groups.u32(ngroups);for(E u:{ex,ey,ez})codes.u32(code(u));terms++;cats[category]++;
  if(!grouped)ngroups++;
 }
 void linear(Form z){row(sc(a.onecol),z);}
 void dec(Form&v,size_t value,bool neg=false,int kind=0,int ind=0){
  for(int t=0;t<4;t++)for(int b=0;b<48;b++){size_t g=4*value+t;
   if(a.isfixed(g)){if((a.constant(g)>>b)&1)v.push_back({uint32_t(a.onecol),key(kind,ind,t,b,neg)});}
   else v.push_back({uint32_t(60*a.index[g]+b),key(kind,ind,t,b,neg)});
  }
 }
#include "compare.inc"
 void run(){
  for(size_t g=0;g<a.free;g++)compare(60*g);
  category="public";for(int s=0;s<f.k+2;s++)for(int j=0;j<5;j++){
   if(s>=1&&s<=f.k&&j==0)continue;
   Form x;dec(x,73*s+j);x.push_back({uint32_t(a.onecol),key(1,5*s+j,0,0,true)});linear(x);
  }
  category="fold_z";for(int j=0;j<69;j++){Form x;dec(x,73*(f.k+1)+j);dec(x,j,true);for(int i=0;i<f.k;i++)dec(x,73*(i+1)+j,true,2,i);linear(x);}
  category="source_and_output_Q";
  for(int s=0;s<f.k+2;s++)for(int j=0;j<4;j++){
   grouped=true;residual=zero;
   for(int l=0;l<8;l++){Form x,y;dec(x,73*s+ia(j,l));dec(y,73*s+ia(j,l)+1);row(x,y);}
   Form x,y;dec(x,73*s,true);dec(y,73*s+1+j);row(x,y);
   if(s==0||s==f.k+1){Form z;dec(z,73*s+69+j);row({}, {},z);}
   ensure(residual==zero,"grouped Q equation failed");ngroups++;grouped=false;
  }
  ensure(ngroups==4292*U(f.k)+36879&&terms==4324*U(f.k)+36951,"dimension formulas");
  ByteOut dict(out/"dictionary.u64"),w(out/"witness.u8");dict.put(values.data(),32*values.size());w.put(a.witness.data(),a.used);
  size_t wt=0;for(auto b:a.witness)wt+=b;ensure(wt<=49*a.free+1,"norm");
  std::ofstream j(out/"compiler.json");j<<"{\"arity\":"<<f.k<<",\"groups\":"<<ngroups<<",\"terms\":"<<terms<<",\"columns\":"<<a.used<<",\"free_coefficients\":"<<a.free<<",\"S0\":"<<49*a.free+1<<",\"honest_weight\":"<<wt<<",\"nnz\":["<<A.nnz<<","<<B.nnz<<","<<C.nnz<<"],\"all_groups_checked\":true,\"dictionary_size\":"<<values.size()<<",\"carrier_constructed\":false}\n";
 }
};

E evalrow(MatrixIn&m,size_t row,const std::vector<uint8_t>&w,const PublicCoefficients&cf){
 E z=zero;for(size_t t=m.p[row];t<m.p[row+1];t++){auto e=m.e[t];ensure(e.col<w.size(),"CSR column");if(w[e.col])z=ea(z,scale(cf.get(e.coef),w[e.col]));}return z;
}

void verify(int k,fs::path dir,int variant,int mutation){
 DirectFixture f(k,variant,mutation==3);if(mutation==4)f.values[73*(k+1)+69]=ea(f.values[73*(k+1)+69],one);ActiveDirect a(f);PublicCoefficients cf(f);
 if(mutation==1)a.witness[0]=2;if(mutation==2)a.witness[48]^=1;
 MatrixIn A(dir/"A"),B(dir/"B"),C(dir/"C");Mapping gids(dir/"groups.u32"),codes(dir/"evaluations.u32"),dictionary(dir/"dictionary.u64");
 auto id=(const uint32_t*)gids.data,cd=(const uint32_t*)codes.data;auto dict=(const E*)dictionary.data;
 ensure(A.rows==B.rows&&B.rows==C.rows&&gids.size==4*A.rows&&codes.size==12*A.rows,"artifact sizes");
 E residual=zero;size_t bad=0,ng=0;for(size_t row=0;row<A.rows;row++){
  E av=evalrow(A,row,a.witness,cf),bv=evalrow(B,row,a.witness,cf),cv=evalrow(C,row,a.witness,cf);
  if(!variant&&!mutation)for(int t=0;t<3;t++){ensure(cd[3*row+t]<dictionary.size/32,"dictionary index");ensure(dict[cd[3*row+t]]==(t==0?av:t==1?bv:cv),"CSR evaluation differs from compiled table");}
  residual=ea(residual,es(em(av,bv),cv));
  if(row+1==A.rows||id[row+1]!=id[row]){ensure(id[row]==ng,"group ordering");bad+=residual!=zero;residual=zero;ng++;}
 }
 ensure(mutation?bad>0:bad==0,"verification result");
 std::ofstream out(dir/("verification-"+std::to_string(variant)+"-"+std::to_string(mutation)+".json"));
 out<<"{\"all_CSR_terms_evaluated\":true,\"groups\":"<<ng<<",\"terms\":"<<A.rows<<",\"invalid_groups\":"<<bad<<",\"challenge_variant\":"<<variant<<",\"mutation\":"<<mutation<<",\"PASS\":true}\n";
}

#ifndef DIRECT_LIBRARY
int main(int argc,char**argv){try{
 ensure(argc>=4,"usage: direct compile|verify|second|negative k directory");int k=std::stoi(argv[2]);ensure(k>0&&k<=1024,"arity");fs::path dir=argv[3];fs::create_directories(dir);std::string op=argv[1];
 if(op=="compile"){DirectFixture f(k);ActiveDirect a(f);DirectCompiler compiler(f,a,dir);compiler.run();}
 else if(op=="verify")verify(k,dir,0,0);
 else if(op=="second")verify(k,dir,1,0);
 else if(op=="negative"){
  for(int m=1;m<=4;m++)verify(k,dir,0,m);
  DirectFixture f(k);f.states[1][0]=scalar(2);bool rejected=false;
  try{PublicCoefficients cf(f);}catch(const std::exception&){rejected=true;}
  ensure(rejected,"public fresh u must be one");std::ofstream out(dir/"public-input-check.json");out<<"{\"invalid_fresh_u_rejected\":true}\n";
 }
 else throw std::runtime_error("unknown operation");
 std::cout<<"PASS "<<op<<" k="<<k<<"\n";
}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
#endif
