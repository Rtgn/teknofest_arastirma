*-------------------------
* SETLER
*-------------------------
Sets
    m   "matches"
    i   "wastes"
    j   "processes"
;

*-------------------------
* PARAMETRELER
*-------------------------
Parameters
    S(m)        "sustainability score (composite: 60% env + 25% econ + 15% tech)"
    E(m)        "env_score — pure CO2 savings component (for double-weighted env objective)"
    W(m)        "waste amount (kg)"
    IW(m,i)     "1 if match m uses waste i"
    JP(m,j)     "1 if match m uses process j"
    Cap(j)      "monthly capacity of process j (kg/month)"
;

Scalar OSB_Limit;
$include osb_limit.txt

*-------------------------
* VERI OKUMA
*-------------------------
$gdxin matches.gdx
$onUNDF
$load m, i, j, S, E, W, IW, JP, Cap
$offUNDF
$gdxin

*-------------------------
* DEGISKENLER
*-------------------------
Binary Variable x(m);
Variable z;

*-------------------------
* DENKLEMLER
* Çevre Ağırlıklı Hedef Fonksiyon (v2):
* z = Σ (w_env * E(m) + w_score * S(m)) * x(m)
* w_env=0.60 → env_score doğrudan pekiştiriliyor
* w_score=0.40 → bileşik sürdürülebilirlik skoru (S) de hesaba katılıyor
* proc_select: her hedef proses en fazla bir seçili eşleşme (tek atık hattı)
*-------------------------
Scalars
    w_env   "weight for direct env_score term"  /0.60/
    w_score "weight for composite sustainability score" /0.40/
;

Equations
    obj
    waste_cap(i)
    osb_cap
    proc_select(j)
    proc_cap(j)
;

obj..
    z =e= sum(m, (w_env*E(m) + w_score*S(m))*x(m));

waste_cap(i)..
    sum(m$(IW(m,i)=1), x(m)) =l= 1;

osb_cap..
    sum(m, W(m)*x(m)) =l= OSB_Limit;

proc_select(j)..
    sum(m$(JP(m,j)=1), x(m)) =l= 1;

proc_cap(j)$(Cap(j) > 0)..
    sum(m$(JP(m,j)=1), W(m)*x(m)) =l= Cap(j);

Parameter hasMatch(i);
hasMatch(i) = sum(m, IW(m,i));

Model symbiosis /all/;
Solve symbiosis using mip maximizing z;
display hasMatch;

* Sonuc: Python yalnizca bu CSV'yi okur (GDX / Python API yok)
* pc=5 (CSV) Put ile birlikte ';' kullanildiginda alanlar ve satirlar bozuluyor — duz metin (pc=0).
* Ayirici: ';' (virgul hem eski Put hatasinda hem Excel locale'de riskli).
file csvout / 'selected_matches.csv' /;
csvout.pc = 0;
put csvout;
put 'match_id;level' /;
loop(m,
    put m.tl:0 ';' x.l(m):15:10 /
);
putclose csvout;
