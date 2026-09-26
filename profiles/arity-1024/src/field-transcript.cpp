// Field-front-end prover prototype using actual compiler evaluation artifacts.
// Deterministic public coins are fixtures, not a Fiat-Shamir implementation.
#define main compiler_tool_main
#include "compiler.cpp"
#undef main
#include <cstring>
using Poly=std::array<E,4>;
std::vector<E> eqweights(const std::vector<E>&v,size_t begin,size_t end){
 std::vector<E>w(1,one);for(size_t j=begin;j<end;j++){std::vector<E>z(2*w.size());E a=es(one,v[j]);for(size_t i=0;i<w.size();i++){z[2*i]=em(w[i],a);z[2*i+1]=em(w[i],v[j]);}w.swap(z);}return w;
}
E evalpoly(const Poly&p,const E&t){E v=zero;for(int i=3;i>=0;i--)v=ea(em(v,t),p[i]);return v;}
struct RawTables{
 Mapping codes,dictionary;size_t rows,nd;const uint8_t*co;const E*dict;
 RawTables(const fs::path&p):codes(p/"evaluation_codes.u8"),dictionary(p/"evaluation_dictionary.u64"){
  ensure(codes.size%3==0&&dictionary.size%sizeof(E)==0,"evaluation artifact shape");rows=codes.size/3;nd=dictionary.size/sizeof(E);co=(uint8_t*)codes.data;dict=(const E*)dictionary.data;
  ensure(nd>0&&nd<=256&&dict[0]==zero,"dictionary must have zero at index zero");for(size_t i=0;i<codes.size;i++)ensure(co[i]<nd,"invalid dictionary symbol");
  for(size_t i=0;i<nd;i++)for(U x:dict[i])ensure(x<q,"noncanonical dictionary");
 }
 unsigned sym(size_t row,int c)const{return row<rows?co[3*row+c]:0;}
};
struct Tables{
 RawTables&raw;unsigned ell,high;std::vector<E>tau;std::vector<E> dense[3];bool is_dense=false;
 Tables(RawTables&r,unsigned e,unsigned h):raw(r),ell(e),high(h){}
 std::vector<E> weightbank(){auto w=eqweights(tau,0,tau.size());std::vector<E>b(w.size()*256,zero);
  for(size_t i=0;i<w.size();i++)for(size_t j=1;j<raw.nd;j++)b[i*256+j]=em(w[i],raw.dict[j]);return b;}
 void pair(size_t tail,size_t i,const std::vector<E>&b,E a[3],E z[3])const{
  if(is_dense){for(int c=0;c<3;c++){a[c]=dense[c][i];z[c]=dense[c][tail+i];}return;}
  for(int c=0;c<3;c++)a[c]=z[c]=zero;
  for(size_t x=0;x<(size_t(1)<<tau.size());x++)for(int c=0;c<3;c++){
   unsigned v=raw.sym(2*x*tail+i,c),w=raw.sym((2*x+1)*tail+i,c);
   if(v){a[c]=ea(a[c],b[256*x+v]);}
   if(w){z[c]=ea(z[c],b[256*x+w]);}
  }
 }
 void materialize(){size_t n=size_t(1)<<(ell-tau.size());auto b=weightbank();for(int c=0;c<3;c++)dense[c].assign(n,zero);
  for(size_t i=0;i<n;i++)for(size_t x=0;x<(size_t(1)<<tau.size());x++)for(int c=0;c<3;c++){
   unsigned v=raw.sym(x*n+i,c);if(v)dense[c][i]=ea(dense[c][i],b[256*x+v]);}
  is_dense=true;
 }
 void fold(const E&t){
  if(is_dense){size_t n=dense[0].size()/2;for(int c=0;c<3;c++){for(size_t i=0;i<n;i++)dense[c][i]=ea(dense[c][i],em(t,es(dense[c][n+i],dense[c][i])));dense[c].resize(n);}}
  tau.push_back(t);if(!is_dense&&tau.size()==high)materialize();
 }
};
void putE(ByteOut&w,const E&e){for(U x:e){uint8_t b[6];for(int j=0;j<6;j++)b[j]=uint8_t(x>>(8*j));w.put(b,6);}}
std::array<E,3> independent_mle(RawTables&t,const std::vector<E>&tau,unsigned ell){
 unsigned low=std::min(16u,ell),hi=ell-low;auto wl=eqweights(tau,hi,ell),wh=eqweights(tau,0,hi);size_t block=size_t(1)<<low;
 std::array<E,3>total{};
 for(size_t h=0;h<wh.size();h++){
  E bins[3][256]{};
  for(size_t l=0;l<block;l++)for(int c=0;c<3;c++){unsigned s=t.sym(h*block+l,c);if(s)bins[c][s]=ea(bins[c][s],wl[l]);}
  for(int c=0;c<3;c++){E v=zero;for(size_t s=1;s<t.nd;s++)v=ea(v,em(bins[c][s],t.dict[s]));total[c]=ea(total[c],em(wh[h],v));}
 }
 return total;
}
int main(int argc,char**argv){try{
 ensure(argc>=3,"usage: field-transcript artifact_directory output_directory [streamed_rounds]");fs::path input=argv[1],output=argv[2];fs::create_directories(output);
 RawTables raw(input);unsigned ell=0;while((size_t(1)<<ell)<raw.rows)ell++;unsigned high=argc>3?std::stoul(argv[3]):6;
 ensure(high>0&&high<=ell,"stream split");Tables tab(raw,ell,high);
 std::mt19937_64 rng(0xF1E1DC0123);auto coin=[&](){E x;for(U&v:x){do{v=rng()&mask;}while(v>=q);}return x;};
 std::vector<E>r;for(unsigned j=0;j<ell;j++)r.push_back(coin());
 ByteOut wire(output/"transcript.bin");for(auto&x:r)putE(wire,x);
 E claim=zero,eprefix=one;auto start=std::chrono::steady_clock::now();
 for(unsigned j=0;j<ell;j++){
  auto rs=std::chrono::steady_clock::now();size_t tail=size_t(1)<<(ell-j-1);unsigned f=ell-j-1,lo=std::min(16u,f),hi=f-lo;size_t block=size_t(1)<<lo;
  auto wl=eqweights(r,j+1+hi,ell),wh=eqweights(r,j+1,j+1+hi);auto bank=tab.is_dense?std::vector<E>():tab.weightbank();
  E totals[3]{};
  for(size_t h=0;h<wh.size();h++){
   E subacc[3]{};
   for(size_t l=0;l<block;l++){
    size_t t=h*block+l;E a[3],b[3];tab.pair(tail,t,bank,a,b);
    E p0=es(em(a[0],a[1]),a[2]);E p2=em(es(b[0],a[0]),es(b[1],a[1]));
    E p1=es(es(es(em(b[0],b[1]),b[2]),p0),p2);E ps[3]={p0,p1,p2};
    for(int c=0;c<3;c++)if(ps[c]!=zero)subacc[c]=ea(subacc[c],em(wl[l],ps[c]));
   }
   for(int c=0;c<3;c++)totals[c]=ea(totals[c],em(wh[h],subacc[c]));
  }
  E e0=es(one,r[j]),e1=es(scale(r[j],2),one);
  Poly g{em(e0,totals[0]),ea(em(e0,totals[1]),em(e1,totals[0])),ea(em(e0,totals[2]),em(e1,totals[1])),em(e1,totals[2])};
  for(auto&x:g){x=em(eprefix,x);putE(wire,x);}
  ensure(ea(g[0],evalpoly(g,one))==claim,"sumcheck round consistency");
  E t=coin();putE(wire,t);claim=evalpoly(g,t);eprefix=em(eprefix,ea(e0,em(e1,t)));tab.fold(t);
  double sec=std::chrono::duration<double>(std::chrono::steady_clock::now()-rs).count();std::cout<<"round "<<j+1<<" seconds="<<sec<<std::endl;
 }
 ensure(tab.is_dense&&tab.dense[0].size()==1,"terminal table size");
 std::array<E,3>ends{tab.dense[0][0],tab.dense[1][0],tab.dense[2][0]};
 ensure(claim==em(eprefix,es(em(ends[0],ends[1]),ends[2])),"final sumcheck equation");
 for(auto&x:ends)putE(wire,x);
 auto independent=independent_mle(raw,tab.tau,ell);ensure(independent==ends,"independent MLE mismatch");
 std::ofstream js(output/"verification.json");
 js<<"{\"field_sumcheck_verified\":true,\"independent_raw_MLE_verified\":true,\"rows\":"<<raw.rows<<",\"rounds\":"<<ell<<",\"streamed_rounds\":"<<high<<",\"dense_table_allocated_bytes\":"<<(3*(size_t(1)<<(ell-high))*sizeof(E))<<",\"wire_bytes\":"<<(144*ell+72)<<",\"fixture_coins_not_production\":true,\"lattice_backend_verified\":false}\n";
 std::cout<<"field proof and independent terminal MLE verified; seconds="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<std::endl;
 return 0;
 }catch(const std::exception&e){std::cerr<<"FAIL: "<<e.what()<<std::endl;return 1;}}
