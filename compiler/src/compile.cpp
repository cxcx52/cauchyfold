#define main original_tool_main
#include "arithmetic.cpp"
#undef main

void validate_public_fresh_u(const std::vector<E>&pub,int k){
 ensure(pub.size()==size_t(5*(k+2)),"public input shape");
 for(int s=1;s<=k;s++)ensure(pub[5*s]==one,"invalid public fresh homogenizing coordinate");
}

struct Active {
 Fixture& f;bool special;size_t stride,helpers,free=0,onecol,used,physical;
 std::vector<int64_t> index;std::vector<uint8_t> witness,fixed,full;
 std::vector<uint32_t> insertion;
 Active(Fixture& ff,bool sp):f(ff),special(sp),stride(sp?60:96),helpers(sp?12:48){
  index.assign(4*f.V,-1);
  for(size_t g=0;g<index.size();g++)if(!isfixed(g))index[g]=free++;
  ensure(free==84*U(f.k)+728,"free coefficient count");onecol=stride*free;used=onecol+1;
  physical=192*f.V+helpers*4*f.V;witness.assign(used,0);fixed.assign(physical,0);full.assign(physical,0);
  insertion.resize(onecol);witness[onecol]=1;
  for(size_t g=0;g<index.size();g++){
   U x=f.values[g/4][g%4];auto h=help(x);ensure(h.size()==helpers,"helper count");
   if(isfixed(g))ensure(x==constant(g),"invalid fixed fresh coordinate");
   for(size_t j=0;j<stride;j++){
    size_t p=j<48?48*g+j:192*f.V+helpers*g+j-48;
    uint8_t bit=j<48?((x>>j)&1):h[j-48];full[p]=bit;
    if(isfixed(g))fixed[p]=bit;
    else{size_t a=stride*index[g]+j;witness[a]=bit;insertion[a]=p;}
   }
  }
  U energy=0;for(auto b:witness)energy+=b;
  ensure(energy<=(special?49:90)*free+1,"honest active energy");
 }
 bool isfixed(size_t g)const{
  size_t v=g/4,t=g%4,s=v/73,j=v%73;
  return s>=1&&s<=size_t(f.k)&&(j==0||j>=69||t>0);
 }
 U constant(size_t g)const{return (g/4)%73==0&&g%4==0?1:0;}
 std::vector<uint8_t> help(U x)const{
  if(!special){std::vector<uint8_t>h(48);int e=1;for(int j=47;j>=0;j--){e*=((x>>j)&1)==((q>>j)&1);h[j]=e;}return h;}
  unsigned s=42-__builtin_popcountll(x>>6);std::vector<uint8_t>h(12);
  for(int j=0;j<6;j++)h[j]=(s>>j)&1;
  h[6]=(1-h[0])*(1-h[1]);for(int j=2;j<6;j++)h[5+j]=h[4+j]*(1-h[j]);
  h[11]=h[10]*((x>>2)&1);return h;
 }
 void save(const fs::path&dir){
  ByteOut w(dir/"witness.u8"),fix(dir/"fixed.u8"),packed(dir/"physical.u8"),ins(dir/"insertion.u32");
  w.put(witness.data(),witness.size());fix.put(fixed.data(),fixed.size());packed.put(full.data(),full.size());
  ins.put(insertion.data(),insertion.size()*4);
  ByteOut values(dir/"values.u64");values.put(f.values.data(),f.values.size()*sizeof(E));
 }
};

struct ReducedCompiler {
 Fixture& f;Active& a;Coefficients cf;MatrixOut A,B,C;ByteOut codes;std::vector<E> dict{zero,one,scalar(q-1)};
 uint64_t rows=0;std::map<std::string,uint64_t>cats;std::string category;fs::path out;
 ReducedCompiler(Fixture&ff,Active&aa,fs::path p):f(ff),a(aa),cf(f),A(p/"A"),B(p/"B"),C(p/"C"),codes(p/"evaluation_codes.u8"),out(p){}
 Form sc(size_t x,bool neg=false,int bit=0){return Form{{uint32_t(x),key(0,0,0,bit,neg)}};}
 Form notbit(size_t x){Form b=sc(a.onecol);b.push_back({uint32_t(x),key(0,0,0,0,true)});return b;}
 E eval(const Form&v){E r=zero;for(auto x:v){ensure(x.col<a.used,"active column");if(a.witness[x.col])r=ea(r,scale(cf.get(x.coef),a.witness[x.col]));}return r;}
 uint8_t code(E x){auto p=std::find(dict.begin(),dict.end(),x);if(p==dict.end()){ensure(dict.size()<256,"dictionary limit");dict.push_back(x);return dict.size()-1;}return p-dict.begin();}
 void row(const Form&x={},const Form&y={},const Form&z={}){
  E ex=eval(x),ey=eval(y),ez=eval(z);ensure(em(ex,ey)==ez,"reduced R1CS row");
  A.row(x);B.row(y);C.row(z);uint8_t c[3]={code(ex),code(ey),code(ez)};codes.put(c,3);rows++;cats[category]++;
 }
 void linear(Form b){row(sc(a.onecol),b);}
 void dec(Form&v,size_t value,bool neg=false,int kind=0,int ind=0,int comp=-1){
  for(int t=0;t<4;t++)if(comp<0||t==comp){size_t g=4*value+t;
   for(int b=0;b<48;b++){
    if(a.isfixed(g)){if((a.constant(g)>>b)&1)v.push_back({uint32_t(a.onecol),key(kind,ind,t,b,neg)});}
    else v.push_back({uint32_t(a.stride*a.index[g]+b),key(kind,ind,t,b,neg)});
   }
  }
 }
 void compare(size_t base){
  category="value_boolean";for(int j=0;j<48;j++)row(sc(base+j),Form{{uint32_t(base+j),key()},{uint32_t(a.onecol),key(0,0,0,0,true)}});
  if(a.special){
   size_t h=base+48;category="count_boolean";for(int j=0;j<6;j++)row(sc(h+j),Form{{uint32_t(h+j),key()},{uint32_t(a.onecol),key(0,0,0,0,true)}});
   category="zero_count";Form b;for(int j=0;j<6;j++)b.push_back({uint32_t(h+j),key(0,0,0,j)});
   for(int j=6;j<48;j++)b.push_back({uint32_t(base+j),key()});
   for(int j:{1,3,5})b.push_back({uint32_t(a.onecol),key(0,0,0,j,true)});
   linear(b);
   category="zero_test_product";row(notbit(h),notbit(h+1),sc(h+6));
   for(int j=2;j<6;j++)row(sc(h+4+j),notbit(h+j),sc(h+5+j));
   category="masked_bit";row(sc(h+10),sc(base+2),sc(h+11));
   category="low_restrictions";row(sc(h+10),Form{{uint32_t(base+3),key()},{uint32_t(base+4),key()},{uint32_t(base+5),key()}});
   row(sc(h+11),Form{{uint32_t(base),key()},{uint32_t(base+1),key()}});
  }else{
   for(int j=47;j>=0;j--){size_t next=j==47?a.onecol:base+48+j+1;category="prefix_recurrence";
    row(sc(next),(q>>j)&1?sc(base+j):notbit(base+j),sc(base+48+j));
    if(!((q>>j)&1)){category="first_difference";row(sc(next),sc(base+j));}
   }
   category="exclude_q";linear(sc(base+48));
  }
 }
 void run(){
  validate_public_fresh_u(cf.bank[1],f.k);
  for(size_t g=0;g<a.free;g++)compare(a.stride*g);
  category="public_coordinates";
  for(int s=0;s<f.k+2;s++)for(int j=0;j<5;j++){
   if(s>=1&&s<=f.k&&j==0){ensure(cf.bank[1][5*s]==one,"invalid public fresh u");continue;}
   Form b;dec(b,73*s+j);b.push_back({uint32_t(a.onecol),key(1,5*s+j,0,0,true)});linear(b);
  }
  size_t os=73*(f.k+1),hs=73*(f.k+2),aux=hs+4*f.k;
  category="folded_z";for(int j=0;j<69;j++){Form b;dec(b,os+j);dec(b,j,true);for(int i=0;i<f.k;i++)dec(b,73*(i+1)+j,true,2,i);linear(b);}
  category="folded_E";for(int j=0;j<4;j++){Form b;dec(b,os+69+j);dec(b,69+j,true);for(int i=0;i<f.k;i++)dec(b,73*(i+1)+69+j,true,3,i);for(int i=0;i<f.k;i++)dec(b,hs+4*i+j,true,4,i);linear(b);}
  category="Q_products";for(int j=0;j<4;j++)for(int l=0;l<9;l++){int x=l<8?ia(j,l):0,y=l<8?ia(j,l)+1:j+1;Form aa,bb,cc;dec(aa,os+x);dec(bb,os+y);dec(cc,aux+9*j+l);row(aa,bb,cc);}
  category="Q_output";for(int j=0;j<4;j++){Form b;for(int l=0;l<9;l++)dec(b,aux+9*j+l,l==8);dec(b,os+69+j,true);linear(b);}
  ensure(rows==(a.special?5296:8488)*U(f.k)+(a.special?45987:73651),"row count");
  ByteOut dd(out/"evaluation_dictionary.u64");dd.put(dict.data(),dict.size()*sizeof(E));a.save(out);
  U energy=0,fixedenergy=0;for(auto x:a.witness)energy+=x;for(auto x:a.fixed)fixedenergy+=x;
  size_t auxbits=6912+a.helpers*4*f.V,auxcols=(auxbits+63)/64;
  std::ofstream js(out/"compiler.json");js<<"{\"k\":"<<f.k<<",\"special\":"<<(a.special?"true":"false")<<",\"rows\":"<<rows<<",\"columns\":"<<a.used<<",\"free_coefficients\":"<<a.free<<",\"physical_bits\":"<<a.physical<<",\"auxiliary_bits\":"<<auxbits<<",\"auxiliary_columns\":"<<auxcols<<",\"auxiliary_padding\":"<<64*auxcols-auxbits<<",\"honest_energy\":"<<energy<<",\"fixed_energy\":"<<fixedenergy<<",\"energy_bound\":"<<(a.special?49:90)*a.free+1<<",\"nnz\":["<<A.nnz<<","<<B.nnz<<","<<C.nnz<<"],\"all_generated_rows_checked\":true,\"categories\":{";
  bool first=true;for(auto p:cats){if(!first)js<<",";first=false;js<<"\""<<p.first<<"\":"<<p.second;}js<<"}}\n";
 }
};

void verify_active(Fixture&f,Active&a,fs::path dir,bool second,int mutation){
 Coefficients cf(f);auto w=a.witness;
 if(!second){std::ifstream in(dir/"witness.u8",std::ios::binary);in.read((char*)w.data(),w.size());ensure(size_t(in.gcount())==w.size()&&in.peek()==EOF,"stored witness length");}
 if(mutation==1)w[0]=2;if(mutation==2)w[48]^=1;if(mutation==3)w[a.onecol]=0;
 validate_public_fresh_u(cf.bank[1],f.k);
 if(w[a.onecol]!=1){if(mutation==3)return;throw std::runtime_error("fixed-one coordinate");}
 ensure(mutation!=3,"constant mutation failed to change witness");
 MatrixIn A(dir/"A"),B(dir/"B"),C(dir/"C");ensure(A.rows==B.rows&&A.rows==C.rows,"matrix row count");
 Mapping codes(dir/"evaluation_codes.u8"),dictfile(dir/"evaluation_dictionary.u64");auto ids=(const uint8_t*)codes.data;auto dict=(const E*)dictfile.data;
 ensure(codes.size==3*A.rows,"evaluation table length");size_t failed=A.rows;
 for(size_t r=0;r<A.rows;r++){
  E x=A.eval(r,w,cf),y=B.eval(r,w,cf),z=C.eval(r,w,cf);
  if(em(x,y)!=z){failed=r;break;}
  if(!second&&!mutation)ensure(x==dict[ids[3*r]]&&y==dict[ids[3*r+1]]&&z==dict[ids[3*r+2]],"CSR/evaluation match");
 }
 if(mutation){ensure(failed<A.rows,"tampered active witness accepted");return;}
 ensure(failed==A.rows,"active CSR verification");
 std::ofstream j(dir/(second?"second_challenge.json":"verification.json"));j<<"{\"all_rows_verified\":true,\"rows\":"<<A.rows<<",\"second_challenge\":"<<(second?"true":"false")<<"}\n";
}

 #ifndef CF_LIBRARY
int main(int argc,char**argv){try{
 ensure(argc>=5,"usage: compiler compile|verify|second|negative k prefix|special directory");
 std::string op=argv[1],mode=argv[3];int k=std::stoi(argv[2]);ensure(k>0&&k<=1024,"arity");ensure(mode=="prefix"||mode=="special","mode");
 fs::path dir=argv[4];fs::create_directories(dir);Fixture f(k,0,op=="second");Active a(f,mode=="special");
 if(op=="compile"){ReducedCompiler compiler(f,a,dir);compiler.run();}
 else if(op=="verify"||op=="second")verify_active(f,a,dir,op=="second",0);
 else if(op=="negative"){
  for(int m=1;m<=3;m++)verify_active(f,a,dir,false,m);
  Coefficients cf(f);cf.bank[1][5]=zero;bool rejected=false;
  try{validate_public_fresh_u(cf.bank[1],k);}catch(const std::exception&){rejected=true;}
  ensure(rejected,"invalid public input accepted");
  std::ofstream j(dir/"negative.json");j<<"{\"rejected_mutations\":4,\"invalid_public_fresh_u_rejected\":true}\n";
 }
 else throw std::runtime_error("unknown operation");
 std::cout<<"PASS "<<op<<" k="<<k<<" "<<mode<<"\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;}}

#endif
