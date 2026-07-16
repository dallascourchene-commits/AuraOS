"""Materialize the reproducible GPT-5.6 Thinking Architect pilot responses.

The payload is compressed only to keep the repository fixture compact. The generated
JSON is human-readable and contains the RAW plan, Aura-slice plan, two Architect
Council candidates, three Shadow critic responses, and the Judge decision.

This is a single-session assisted pilot, not a blinded or independent evaluation.
"""
from __future__ import annotations

import argparse
import base64
from pathlib import Path
import zlib

_PAYLOAD_B85 = r'''c-rk<TXWmS6@K@x*wIrvL&|lUrb+ZfQ*^?KZq>zZr_ErNz>-7+0tgn6OlR`nd(PP_Ktci?O4elXVpHS-SnN69xqevu_KL9sUKKo$NgRqGPk4IpJ^Ky5#vj5^<Rwqxhp>oCQN$d6{4f0oKcA<9<)V<WEJa$fAFCBl*=T{E@jUE4D{f`ZL&1_by_GDR{UX9Lz7qqsD6%Sz;&d@!A%_nUFNGX1DH0eVB07G+Mq$auJeO61Kf;I-{=0)|%wtioLWCmD@hdn3i(;8)GA`pRJv<ngDZ<fw7AJAJra|&HP7)j%W^kG{oT8F~iH~pxFc<i90iTLkNE%&;6^~QKqq|sU#o9aViCFM(%|=DIgk^zQ;&656qe7&djV`9r9G}4&ahw-VSh<87Uo7F0IjnaK2Sz-Hg_YjP&oX`ccW~ycfE9wZkHZ1W3bx83k-&-JUQ?L)qTp#M*{Uk(0yrWsvQ<WZ@Ty#9a41ZiPW|)1NVN<~E^nnL%ir|>HKD`r2iHqMa-1jGJ<d9lxH!Jp8=}4yYmnb;t-jBf9Ht5XERWnWzq=frPX1SY_2#>;ez-ipIXhOLFHS~h>eFa^t-rcFf3HU#PsY>Z37d%}zl*a%FRo-^w#wn=XNho2h<A~|ghdp9q;t9v30F=8o1xyp1kGWj8^at{R1|kOIT6LBf1(f;x-8&QrN3TEQ0Kw%^l~!34q%?gH{<K+`B`v!b3MWj-Z^0C#pUE`a`}D|T->}pnT`X{kE{BK$-gh)hv{`NIv!nIPcE;5^Rtux)W`gIb2>T;E+_A&lMnFUzi!~_#|L)A&)&2_RD`4;tIE78aRqM9rthYcW0>>1cm5q(SmK}yC0I~Y!8m>EX*r1$Reb?)W#TT51gHrE9mnB5{;kS@h)TgDmd#mN2u|{c)y{dLHI}BwxYPjVO+gkS;dmeO7>qzu0%W<Cc-?^Gbpwv*JIvShb)#Y2+(wXOS&n12E?ki%v=HG^@I07RaT1BbpOB0{(STF`%aRuhQPL#ww~cw3^{7wH946PRS(e~|w1%{VAM_FR;qo?!BOEw>W2XQ6pbLh<?10Dsp|_$0?94@hqLU7kAX+rCd_K>L2#?fu^$Jbq2f^>i;({p#dvhOyWdW&?`5}q&GF&=?gLWvY(8BSCUF|Wt2aH~lER`=q5rxjlIoD=9O$JUH-5df7kvHVZL6auzh%~1hK@=C{oz~mI=B5;&Vg*_QT1L~Y+>?$y11`fXyv^g%pCh58cnq90s(EX&4WM6j2k1qSk$Ax##$X5q%w-j)2u$$$TJHg?iHbTv1b{^pJlfxqf*}BFB*FyDpR@sz1~9}|X;!ju$<u}KgMuE3f81Lt!Fevy4_U$al^MB4kU^G$HB2x(Lob&Mvou+=3(%kx*YRz}i^yUY53z>1w)Q4o+!46BzD_X1>%0*E7-pCND3@(#_!tHuo<LD;KRBqZRU0t>-W`}@IA0<#AweX~60jWb*$ey2Qmh~aL9s>^ghG<15UYQ}45lV%&?}gm&>_9@pkS6MV*w+ol9Q||;1p53z(l9V=RQ282*Fx5B3PGD8A}P@WU}1IBVB|G;pqb1YD&__1P^Bf0S(4UyE;))S$BMph-lGtK4x$NH{y`_44`bz?lC;lwKk4wgWlKOp*J!1?{s{@$}CH4K5b$gjA)J+<fD=jiCm<wQ}MBUEvwlohW{WZuH<XXS&Nd%CCrfwtK@*gSrNmcGaMs)FR8L;q48WVCiFP`Y#dIgaG?DfxGyY)oSd98Dmqya`tHwpOuwvxx<J9ut`5*#HAs?Gps&~B23;N*C@pyo)Oi<Oh52KkgHSF?FsS~u0$0%nwtsX7+f}13CICQK<{^DXKc`DzCV?!Me0vt@r6SW~Ea)kpwgNQyH9SO|DOwGwn1J^JDa8ubp?7`zfZQp+6}99Y7s@y`ZnA~Q1e6e~VjZU70KNj{i-WLAlO!Tx%Qyl@$ZQt(CDO(xhF~KHeF%Od81JoY8~(o8twM7%MF1j-s#q=wQ~*89|0u^0(Ewxwh%4|D0;ozs*|X#hgy;g5lp;_3Q?fL}bT3;0JVI9^1{{>IY(2>K5?`hf!9{FT#O1Ak%pps?1_$E_c_BO+j3C)Pia?Y+HyRt;3ajJ?|3HCsdm*wtPkhE2>6Y5<Lj_V=i8k#0(_*jQ`Y@4nRe&uLVT^GANn1xJjf5QH{)f`{nxNVJGFBxv0}hvVyek08Ji)W;;=sVS%>(B8R3~8f25e+a=0J&jVq<HiEGiPxq3?YP%7?9y7=GDoEiqHncbbSZmnIRSM6@W4N@8_B#_AC!Mc}a$@XBC=w|3q@6OtLk1il`VOlx`6V|v_THV*V14CgSN5)BuaJDfiX&9=)Ps;Ib8WK2ysB6GNVHCIli77uk};a(QPL2?Z%3(^q!#tJaD!j<I@>Q+{OzGC@%nU(UM=dK-B@4*!@=<15+{@pq)Q(eB9z>)!mVT+ij7;k~pLJE->IB)4Hj|ZmM4w05vVVri4?OJcZoNGBH8C)R#WScJq$Ih%?ooXi6V8T|`pSTl%cgky3$`vRSgcvECW7Dx-|8Lx@){y`N7?DEMgxr7}x~Dj;bQeLFJRuOlFXlW>yqntEa8eyd+a^?HPYKS_*mz&kh$0vDCaSrax^NcrPB+?N5D@_Qlr$q#^sy~iRl#9*+$w8rJ$COEb?Otn(t*ao3}(1o@!~ePL)<F^H@dkT1*6OHkJD>(!Q=C@tMilTF*)Dh?c{9y<LT(~r{Mh?x+DOyO2asDQ~+fur2T@%$kO{8@tR}oA<zVuMI}7jtV(AE3BKk@bYr~Mdo)>xu7v4cyiGRz7}Y8Myh_MCV>#}K*)?E%v4AKNM~u}yffY;=3C5FpkOFMR9FAf-;-QRG@eimRS@UWjbDZek4!`}T8QL9~&}o0mfk7eJY1;x|So@3-zc58@^(hjRE>tsC{|J`s7e!52vlz>mXgHLPQu+oyFm1Xw*T$#PHLuy6MHUTJ^wY8`-@Vyb70UPax+)Wbs#j)bDOXmq5J<2fq%egPtvQrgLO3jVF*CMgU@gV~ed)j}=nYjtPC2ui=@3lX0zDY%qILz=thXu1ceVIKFUY|!6`a|}5Xv`be*54e)fR))R20D*a1q!cLTRot4IwOCYoZN>@SgXyLCg1BVjG73ZLk?f4BE&(=n>J*U;tsNq;5I2OB$$<#V`0sFJ7Q3K*YvH6(W~|VTmJ~&+E&p*+GGgV|2J@m*HURs_UQqb$^)I)bK5;_7sxu$1<bpy{Se7xJuGT8|vA)ZLpclGU+f2T?d4r108RfUczRWr2{eLa<+$D^B5~?8-Z7C^^mRQgx&DEb>9y5B(hEZ2sH&qBK-)$8~o_op(vxOY`M-GrEm&xeMZ5+D-R75igR)Dsv(WdRXjD-App(*GEiG%-ic8JH;k$=J(f1l1;JpE+P`cgT&AH4(bj9jG%y2z+u^dpB1p46!zqsDBwn3aI|o#|+NM(LE<!==29=5z<a1DHw6?AcO~J|#gU}(_Z>?%1*+Zku))a1KZuwP(KMQ+nj}?grYZ5zECA!olx>Y6~uT9j_?VaiqFP+czNWr2rr>jHPy19stRV`ZT7N5=T+L_<g#_;k2sz=fO0(o9Nn)in0r(u3|#AKH;{;vG5#~5Hwi{Xw;u+QRxwXwmvg855x!g|#1&j-H*mRLuSKg<;S;$F7{XKa70u{PdVR|vll_E?YP{rTVL=96`G&D}U<9av>g3*U#?WuL__Yh##o1?fxVne~X>8)Bc9dDao0UD#(G`Dagz&xd$uJ2BDPxM*Er`EnU)JvjFU&gbH&J#&KlOkizgtnJ2GYh$hLQg!-*+_fH#dyH<sIGgP=%EN8N*AASv=c^EJe=d0kc3T_2tt(1T>K!l)QUPaRZBfPpoi?f_)WGGT12)6nbUEbrywHNBj8t)xT)Wn7;$UMbL$J{OT}7J`s@Kpv)TizCxCB*~4lMdit&i(gP(AlFjZ)SBq{x{VAnT#zbH4`)nUWK}X%jeu4Q4zPQPoD2_{^-fy&8q%LOq>UkF9?XR&n~QRpzb_d~N#ddM8^!xZNgv>)C|O)^Qv2b&Op+QEv+SCK`*6?1OC(-!D-qwva|ZPY{-dVie0QeA+|ylMwk<HtZ-Y?dJ_LEUaRU5Nl$Y7H+Ibw}zDH*|xkS%2cG73K&YHik&fAJFZKTNjYrBo$_!Sze6?pua-Q@?o|Z{b0A|GT}$1vV~(^>4AlxzH2{enHUQFxZsX8syM5$9M{X560QFL#o8FP;gD5HyNl5kFQ7($UY`2ObJIiZZ+_c$I$JbOB#tW$#a|+^=efcDsw@Yk|+Qae`BL*rT3y6{%z~lo($qj0hTp0cSYNYC%a2F|&mU()snvS(ydK!;4z!FEovOtO1i`*SYmqP`rP0MHb8oHMWKnHHku*SE7q!hlY<Z@uxF=CUov4!hPgi2Jk25Rihp&t5^ay&=mv}WlX{-X3&^L@2`_=gy}W0@gKS83YEPzdn;zgC<Q;sq?6f5@!Ju(fYIN}VjM*i4c_ce35gl8SXQ?VoCcFN~A6ydo1FMorFeZQUN^4a0z>xeJq~3BwYhUDQpn7?X+8w#=fMf~2-rqS?Q?JfM`&RR?Ux+ph|c&@CNnB}zC|$(!dlH73O$<3u)+fOv)ljYJ^B26d;R5}~UH9yA_L(S`tqS`z@+6bsF}z_Xj8BKQ2S@y&Hxu({ZuLviRzOWt7O1&})I#Ku#kPX!rGQ3s{a^k$T>O20*+do3uojh%!poP%@LSyg6n^=8V-qSdR&FAy!*=O9}a*;XdlS!Pwqn46*kFt5bMPF#P8(>38p!O&N-4PLFc=-UQ{1gri)Qv%?WMAp!rZHQl5Yg4a+X-(Ox@qO6-Bw_m$s~Xe+#Ff{gH5DZgngmqLh=NI+?`511eEnC&D)LDrS0!cbuo}6zlO;X4VQuHo7<J1D^9rZhyF6n%`2}%Ay6$AOVGQeG?4EgEJ*%_N^Ltij&+6=1ojt3wXLa_h&YsoTvpRcLXV2>Fk=(O7dsb)9>g-vaJ*)HOu{x=lY#XAAg`%7|r8CO1Iws1|gFLdu(wbwBPNsHiuyDsq&62gIr-fw?$R`2hs4TH9k+-*4)K(ly@@xr%FvQUz^5$j>rba=z3~dVl0hMvIW=D>M&qN}hm_GJ^6aJI&$hvbz-U?iPidSj3r20l7uWgsY_Amx0=G4HLVPC%f?wrkLgV}+mg_dH~>yY8zZ5x|DD4GNLZR}_xY*i_9o)s&uF51YzC@62;@r`yxIb_#M+WRVvSIBXw?T>?fe!U6Yir=dA&Gcwg1JRY(G~oi@G_(TX#Hko!Z@6ApZRcR{2pi&e!ZK9+Mr19^*km@ij=R6L3T=7TU^{fBGPq8asT$VX*IuiNuV(S0YFvC3+b%ZcRv$l)4zSrcgB1c`H1?y`wUx#WVfFb)bOWw!<~7u0x7K-=O4*|wqgMu&YF{tf6%L2}aB)5S$Kf}qi;4pC7v;5vCh*~sAOi_!oMh!+)s|impprp^bVtRf#34{y>(Mx^8Hyi+WyX!`m>`Fp!RT2Mql-LJ1QS355>u*F@7)5cTD<-m(ep7zE>N1;Coc?{`yQ|cfJH!xNNN2+!S8o_2id9KTu3TDm|J&$Z<!2ijX)$RB1=`wIabeco|b^KZO0q11aaZ2G0Lua_`FEWK7yNUXKlBr%ev{`bktLSS(#!v*!3~pG)-D^TO}DPZU0`cey7_0y<Yu$z54fh_3!oS-|N-C*Q<Z8*WSEk|6Z^Dy<Yu$z54fh?czlH_j>j3_3Gd2)xX#4`QGc*?cFA0yYshb>9%m%B)ne!akkagfWVNNin_OvvrA1>?lEZJW!mi|{?I<*^Z?I;s$w5kWLH$TR(o)(NZ19|?$NATh0YlNfxkO^<N2t^UQDw28W_CGmbZ<lE!b<nZ+pgYmp6sbgHY<JJNGCM++Vrvl^`xlcfVGtGi_-JD8gCZm&={r+%Zbm3`|oalGXc~yKCVvuRgjc6in*_T#Z59$8)_g<JIr4{tu76ojL'''


def materialize(output: Path) -> Path:
    raw = zlib.decompress(base64.b85decode(_PAYLOAD_B85.encode("ascii")))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/architect_consolidation/responses.gpt-5.6-thinking.json"),
    )
    args = parser.parse_args()
    path = materialize(args.output)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
