 void compare(size_t base){
  category="value_boolean";for(int j=0;j<48;j++)row(sc(base+j),Form{{uint32_t(base+j),key()},{uint32_t(a.onecol),key(0,0,0,0,true)}});
  {
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
  }
 }
