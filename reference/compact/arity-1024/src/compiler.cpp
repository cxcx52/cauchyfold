// Complete arity-parametric sparse field compiler and independent CSR evaluator.
// Test fixtures use deterministic randomness; they are NOT production setup coins.
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
#include <boost/multiprecision/cpp_int.hpp>
using U=uint64_t; using Wide=__uint128_t; namespace fs=std::filesystem;
constexpr U q=(U(1)<<48)-59,mask=(U(1)<<48)-1;
U add(U a,U b){U x=a+b;return x>=q?x-q:x;}
U sub(U a,U b){return a>=b?a-b:q-(b-a);}
U mul(U a,U b){Wide p=Wide(a)*b;U t=U(p&mask)+59*U(p>>48);U x=(t&mask)+59*(t>>48);return x>=q?x-q:x;}
U power(U a,U n){U b=1;for(;n;n>>=1,a=mul(a,a))if(n&1)b=mul(b,a);return b;}
using E=std::array<U,4>; const E zero{0,0,0,0},one{1,0,0,0};
E scalar(U a){return E{a,0,0,0};}
E ea(E a,const E&b){for(int i=0;i<4;i++)a[i]=add(a[i],b[i]);return a;}
E es(E a,const E&b){for(int i=0;i<4;i++)a[i]=sub(a[i],b[i]);return a;}
E scale(E a,U b){for(auto&x:a)x=mul(x,b);return a;}
E em(const E&a,const E&b){
 if(!(a[1]|a[2]|a[3]))return scale(b,a[0]);
 if(!(b[1]|b[2]|b[3]))return scale(a,b[0]);
 U t[7]={};for(int i=0;i<4;i++)for(int j=0;j<4;j++)t[i+j]=add(t[i+j],mul(a[i],b[j]));
 for(int j=6;j>=4;j--){t[j-2]=add(t[j-2],mul(4,t[j]));t[j-4]=sub(t[j-4],mul(2,t[j]));}
 return E{t[0],t[1],t[2],t[3]};
}
E inv(E a){if(a==zero)throw std::runtime_error("inverse of zero");
 boost::multiprecision::cpp_int e=q;e=e*e*e*e-2;E b=one;
 for(;e!=0;e>>=1,a=em(a,a))if((e&1)!=0)b=em(b,a);
 return b;
}
using State=std::array<E,73>;
int ia(int j,int l){return 5+16*j+2*l;}
std::array<E,4> quadratic(const State&s){std::array<E,4> out{};
 for(int j=0;j<4;j++){E a=zero;for(int l=0;l<8;l++)a=ea(a,em(s[ia(j,l)],s[ia(j,l)+1]));out[j]=es(a,em(s[0],s[1+j]));}return out;}
std::array<E,4> bilinear(const State&a,const State&b){std::array<E,4> out{};
 for(int j=0;j<4;j++){E x=zero;for(int l=0;l<8;l++){int t=ia(j,l);x=ea(x,ea(em(a[t],b[t+1]),em(b[t],a[t+1])));}out[j]=es(es(x,em(a[0],b[1+j])),em(b[0],a[1+j]));}return out;}
void ensure(bool b,const char*s){if(!b)throw std::runtime_error(s);}
struct Fixture{
 int k;size_t V,B,used,cap,carrier_start,aux_start;std::vector<State> states;
 std::vector<std::array<E,4>> H;std::vector<E> values,weights,squares,cw;std::vector<uint8_t> bits;E c;
 Fixture(int kk,size_t capacity,int variant=0):k(kk){
  V=77*size_t(k)+182;B=192*V;used=2*B+1;cap=capacity?capacity:used;
  ensure(cap>=used && cap<(U(1)<<32),"bad capacity");
  carrier_start=192*73*(k+2);aux_start=carrier_start+192*4*k;
  std::mt19937_64 rng(0xC0A1024);states.resize(k+2);
  for(int i=0;i<=k;i++){
   auto&s=states[i];s[0]=scalar(i?1:2);
   for(int j=0;j<4;j++){
    for(int l=0;l<8;l++){int t=ia(j,l);s[t]=scalar(rng()%q);s[t+1]=scalar(rng()%q);
     if(!i)for(int h=1;h<4;h++){s[t][h]=rng()%q;s[t+1][h]=rng()%q;}}
    if(!i)for(auto&x:s[1+j])x=rng()%q;
    else{E t=zero;for(int l=0;l<8;l++)t=ea(t,em(s[ia(j,l)],s[ia(j,l)+1]));s[1+j]=t;}
   }
   auto e=quadratic(s);for(int j=0;j<4;j++)s[69+j]=e[j];
   if(i)ensure(e==std::array<E,4>{},"fresh relation invalid");
  }
  // Independent direct-residue construction, O(k^2*n), NOT a fast-tree benchmark.
  std::vector<U> inverses(k);for(int i=1;i<k;i++)inverses[i]=power(i,q-2);
  std::vector<U> dp(1,1);
  for(int i=0;i<k;i++){std::vector<U> z(dp.size()+1);for(size_t j=0;j<dp.size();j++){z[j]=sub(z[j],mul(i,dp[j]));z[j+1]=add(z[j+1],dp[j]);}dp.swap(z);}
  H.resize(k);
  for(int i=0;i<k;i++){
   State v=states[0];
   for(int j=0;j<k;j++)if(i!=j){U a=i>j?inverses[i-j]:q-inverses[j-i];for(int h=0;h<69;h++)v[h][0]=add(v[h][0],mul(a,states[j+1][h][0]));}
   auto R=bilinear(states[i+1],v);std::vector<U> P(k);P[k-1]=1;
   for(int t=k-1;t>0;t--)P[t-1]=add(dp[t],mul(i,P[t]));
   ensure(add(dp[0],mul(i,P[0]))==0,"pole division remainder");
   for(int t=0;t<k;t++)for(int j=0;j<4;j++)H[t][j]=ea(H[t][j],scale(R[j],P[t]));
  }
  c=variant?E{U(k+19),7,11,13}:E{U(k+17),3,4,5};
  std::vector<E> pref(k+1,one),diff(k);for(int i=0;i<k;i++){diff[i]=es(c,scalar(i));pref[i+1]=em(pref[i],diff[i]);}
  E dinv=inv(pref[k]);ensure(em(dinv,pref[k])==one,"field inverse");E r=dinv;
  weights.resize(k);squares.resize(k);cw.resize(k);E cp=one;
  for(int i=k-1;i>=0;i--){weights[i]=em(r,pref[i]);r=em(r,diff[i]);}
  for(int i=0;i<k;i++){ensure(em(weights[i],diff[i])==one,"Cauchy weights");squares[i]=em(weights[i],weights[i]);cw[i]=em(dinv,cp);cp=em(cp,c);}
  auto&out=states[k+1];out=states[0];
  for(int i=0;i<k;i++)for(int j=0;j<73;j++)out[j]=ea(out[j],em(j<69?weights[i]:squares[i],states[i+1][j]));
  for(int t=0;t<k;t++)for(int j=0;j<4;j++)out[69+j]=ea(out[69+j],em(cw[t],H[t][j]));
  auto oe=quadratic(out);for(int j=0;j<4;j++)ensure(oe[j]==out[69+j],"carrier identity");
  for(auto&s:states)for(auto&x:s)values.push_back(x);
  for(auto&h:H)for(auto&x:h)values.push_back(x);
  for(int j=0;j<4;j++){for(int l=0;l<8;l++)values.push_back(em(out[ia(j,l)],out[ia(j,l)+1]));values.push_back(em(out[0],out[1+j]));}
  ensure(values.size()==V,"value count");bits.assign(cap,0);
  for(size_t vi=0;vi<V;vi++)for(int t=0;t<4;t++){U x=values[vi][t];int e=1;for(int b=47;b>=0;b--){int z=(x>>b)&1;bits[192*vi+48*t+b]=z;e*=z==int((q>>b)&1);bits[B+192*vi+48*t+b]=e;}}
  bits[used-1]=1;
 }
};
uint32_t key(int kind=0,int index=0,int basis=0,int bit=0,bool neg=false){
 ensure(kind>=0&&kind<=4&&index>=0&&index<(1<<20)&&basis>=0&&basis<4&&bit>=0&&bit<48,"coefficient key overflow");
 return (uint32_t(neg)<<31)|(uint32_t(kind)<<28)|(uint32_t(index)<<8)|(basis<<6)|bit;
}
// Separate bank uses 256 slots per item so bit-fields index directly.
struct Coefficients{
 std::array<std::vector<E>,5> bank;
 Coefficients(const Fixture&f){
  bank[0].resize(256);for(int t=0;t<4;t++)for(int b=0;b<48;b++){E a=zero;a[t]=U(1)<<b;bank[0][t*64+b]=a;}
  bank[1].resize((f.k+2)*5);for(int s=0;s<f.k+2;s++)for(int j=0;j<5;j++)bank[1][5*s+j]=f.states[s][j];
  const std::vector<E>* ws[3]={&f.weights,&f.squares,&f.cw};
  for(int kind=2;kind<5;kind++){
   bank[kind].resize(256*f.k);
   for(int i=0;i<f.k;i++)for(int t=0;t<4;t++)for(int b=0;b<48;b++)bank[kind][256*i+64*t+b]=em((*ws[kind-2])[i],bank[0][64*t+b]);
  }
 }
 E get(uint32_t code)const{
  unsigned kind=(code>>28)&7,index=(code>>8)&0xfffff,t=(code>>6)&3,b=code&63;
  ensure(kind<5&&b<48,"invalid recipe");size_t p=kind==1?index:256*size_t(index)+64*t+b;
  ensure(p<bank[kind].size()&&(kind!=1||(t==0&&b==0)),"recipe index out of bounds");
  const E&a=bank[kind][p];return code>>31?es(zero,a):a;
 }
};
struct ByteOut{
 std::ofstream s;std::vector<char>b;size_t pos=0;
 ByteOut(const fs::path&p):s(p,std::ios::binary),b(1<<20){ensure(bool(s),"cannot open output");}
 void put(const void*p,size_t n){const char*x=(const char*)p;while(n){size_t a=std::min(n,b.size()-pos);std::copy(x,x+a,b.data()+pos);pos+=a;x+=a;n-=a;if(pos==b.size())flush();}}
 void u32(uint32_t x){put(&x,4);}void flush(){if(pos){s.write(b.data(),pos);ensure(bool(s),"write failed");pos=0;}}
 ~ByteOut(){flush();}
};
struct Entry{uint32_t col,coef;};using Form=std::vector<Entry>;
struct MatrixOut{
 ByteOut ptr,ent;uint64_t nnz=0;
 MatrixOut(fs::path p):ptr(p.string()+".ptr"),ent(p.string()+".ent"){ptr.u32(0);}
 void row(const Form&x){nnz+=x.size();ensure(nnz<0xffffffff,"CSR offset overflow");ent.put(x.data(),x.size()*8);ptr.u32(uint32_t(nnz));}
};
struct Compiler{
 Fixture& f;Coefficients cf;MatrixOut A,B,C;ByteOut codes;std::vector<E> dict{zero,one,scalar(q-1)};
 uint64_t rows=0;std::map<std::string,uint64_t> cats;std::string category;fs::path out;
 Compiler(Fixture&ff,fs::path pp):f(ff),cf(f),A(pp/"A"),B(pp/"B"),C(pp/"C"),codes(pp/"evaluation_codes.u8"),out(pp){}
 uint8_t code(const E&a){if(a==zero)return 0;if(a==one)return 1;if(a==scalar(q-1))return 2;
  auto it=std::find(dict.begin(),dict.end(),a);if(it==dict.end()){ensure(dict.size()<256,"evaluation dictionary capacity");dict.push_back(a);return uint8_t(dict.size()-1);}return uint8_t(it-dict.begin());}
 E eval(const Form&a){E v=zero;for(const auto&x:a){ensure(x.col<f.cap,"column bounds");if(f.bits[x.col])v=ea(v,scale(cf.get(x.coef),f.bits[x.col]));}return v;}
 Form sc(size_t x,bool neg=false){return Form{{uint32_t(x),key(0,0,0,0,neg)}};}
 void dec(Form&v,size_t start,bool neg=false,int kind=0,int index=0,int comp=-1){
  for(int t=0;t<4;t++)if(comp<0||t==comp)for(int b=0;b<48;b++)v.push_back({uint32_t(start+48*t+b),key(kind,index,t,b,neg)});
 }
 void row(const Form&a={},const Form&b={},const Form&c={}){
  E va=eval(a),vb=eval(b),vc=eval(c);ensure(em(va,vb)==vc,"generated R1CS row failed");
  A.row(a);B.row(b);C.row(c);uint8_t x[3]={code(va),code(vb),code(vc)};codes.put(x,3);rows++;cats[category]++;
 }
 void lin(const Form&b){row(sc(f.used-1),b,{});}
 void run(){
  category="private_bit_boolean";
  for(size_t x=0;x<f.used-1;x++){Form b=sc(x);b.push_back({uint32_t(f.used-1),key(0,0,0,0,true)});row(sc(x),b);}
  for(size_t vi=0;vi<f.V;vi++)for(int t=0;t<4;t++){
   size_t base=f.B+192*vi+48*t;
   for(int b=47;b>=0;b--){size_t bit=192*vi+48*t+b,next=b==47?f.used-1:base+b+1;
    category="canonical_prefix_recurrence";
    if((q>>b)&1)row(sc(next),sc(bit),sc(base+b));
    else{Form v=sc(f.used-1);v.push_back({uint32_t(bit),key(0,0,0,0,true)});row(sc(next),v,sc(base+b));category="canonical_first_difference";row(sc(next),sc(bit));}
   }
   category="canonical_exclude_q";lin(sc(base));
  }
  category="public_coordinates";
  for(int s=0;s<f.k+2;s++)for(int j=0;j<5;j++){Form b;dec(b,192*(73*s+j));b.push_back({uint32_t(f.used-1),key(1,5*s+j,0,0,true)});lin(b);}
  category="strict_fresh_u_and_E";
  for(int s=1;s<=f.k;s++){
   Form b;dec(b,192*73*s);b.push_back({uint32_t(f.used-1),key(0,0,0,0,true)});lin(b);
   for(int j=0;j<4;j++){Form z;dec(z,192*(73*s+69+j));lin(z);}
  }
  category="strict_fresh_base_field";
  for(int s=1;s<=f.k;s++)for(int j=0;j<69;j++)for(int t=1;t<4;t++){Form b;dec(b,192*(73*s+j),false,0,0,t);lin(b);}
  size_t os=192*73*(f.k+1);
  category="folded_z";
  for(int j=0;j<69;j++){Form b;dec(b,os+192*j);dec(b,192*j,true);for(int i=0;i<f.k;i++)dec(b,192*(73*(i+1)+j),true,2,i);lin(b);}
  category="folded_E";
  for(int j=0;j<4;j++){Form b;dec(b,os+192*(69+j));dec(b,192*(69+j),true);
   for(int i=0;i<f.k;i++)dec(b,192*(73*(i+1)+69+j),true,3,i);
   for(int i=0;i<f.k;i++){dec(b,f.carrier_start+192*(4*i+j),true,4,i);}lin(b);}
  category="Q_product_gates";
  for(int j=0;j<4;j++)for(int l=0;l<9;l++){int a=l<8?ia(j,l):0,b=l<8?ia(j,l)+1:j+1;Form aa,bb,cc;dec(aa,os+192*a);dec(bb,os+192*b);dec(cc,f.aux_start+192*(9*j+l));row(aa,bb,cc);}
  category="Q_linear_output";
  for(int j=0;j<4;j++){Form b;for(int l=0;l<9;l++)dec(b,f.aux_start+192*(9*j+l),l==8);dec(b,os+192*(69+j),true);lin(b);}
  category="fixed_zero_handoff_coordinates";for(size_t x=f.used;x<f.cap;x++)lin(sc(x));
  ensure(rows==46109*U(f.k)+108595+f.cap-f.used,"compiler count formula mismatch");
  ByteOut vals(out/"values.u64");vals.put(f.values.data(),f.values.size()*sizeof(E));
  ByteOut wb(out/"witness.u8");wb.put(f.bits.data(),f.bits.size());
  ByteOut dd(out/"evaluation_dictionary.u64");dd.put(dict.data(),dict.size()*sizeof(E));
  std::ofstream js(out/"compiler.json");js<<"{\"k\":"<<f.k<<",\"rows\":"<<rows<<",\"columns\":"<<f.cap<<",\"used\":"<<f.used<<",\"dict_size\":"<<dict.size()<<",\"nnz\":["<<A.nnz<<","<<B.nnz<<","<<C.nnz<<"],\"categories\":{";bool first=true;for(auto&p:cats){if(!first)js<<",";first=false;js<<"\""<<p.first<<"\":"<<p.second;}js<<"},\"all_generated_rows_checked\":true,\"coefficient_spec\":\"sign:31;kind:28..30;index:8..27;basis:6..7;bit:0..5\"}\n";
  std::cout<<"compiled "<<rows<<" rows; "<<A.nnz+B.nnz+C.nnz<<" entries\n";
 }
};
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
struct Mapping{
 int fd=-1;size_t size=0;void*data=nullptr;
 Mapping(const fs::path&p){fd=open(p.c_str(),O_RDONLY);ensure(fd>=0,"missing artifact");struct stat st{};ensure(fstat(fd,&st)==0,"fstat");size=st.st_size;
  if(size){data=mmap(nullptr,size,PROT_READ,MAP_PRIVATE,fd,0);ensure(data!=MAP_FAILED,"mmap");}}
 ~Mapping(){if(size)munmap(data,size);if(fd>=0)close(fd);}
};
struct MatrixIn{
 Mapping ptr,ent;const uint32_t*p;const Entry*e;size_t rows,nnz;
 MatrixIn(fs::path f):ptr(f.string()+".ptr"),ent(f.string()+".ent"){
  ensure(ptr.size>=4&&ptr.size%4==0&&ent.size%8==0,"CSR sizes");p=(const uint32_t*)ptr.data;e=(const Entry*)ent.data;
  rows=ptr.size/4-1;nnz=ent.size/8;ensure(p[0]==0&&p[rows]==nnz,"CSR endpoints");}
 E eval(size_t r,const std::vector<uint8_t>&w,const Coefficients&c)const{
  ensure(p[r]<=p[r+1]&&p[r+1]<=nnz,"CSR monotonicity");E v=zero;
  for(size_t t=p[r];t<p[r+1];t++){auto x=e[t];ensure(x.col<w.size(),"CSR column bounds");E a=c.get(x.coef);if(w[x.col])v=ea(v,scale(a,w[x.col]));}return v;
 }
};
void verify(Fixture&f,const fs::path&out,bool second,bool mutate){
 Coefficients c(f);
 if(second){ByteOut w(out/"witness_second.u8");w.put(f.bits.data(),f.bits.size());}
 {std::ifstream w(out/(second?"witness_second.u8":"witness.u8"),std::ios::binary);ensure(bool(w),"missing witness");w.read((char*)f.bits.data(),f.bits.size());ensure(size_t(w.gcount())==f.bits.size()&&w.peek()==EOF,"witness size");}
 if(mutate)f.bits[0]=2;
 ensure(f.bits[f.used-1]==1,"fixed constant");
 MatrixIn A(out/"A"),B(out/"B"),C(out/"C");
 ensure(A.rows==B.rows&&A.rows==C.rows&&A.rows==46109*U(f.k)+108595+f.cap-f.used,"CSR row count");
 size_t bad=A.rows;
 // Link the field prover's compressed evaluation tables to the independently
 // read CSR matrices. The compression is lossless for this fixture, not a
 // assumption about arbitrary witnesses.
 Mapping codes(out/"evaluation_codes.u8"), dictionary(out/"evaluation_dictionary.u64");
 ensure(codes.size==3*A.rows && dictionary.size%sizeof(E)==0,"evaluation artifact shape");
 const auto *ids=static_cast<const uint8_t*>(codes.data);
 const auto *dict=static_cast<const E*>(dictionary.data);size_t ndict=dictionary.size/sizeof(E);
 for(size_t r=0;r<A.rows;r++){
   E a=A.eval(r,f.bits,c),b=B.eval(r,f.bits,c),cc=C.eval(r,f.bits,c);
   if(em(a,b)!=cc){bad=r;break;}
   if(!second && !mutate){
     ensure(ids[3*r]<ndict&&ids[3*r+1]<ndict&&ids[3*r+2]<ndict,"evaluation dictionary index");
     ensure(a==dict[ids[3*r]]&&b==dict[ids[3*r+1]]&&cc==dict[ids[3*r+2]],"CSR/evaluation-table mismatch");
   }
 }
 if(mutate){ensure(bad<A.rows,"mutation was not rejected");std::cout<<"negative test rejected at row "<<bad<<"\n";return;}
 ensure(bad==A.rows,"independent CSR evaluation failed");
 std::ofstream js(out/(second?"verification_second.json":"verification.json"));
 js<<"{\"all_rows_verified\":true,\"rows\":"<<A.rows<<",\"read_from_CSR_artifacts\":true,\"challenge_variant\":"<<int(second)<<",\"evaluation_tables_match_CSR\":"<<(second?"null":"true")<<",\"full_lattice_protocol_verified\":false}\n";
 std::cout<<"independent reader verified "<<A.rows<<" rows, challenge variant "<<second<<"\n";
}
int main(int argc,char**argv){try{
 ensure(argc>=4,"usage: compiler compile|verify|verify-second|negative k out [capacity]");
 ensure(__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__,"little-endian implementation required");
 std::string op=argv[1];int k=std::stoi(argv[2]);ensure(k>=1&&k<=1024,"supported tested k range 1..1024");
 size_t capacity=argc>4?std::stoull(argv[4]):0;fs::path out=argv[3];fs::create_directories(out);
 std::mt19937_64 gen(37);for(int j=0;j<100000;j++){U a=gen()%q,b=gen()%q;ensure(mul(a,b)==U((Wide(a)*b)%q),"modular multiplication regression");}
 auto start=std::chrono::steady_clock::now();Fixture f(k,capacity,op=="verify-second");
 if(op=="compile"){Compiler z(f,out);z.run();}
 else if(op=="verify"||op=="verify-second"||op=="negative")verify(f,out,op=="verify-second",op=="negative");
 else throw std::runtime_error("unknown operation");
 double secs=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
 std::cout<<"elapsed_seconds="<<secs<<"\n";
 return 0;
 }catch(const std::exception&e){std::cerr<<"FAIL: "<<e.what()<<"\n";return 1;}}
