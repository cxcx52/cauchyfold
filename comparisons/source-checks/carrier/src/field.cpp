#define DIRECT_LIBRARY
#include "carrier.cpp"
#include <sstream>

using Poly=std::array<E,4>;
E peval(const Poly&p,E x){E z=zero;for(int i=3;i>=0;i--)z=ea(em(z,x),p[i]);return z;}
void putE(ByteOut&w,E x){for(U a:x)for(int j=0;j<6;j++){uint8_t b=(a>>(8*j))&255;w.put(&b,1);}}
E readE(std::istream&r){E x{};for(U&a:x){for(int j=0;j<6;j++){int c=r.get();ensure(c!=EOF,"truncated field element");a|=U(c)<<(8*j);}ensure(a<q,"noncanonical field element");}return x;}
std::vector<E> eq(const std::vector<E>&r){
 std::vector<E>w(1,one);for(E t:r){std::vector<E>z(2*w.size());for(size_t i=0;i<w.size();i++){z[2*i+1]=em(w[i],t);z[2*i]=es(w[i],z[2*i+1]);}w.swap(z);}return w;
}

void prove(int k,fs::path dir){
 MatrixIn mat(dir/"A");Mapping groupfile(dir/"groups.u32"),codesfile(dir/"evaluations.u32"),dictfile(dir/"dictionary.u64");
 auto group=(const uint32_t*)groupfile.data,code=(const uint32_t*)codesfile.data;auto dict=(const E*)dictfile.data;
 size_t terms=mat.rows,groups=group[terms-1]+1,P=1,G=1;unsigned ell=0,g=0;while(P<terms){P*=2;ell++;}while(G<groups){G*=2;g++;}
 std::mt19937_64 rng(0xC0A20261011ULL);auto coin=[&](){E x{};for(U&a:x){do{a=rng()&mask;}while(a>=q);}return x;};
 std::vector<E>r;for(unsigned i=0;i<g;i++)r.push_back(coin());auto wr=eq(r);
 std::array<std::vector<E>,4>tab;for(auto&v:tab)v.resize(P,zero);
 for(size_t i=0;i<terms;i++){tab[0][i]=wr[group[i]];for(int j=0;j<3;j++)tab[j+1][i]=dict[code[3*i+j]];}
 ByteOut wire(dir/"field.bin");for(E t:r)putE(wire,t);E claim=zero;
 for(unsigned round=0;round<ell;round++){
  size_t n=tab[0].size()/2;Poly poly{};
  for(size_t j=0;j<n;j++){
   E w=tab[0][j],a=tab[1][j],b=tab[2][j],c=tab[3][j];
   E dw=es(tab[0][j+n],w),da=es(tab[1][j+n],a),db=es(tab[2][j+n],b),dc=es(tab[3][j+n],c);
   E p0=es(em(a,b),c),p1=es(ea(em(a,db),em(da,b)),dc),p2=em(da,db);
   poly[0]=ea(poly[0],em(w,p0));poly[1]=ea(poly[1],ea(em(w,p1),em(dw,p0)));
   poly[2]=ea(poly[2],ea(em(w,p2),em(dw,p1)));poly[3]=ea(poly[3],em(dw,p2));
  }
  ensure(ea(poly[0],peval(poly,one))==claim,"sumcheck round consistency");
  for(E x:poly)putE(wire,x);E tau=coin();putE(wire,tau);claim=peval(poly,tau);
  for(auto&v:tab){std::vector<E>z(n);for(size_t j=0;j<n;j++)z[j]=ea(v[j],em(tau,es(v[j+n],v[j])));v.swap(z);}
 }
 ensure(claim==em(tab[0][0],es(em(tab[1][0],tab[2][0]),tab[3][0])),"terminal field check");
 for(int j=1;j<4;j++)putE(wire,tab[j][0]);wire.flush();
 std::ofstream out(dir/"field.json");out<<"{\"arity\":"<<k<<",\"batching_variables\":"<<g<<",\"rounds\":"<<ell<<",\"degree\":3,\"padded_terms\":"<<P<<",\"P_bytes\":"<<24*(4*ell+3)<<",\"V_bytes\":"<<24*(g+ell)<<",\"fixture_coins_only\":true,\"all_rounds_checked\":true}\n";
}

void verifyfield(int k,fs::path dir){
 DirectFixture f(k);ActiveDirect a(f);PublicCoefficients cf(f);MatrixIn first(dir/"A");Mapping groupfile(dir/"groups.u32");auto ids=(const uint32_t*)groupfile.data;
 size_t terms=first.rows,groups=ids[terms-1]+1,P=1,G=1;unsigned ell=0,g=0;while(P<terms){P*=2;ell++;}while(G<groups){G*=2;g++;}
 std::ifstream in(dir/"field.bin",std::ios::binary);ensure(bool(in),"missing field transcript");
 std::vector<E>r,tau;for(unsigned i=0;i<g;i++)r.push_back(readE(in));E claim=zero;
 for(unsigned j=0;j<ell;j++){
  Poly poly;for(E&v:poly)v=readE(in);ensure(ea(poly[0],peval(poly,one))==claim,"stored round inconsistent");
  E t=readE(in);tau.push_back(t);claim=peval(poly,t);
 }
 std::array<E,3>terminal;for(E&v:terminal)v=readE(in);ensure(in.peek()==EOF,"trailing bytes");
 auto wr=eq(r),wt=eq(tau);E W=zero;for(size_t row=0;row<terms;row++)W=ea(W,em(wt[row],wr[ids[row]]));
 ensure(claim==em(W,es(em(terminal[0],terminal[1]),terminal[2])),"independent public weight check");
 for(int m=0;m<3;m++){
  MatrixIn mat(dir/std::string(1,char('A'+m)));std::vector<E>adj(a.used,zero);
  for(size_t row=0;row<terms;row++)for(size_t t=mat.p[row];t<mat.p[row+1];t++){auto e=mat.e[t];adj[e.col]=ea(adj[e.col],em(wt[row],cf.get(e.coef)));}
  E value=zero;for(size_t j=0;j<a.used;j++)if(a.witness[j])value=ea(value,scale(adj[j],a.witness[j]));
  ensure(value==terminal[m],"actual scalar handoff mismatch");
 }
 std::ofstream out(dir/"handoff.json");out<<"{\"stored_transcript_verified\":true,\"public_W_evaluated_independently\":true,\"actual_CSR_transposes_checked\":3,\"scalar_field_equations\":12,\"columns\":"<<a.used<<",\"no_Cauchy_carrier\":false,\"full_lattice_backend_executed\":false}\n";
}

int main(int argc,char**argv){try{
 ensure(argc==4,"usage: field prove|verify k directory");int k=std::stoi(argv[2]);fs::path dir=argv[3];
 if(std::string(argv[1])=="prove")prove(k,dir);else if(std::string(argv[1])=="verify")verifyfield(k,dir);else throw std::runtime_error("unknown operation");
 std::cout<<"PASS field "<<argv[1]<<" k="<<k<<"\n";
}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
