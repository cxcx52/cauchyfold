#define DIRECT_LIBRARY
#include "direct.cpp"

using Ring=std::array<U,64>;
Ring product(const Ring&a,const Ring&b){
 Ring r{};for(int i=0;i<64;i++)for(int j=0;j<64;j++)if(b[j]){
  U v=mul(a[i],b[j]);if(i+j<64)r[i+j]=add(r[i+j],v);else r[i+j-64]=sub(r[i+j-64],v);
 }return r;
}

int main(int argc,char**argv){try{
 ensure(argc==2,"usage: commitments output-json");
 DirectFixture f(4);ActiveDirect a(f);size_t valuebits=192*f.values.size(),physical=valuebits+48*f.values.size();
 std::vector<int64_t>reverse(physical,-1);std::vector<uint8_t>full(physical),fixed(physical);
 for(size_t g=0;g<4*f.values.size();g++){
  U x=f.values[g/4][g%4];unsigned z=42-__builtin_popcountll(x>>6);std::vector<uint8_t>bits(60);
  for(int j=0;j<48;j++)bits[j]=(x>>j)&1;for(int j=0;j<6;j++)bits[48+j]=(z>>j)&1;
  bits[54]=(1-bits[48])*(1-bits[49]);for(int j=2;j<6;j++)bits[53+j]=bits[52+j]*(1-bits[48+j]);bits[59]=bits[58]*bits[2];
  for(int j=0;j<60;j++){size_t pos=j<48?48*g+j:valuebits+12*g+j-48;full[pos]=bits[j];
   if(a.isfixed(g))fixed[pos]=bits[j];else{reverse[pos]=60*a.index[g]+j;ensure(full[pos]==a.witness[reverse[pos]],"insertion");}}
 }
 struct Segment{size_t start,length;int key;};std::vector<Segment>segments;
 for(int i=0;i<f.k+2;i++)segments.push_back({size_t(i)*14016,14016,0});
 segments.push_back({valuebits,physical-valuebits,1});
 size_t equations=0;
 for(const auto&seg:segments){
  size_t cols=(seg.length+63)/64;std::mt19937_64 gen(20260928+seg.key);
  for(int row=0;row<4;row++){
   Ring lhs{},offset{},linear{};
   for(size_t col=0;col<cols;col++){
    Ring matrix{},packed{},offsetbits{};for(U&v:matrix)v=gen()%q;
    for(int j=0;j<64;j++)if(64*col+j<seg.length){packed[j]=full[seg.start+64*col+j];offsetbits[j]=fixed[seg.start+64*col+j];}
    auto u=product(matrix,packed),v=product(matrix,offsetbits);
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
 std::ofstream out(argv[1]);out<<"{\"status\":\"PASS\",\"arity\":4,\"ring_degree\":64,\"all_segment_commitment_scalar_equations\":"<<equations<<",\"state_key_reused\":true,\"independent_key_families\":2,\"deterministic_test_matrices_not_production_CRS\":true}\n";
 std::cout<<"Affine module commitments checked: "<<equations<<" scalar equations\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
