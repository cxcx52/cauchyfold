#define CF_LIBRARY
#include "compile.cpp"
#undef CF_LIBRARY

using Ring=std::array<U,64>;
Ring product(const Ring&a,const Ring&b){
 Ring r{};for(int i=0;i<64;i++)for(int j=0;j<64;j++)if(b[j]){
  U v=mul(a[i],b[j]);if(i+j<64)r[i+j]=add(r[i+j],v);else r[i+j-64]=sub(r[i+j-64],v);
 }return r;
}

int main(int argc,char**argv){try{
 ensure(argc==3,"usage: check-commitments prefix|special output-json");bool sp=std::string(argv[1])=="special";
 Fixture f(4,0);Active a(f,sp);std::vector<int64_t>reverse(a.physical,-1);
 for(size_t j=0;j<a.insertion.size();j++)reverse[a.insertion[j]]=j;
 struct Segment{size_t start,length;int key;};std::vector<Segment>segments;
 for(int i=0;i<f.k+2;i++)segments.push_back({size_t(i)*14016,14016,0});
 segments.push_back({size_t(f.k+2)*14016,size_t(768*f.k),1});
 size_t aux=192*(73*(f.k+2)+4*f.k);segments.push_back({aux,a.physical-aux,2});
 size_t equations=0;
 for(const auto&seg:segments){
  size_t cols=(seg.length+63)/64;std::mt19937_64 gen(20260928+seg.key);
  for(int row=0;row<4;row++){
   Ring lhs{},offset{},linear{};
   for(size_t col=0;col<cols;col++){
    Ring matrix{},full{},fixed{};for(U&v:matrix)v=gen()%q;
    for(int j=0;j<64;j++)if(64*col+j<seg.length){full[j]=a.full[seg.start+64*col+j];fixed[j]=a.fixed[seg.start+64*col+j];}
    auto u=product(matrix,full),v=product(matrix,fixed);
    for(int t=0;t<64;t++){lhs[t]=add(lhs[t],u[t]);offset[t]=add(offset[t],v[t]);}
    // Independent scalar expansion of the packed negacyclic commitment map.
    for(int j=0;j<64;j++)if(64*col+j<seg.length){
     auto ix=reverse[seg.start+64*col+j];if(ix<0||!a.witness[ix])continue;
     for(int t=0;t<64;t++){
      U value=mul(matrix[(t-j+64)%64],a.witness[ix]);
      linear[t]=t>=j?add(linear[t],value):sub(linear[t],value);
     }
    }
   }
   for(int t=0;t<64;t++){ensure(sub(lhs[t],offset[t])==linear[t],"affine commitment handoff mismatch");equations++;}
  }
 }
 std::ofstream out(argv[2]);out<<"{\"status\":\"PASS\",\"arity\":4,\"ring_degree\":64,\"all_segment_commitment_scalar_equations\":"<<equations<<",\"state_key_reused\":true,\"independent_key_families\":3,\"deterministic_test_matrices_not_production_CRS\":true}\n";
 std::cout<<"Affine module commitments checked: "<<equations<<" scalar equations\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
