#define CF_LIBRARY
#include "compile.cpp"
#undef CF_LIBRARY

E read_field(std::istream& in){
 E x{};for(U&v:x){v=0;for(int i=0;i<6;i++){int c=in.get();ensure(c!=EOF,"truncated field message");v|=U(c)<<(8*i);}ensure(v<q,"noncanonical field value");}return x;
}

int main(int argc,char**argv){try{
 ensure(argc==5,"usage: check-handoff k mode circuit-directory field-directory");
 int k=std::stoi(argv[1]);
 fs::path input=argv[3],field=argv[4];Fixture f(k,0);Active a(f,std::string(argv[2])=="special");Coefficients cf(f);
 MatrixIn first(input/"A");unsigned ell=0;while((size_t(1)<<ell)<first.rows)ell++;
 std::ifstream wire(field/"transcript.bin",std::ios::binary);ensure(bool(wire),"missing field transcript");
 for(unsigned i=0;i<ell;i++)read_field(wire);
 std::vector<E>tau;for(unsigned i=0;i<ell;i++){for(int j=0;j<2;j++)read_field(wire);tau.push_back(read_field(wire));}
 std::array<E,3>terminal;for(E&x:terminal)x=read_field(wire);ensure(wire.peek()==EOF,"trailing field bytes");
 std::vector<E>weights(1,one);
 for(const E&t:tau){std::vector<E>next(2*weights.size());for(size_t j=0;j<weights.size();j++){next[2*j]=em(weights[j],es(one,t));next[2*j+1]=em(weights[j],t);}weights.swap(next);}
 for(int m=0;m<3;m++){
  MatrixIn mat(input/std::string(1,char('A'+m)));std::vector<E>adj(a.used,zero);
  for(size_t row=0;row<mat.rows;row++)for(size_t t=mat.p[row];t<mat.p[row+1];t++){
   auto e=mat.e[t];ensure(e.col<a.used,"adjoint column");adj[e.col]=ea(adj[e.col],em(weights[row],cf.get(e.coef)));
  }
  E result=zero;for(size_t j=0;j<a.used;j++)if(a.witness[j])result=ea(result,scale(adj[j],a.witness[j]));
  ensure(result==terminal[m],"terminal claim disagrees with actual matrix transpose");
  ByteOut serialized(field/(std::string(1,char('A'+m))+"_transpose.u64"));serialized.put(adj.data(),adj.size()*sizeof(E));
 }
 std::ofstream out(field/"handoff.json");out<<"{\"actual_dense_transposes_checked\":3,\"all_match_terminal_claims\":true,\"k\":"<<k<<",\"columns\":"<<a.used<<",\"rounds\":"<<ell<<"}\n";
 std::cout<<"All three actual matrix transposes match terminal claims\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
