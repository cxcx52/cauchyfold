"""Create the matched carrier/grouped compiler without editing either baseline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIRECT = ROOT.parent/'direct'


def replace(text, old, new):
    assert old in text, old
    return text.replace(old, new)


def main():
    out = ROOT/'src'
    out.mkdir(parents=True, exist_ok=True)
    text = (DIRECT/'src/direct.cpp').read_text(encoding='utf-8')
    start, end = text.index('struct DirectFixture {'), text.index('struct ActiveDirect {')
    text = text[:start]+'''struct DirectFixture: Fixture {
 DirectFixture(int k,int variant=0,bool invalid=false):Fixture(k,0,variant){
  ensure(!invalid,"unsupported carrier fixture mutation");
  values.resize(73*(k+2)+4*k);
 }
};

'''+text[end:]
    start, end = text.index('struct PublicCoefficients {'), text.index('struct DirectCompiler {')
    text = text[:start]+'using PublicCoefficients=Coefficients;\n\n'+text[end:]
    text = replace(text, '#include "primitives.cpp"', '#include "../../direct/src/primitives.cpp"')
    text = replace(text, '#include "compare.inc"', '#include "../../direct/src/compare.inc"')
    text = replace(text, 'free==68*U(f.k)+584', 'free==84*U(f.k)+584')
    text = replace(text, 'category="source_and_output_Q";', '''category="folded_E";
  for(int j=0;j<4;j++){
   Form x;dec(x,73*(f.k+1)+69+j);dec(x,69+j,true);
   for(int i=0;i<f.k;i++)dec(x,73*(i+1)+69+j,true,3,i);
   for(int t=0;t<f.k;t++)dec(x,73*(f.k+2)+4*t+j,true,4,t);
   linear(x);
  }
  category="output_Q";''')
    text = replace(text, 'for(int s=0;s<f.k+2;s++)for(int j=0;j<4;j++){',
                   'for(int s=f.k+1;s<f.k+2;s++)for(int j=0;j<4;j++){')
    text = replace(text, '4292*U(f.k)+36879&&terms==4324*U(f.k)+36951',
                   '5296*U(f.k)+36879&&terms==5296*U(f.k)+36915')
    text = replace(text, 'carrier_constructed\\\":false', 'carrier_constructed\\\":true')
    (out/'carrier.cpp').write_text(text, encoding='utf-8', newline='\n')
    field = (DIRECT/'src/field.cpp').read_text(encoding='utf-8')
    field = replace(field, '#include "direct.cpp"', '#include "carrier.cpp"')
    field = replace(field, 'no_Cauchy_carrier\\\":true', 'no_Cauchy_carrier\\\":false')
    (out/'field.cpp').write_text(field, encoding='utf-8', newline='\n')

    source = (DIRECT/'backend/build_profiles.py').read_text(encoding='utf-8')
    source = replace(source, 'import layout', 'sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"direct/backend"))\nimport layout')
    source = replace(source, 'ROOT = Path(__file__).resolve().parent', 'ROOT = Path(__file__).resolve().parents[1]/"direct/backend"')
    source = replace(source, 'direct = front_override is not None',
                     'direct = front_override is not None and not front_override.get("with_carrier", False)')
    source = replace(source, 'f = dict(front_override) if direct else', 'f = dict(front_override) if front_override is not None else')
    source = replace(source, '(96 if direct else (48 if large else 96))*f[\'field_rounds\']',
                     '24*f.get("round_coefficients", (4 if direct else (2 if large else 4)))*f[\'field_rounds\']')
    source = replace(source, "(f['batching_variables'] if direct else ell)", "f.get('batching_variables', ell)")
    (ROOT/'parameter_model.py').write_text(source, encoding='utf-8', newline='\n')
    print('Prepared matched grouped carrier compiler and parameter model')


if __name__ == '__main__':
    main()
