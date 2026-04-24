$title Build matches.gdx from CSV (csv2gdx, no Python API)

* Girdi dosyalari: gdx_builder.py tarafindan yazilan gams_*.csv (calisma dizininde)
* Cikti: matches.gdx (new3.gms ile uyumlu semboller: m, i, j, S, E, W, IW, JP, Cap)

Set m, i, j;
Parameter
    S(m), E(m), W(m), IW(m,i), JP(m,j), Cap(j)
;

$call csv2gdx gams_S.csv id=S index=1 value=2 useHeader=y trace=0 output=p_S.gdx
$if errorlevel 1 $abort 'csv2gdx failed: gams_S.csv'

$gdxin p_S.gdx
$load m=Dim1 S
$gdxin

$call csv2gdx gams_E.csv id=E index=1 value=2 useHeader=y trace=0 output=p_E.gdx
$if errorlevel 1 $abort 'csv2gdx failed: gams_E.csv'

$gdxin p_E.gdx
$load E
$gdxin

$call csv2gdx gams_W.csv id=W index=1 value=2 useHeader=y trace=0 output=p_W.gdx
$if errorlevel 1 $abort 'csv2gdx failed: gams_W.csv'

$gdxin p_W.gdx
$load W
$gdxin

$call csv2gdx gams_IW.csv id=IW index=1,2 value=3 useHeader=y trace=0 output=p_IW.gdx
$if errorlevel 1 $abort 'csv2gdx failed: gams_IW.csv'

$gdxin p_IW.gdx
$load i=Dim2 IW
$gdxin

$call csv2gdx gams_JP.csv id=JP index=1,2 value=3 useHeader=y trace=0 output=p_JP.gdx
$if errorlevel 1 $abort 'csv2gdx failed: gams_JP.csv'

$gdxin p_JP.gdx
$load j=Dim2 JP
$gdxin

$call csv2gdx gams_Cap.csv id=Cap index=1 value=2 useHeader=y trace=0 output=p_Cap.gdx
$if errorlevel 1 $abort 'csv2gdx failed: gams_Cap.csv'

$gdxin p_Cap.gdx
$load Cap
$gdxin

execute_unload 'matches.gdx', m, i, j, S, E, W, IW, JP, Cap;
