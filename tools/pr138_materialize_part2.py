from __future__ import annotations

import base64
import json
import lzma
from pathlib import Path

PAYLOAD = """{Wp48S^xk9=GL@E0stWa8~^|S5YJf5;DBKpmR$fnh>C`kTvljae^AtOKu1`=O(ifzFyo3leO9M??7i4$RrcJyKB%aE@hffB_=Sn<
qO!SVL~db@GEQZkd&IqOp<LqK(<9|V&4{%T$&0tw`bFwCaPQ>;!tl)GNnn<htqjpa_q>ZlDD-
3R1=RiDOvZhOAXdvZrv5581aahIbiw#Uzu^c%Cduz=(<C04H2M;d0e4?P#<aC14aB_JQqj-3W}WM$A9k|4IW^TwIF-
{JOg`vE3i}-
6WDqe(qtK9X2w4Zw`O~K?XOK~gk$RiVEt?LNDju>55Wu366lEw@xaB#6%!s~aoI#grRQxGXZ$Zcflb{gKDQW|T)WqZVi#ja6#G2}
Nf?vphWHc0Gi8I6zn(C9i5fRJ;uonT6Kkt0a{jbF8n$kra+1W5bCPPqL+IpC92uOV)Ig#6k1pk~W!s}CCkQz7g0HLn*ZM2?ux;2$
wu#c|hO2CxoIp3epi23xe2@-YrU$j$c*Kd(lXX2yKrL-7Grp-
17vKz;H;G;L$FeO$b_zur2GPr={I5VJ*R_SCNpK_)JHl!|{glT|4BPSpb6gqEfh+{+s@tHlea$ehwLaP$@9~xxF8t)^%!B<pde@2
)uL#9<R8klrdE18Ck#Z+ZUL#Rmaxy@9Q!OKSV2$3jY);6-
^djog{KFw$R>!3;ey=poGyK8+9x&Q42Sl800uBpOg>@NS+$umc$!}F}jD{cVWl?(>yvX&j)Fs5vkW2EvD0P+aTj>x8{ef@Cs;#y*
v3cP99r%8-
@Y`huGo>jmqXUWK6os0X6Ea})Y1r_<C0UKD0Oi;zKt{JqSiX;om_03N7%A%#7tZP^0!Yyt77$o~|BCWR0pDn_^v`v0M2~ZhR<9FO
c>qpcj&6F+XHXuMQdN}KM2F#k1&y7YrBb|vmoWd}ja!HF|IQHvRC<FpufPf4_eC?LutzC^fB@YyJAr8g+BcG=|x5-
;&VQoCmu}eWrsdI!C)uC6dhU=fZs*=Q?WSz@SP0&tlack9NPp?81YbxN`%zQA3?AwDGQ%>jlG#Vg8SqyFLr7>RJmv#5SI&WbIr&M
Mwt0+&%w{ANnNVE_rhf*RDcO%mdWF7#rl@~UdL5>2-
+>Ljy+==ZgvnM3dNV%l4i1^W;4??tInOHA}aEL&6(PyKgFXKa`yd*&^c9PxfR<Ph^k|hN492Kn1VkpW-^+R#O1}juN45-
hMIS~$L#y=%rsemyeS#2Rc`hM7}Wnw6$-
PRlP#n`Y=I5mAS7Cozb@?V3FiHjrDu)mOZ?#XhamzA;^^PrAV(x69*;JX>xnPE5L#b6*+{Z0JR&hB1}1M}^+TbJ}TS2)Yni;NBQd
|zB3rU~XT{}?!$!3KRfoO($yIa&^!m;dB{u#CeAb=02SOt_a#ss7G38kds(AdrA!?CzUtS?2BOGv5q^2W-
i>H>@>Lzgy&h3|5lTs7Cr~WW++&L}m2jGgb>#!hDKdavDZ&n@wi)YUy!wG_;ZXH^LYZVLQdq0;cV~0wKp42SE5OSHRZ+{5#dwg~K
3d#F9||MQt$YNZ6r0I}n-iJ14!5e0W^FyNEfebpwY<u5)A_JuNC1CUujHcxCfonOLHWfb$>9nmX_Q-
!updAq9ftOXhQ|96A}tuW?v2^Xooqgd>g0Uj;laAd{+>UB%vH#DKp|7l7>B0whE=Vi_}K4*d)f3c3yucM0HFW<mo{b2ah2<=KSPG
@N>-
VypmwnJTsR0pwW0h9Ms1dDWpN(IuAL;7IqZz(7cudt^S@n?_a$)vytI(yGt6G#d8+0XsN5%TeVEigFbvr%4l&6cJ!@Hd*qM6uEdg
6Ma^v0~xZ!@Z$RKKgLU?gXuSAgUFg5dmN5g>>uC3oUIs5C^zQwJyQ+x>wvK_Ce}mYklXaA5IooaI5-
#JJwT4){aE50>n2?k2h#ggqxl0Dv~IZKhuKk@6#VzBQb}ml7s8~uSnXSjGg<|_&$dzUfi4EDv{6o-
aG#9Z9dDCS*9aL0Z?8rLUaU69Af-2|<pk9;=e1AHZ6+H6pbFUJ#4O^HVCrE4g@2{sq-
~TL^%aCv$qxT&A*CehE8Y%Xg6I{h{M$@iCD??2Lk2A<>^$PMb|~MaK}w5nSGlvo;y${66Ov#(%)*URRNnp1yE_7~A=YME@+6!TeW
qDLX$NRxm9-
KBjIAoXtVnSsC?yQXVycv$yt6WhMQS!5cfAgz>_6Da4m5nHp4_y^&_rtLdcznRphUab&IxGlGx?0aQ(ooTgN@G$Q`o(wX${j+IYt
IlM%o~NU*HfJJ3(ZMcsr{9CX$#!T^N1%MfWJxmP^N8%;@F5Muc5(u~>AoeM(#Cu!6Xd7eX-D+DS|Yoo>l#)-
req8Od|d1VWjDl$L2`<G?fD6P{N7zkBRW^RfZ^_FCg;web`NJUMN-
@8_3U>|_)LVOLuw+cj@OLMoCt$MYZtGmD9^HWCXL#;sF~T;#%HHJqACyj;8ucxZ=iMk!aY)Y0u4L>6QAQ!OgBgJWoKtbW2EfcYA4
Tg|#6hg<~nP83@CxHXvgG+>1ouXEy8mjX-WU>NscEiJC!R+)BeBq3a9AQj=rRIY2CE5}p2ZSh&M`$=5Tc-
$(prz9cCPV{Lg#qat8_c24?o9fZ7Wf^@%5ulke6XS$i&n@&!ys4ysW;BVfh^hX3RtD^{UY|%B*5W8U^&+`6r!?#(8XGy<XA;%Mi>
H!*nqpV)qgVT=+SjKb_}hwj=UV77f9`FU`&|3;cM~qkA|Zd@R&!e)%At(NL}^JryT@)2Z!eK}4n&BY1{ipL*b+~!TvUX|n%Qy0Zn
Z_$!%IB0cenk8B?qNi_NNtD)g91jwFVYpa@gqAaw&j{OjjM|{gZzP<X}3X?=2&Dl6<G`hqLdwKFx?_I^7JqB#d0wjWjN$+UfMG7#
+ed<zy3YYOLEpQqW`CINVtqJ7!HhK1U?xNGPN+5N4Q0pD%odoF!T;<O9Wr_S8X>u(SO;<$bGf*J-
E^&G>cWKrcI$RG<5KB{kQOrt0Y{6+XOHpOzDQa3hqR)lE!Y#@*Y^Cn!n*wJDUH*_iVoB@I8z1J)IY{cSBh$gb)BL7E_8H%R1&09^
q7pJL;Y;`$J>F00*WEeZ%*e#Wf>mzX-f`TR}MN`EdgQbZ!_aIax**LO|bA!LSVl4YIuD-
+FU0_bCKq^;658_73JYnC30l;H_c88EyhH5}S72gXXNJroI$w;_@w$a-
D}$fSbx7K4vbea8Vu5B$Wy91l1=VfAyWM!Iq*k(zeOh(X|8!+hj4={~xqcGUUxFNH(ztIXtwz!`YK#43m<NBDyFc=EF!LR*pJ5Pr
zJ;=}erLhpe+#|6M51rUC5wmls25f9j^n+LUg!5i-
&LaA!<T0FFaI_M*z++B(6CJ7`|+@cHJ_#hwPUBa5Lv+(W~J=+mjjCSVWl@(%EFse+f7i<z)X*}iyOT|>-
#o<zh=J>rQ_zJ4~OD+>IWK}sLhg#ffQ#qS9GN>uQSPeg^f8dh-
=<Qf&V`54H!<c7;=R9**J4nYmaJcjI4?l~Xj0*ei1uQgb_7EB>WJaX?%T_jjeB28DHVgAIq|Nu2xV%=^xcY{`iRpY13>u8JAW*gN
-@@|JtoxMUd<@9_lX(d?w%(BX(^2h@<%H_Lu)bsa`Bs~7()U{q#nqhHbBe+?JLyBf-
4_g8b))lY#;h_T<AQyxtDy8RaraWjdpm9Bo3#4W(Vt9DFXDwpp@sSud==l`mj>_mVCq>MnFw%~)$eL=58~k!?WbCv;nqds_jTVEd
!Eh7iYFp_4d*W$e#G<(^lZwBP>T|Xdz<vR0p42)-Y{z7zAvO0oczXjWJJPbX7eANs~hQ6NaLw;_h4W3(pUmFfy)LYlF-UYt&;pf$
)P@Zq9*Jo1qub3ZDs*`rsbA{2aVW+!cK@D79s!4)7XWRXqQp8O0VFbf)MhUCn2}RY|@fP98~1)7Uu~>fTqrH<aWRfXMCL%a+8iuo
PsJTIMs5hpju;u_5{(58o!xvica;50lY*Jl}MKp);F}$2gel^Z#0}qQRb7+uFVz^85qvjbFLoZv{$zdz#S!sqw%-
+hV2`P?vFY6vU0m1(AL*!H}iPA0y~3Zr}(TzbC$7`9gI7a?dSCU8CNb8a!Rrv@|8;VkL(fDw|h$?!b>+aGQR2J$qBfAchsK5I)}8
0ND(pvjz3yzDVb3%)Q|@P^%-N&&b+Q>J|0@%TYiq7OZE?sZd<R_^sy$!oaT{PAlP){0-
yAF@R;*Tx5$opZVUv#|3qV<&`LUlHX^;p`Mg0_Z`_lzdY#tfN`NQ17lJ@4z%_^^K?kfE!*E1+e}>T<gnAR{)gl;kM8WYB>LL`?l-
KQzbU+)HPjY1j{IgIPrWc7jz~ID(>CHWlO^Km<BY6l+ZL*SO41$0_p`B$O#IrKUQ_uuIePS@5R@G;vU>h%Xo!W`W_y{lr5qviMqE
w32ZgEp9Nz+jx)&VHxg&lA+)qZ#Vj{r`__!EMMEJrVkG^;;FeBN$G#x~q9GSexv;tkE-CO`0mlla{qo@lvyTx*ZdBfZz>49_7Ox~
i|TFM<#RL%1GZ-6%_@T$8HYMT&Z+`QWyz#K-
Y}kV3_}qcIgi^}MQE9#Ar9R7eG;m`oPw^>dr){1l4UwE=3hT9unyi_EUx1K_1!xS!m@h|V2F9X10lz+>9T76jhTejEA6D{<<H>=w
YjdefXG7mN3YB@|b3`$73>iUjUgrIXHXR#D<{QFL;%k(|(HN*L25lx^jWCIsvE&oRaAkMv!s$@97-
7XeHC<4&G==3GjM1;q_=^9lK8)Vx~dS6{t=@rWJ(1vhrv-1Z8=W4(+#dq}-
TJ*GP~ki`O00UKr5tq;oL=7i1z1=)7jEmD3NGn(jO>fnDH!aDE`YCuV!AVAW<43{e{iHU^BUQY!P%1j!`O#rxo@DjiW7@;n#_Q|P
U+|AIAcPKQfYj0CZId$gVM+~{4`6`rILz)s7=due^FsKXG;pFEh;^9B0i(#~76Dwif$lSXq6i9yvU80c{Spd??3L|Gm6o)AVEw|4
c<h>w}w+yBK0~R6oUfq;B7Jwqo&XX!*cX+6+4O)l<CseWoy(}&Q15zjGJqafZurDXBU$Y%(6m)ICH8zt8Tqr3JyvMK$@t7A}EWzU
!3`Ze%Aggi})qUC%ya~m$8v2d{1afRD9q||)!3i6K5Jvv7Qk@TJI&VVTyq0W>h#^kHWk(lb8S7WlDP)ci8E6@6UVof_*y}Fi654^
gJMGJAP$*-t`otZ*YaF7~Hq%Vd4V7`lliB<C?_dKh4{1db-
$QmPUV1M=eMH&K41Wl9VYqtHVZN|G1$}}$D|qDDpGujYis+WrF}3IdFe_HNCmhj>h2KK+*G?XYrEAF&Qi}Qi1A<@%F6IIlsM~mO&
f7x>Hb=9DD{4!qas1f`CJs1XlntJAQ(~1Sm|12OG$~_Qw0(^wfOCGDs$4dcVq1Xvo7B>|*@%8K9D^3<D`LJ}-2|}pp-
`7B>#*CkE@`kvrkZn<D$0vaiy9j;i&Y!HNe2TQUxBDa<P28cv^-_QTm1N{yIdEKqR95<RkoB9I!a356$}UY);!e9OylQCqG^u-
!4(>FcirC+6h7!vO`9aEkQ*eol)6d(SS_sYAdE@lW}xPs3)^m}exGa}9HUT<^qp?JEOs$qlX%k&UaaXYq~gkpcAxnqz&%L4xCPF!
ycrJ6Ckkkgb2(y*i<P7-
RLf&L4X%yr7YKm#_8wauQ=0{hux@p!;+93D;NV3k$cx{$pr&_^x{dT(u5whjcRLCQV#o^h0$mD;p%5Fq$j}@7Fs9DW;0*qh51h}$
haF&!Sbf`dOl3_ch}<}MH<|`PE|aUj!0KkxZfpL92=W5g@PBiyWg7Il_R4dToOmW<ZmYg1$(~TcInr9>#16ioFKm;*eP>GH3@RM~
VF7N!lqlL|<>|tE@f65)eCuN+PFL9n<wrU7sE`(mXc&HwZ%gZG+?yLS60nOc`)@qj+kNVTFfYH7g0M6(v;(mYG5}^czUN03e%9ym
i=*>XjB=JxGJfj*qVvSSxg;^IwuD<m4XWpo%mMWd@<wJ&zbdGV25D}n{ReM~9`4%HHfc_~&KS_z{%_3ZoHUut8Sm;8hLaC$)%QF3
Yy4_@IJ8AEF4Foft#fL^Gn8Y2skgrwZt-kP%6^AyHy&)``AD6m{(`gN?E?B#W``u7#Mo*eOiAPTOT^9+-X4ZYxUg+-M2@&!-
~!(6Lz>2~tx#(DtzqG?iT$}lf?_$GUHdNHhG#GckY1`W_LyCN;l;!6_1D>hS(n_Uk2>S^F$6)qh5DOhxi_Ozjd6Q(NXm;PslSzr<
mLz3V=>|C*JVnR(qC-ilcdiV>w=!K4Ir;C8O+P*zG4}nQkn@Gr6Dbd2Qe~8{LVGNi3<>Mn+IU@amXTB?`$n$<|2S%dhw$WhehF(P
eP>%ywD&SUyCjCjHIV!qOGqthC|}N$taQp00I>rsfv|&68*e8YZ8P?cu3`2$`P&0HHM^YdwGI7fns$SeCsOoaJ~{-
Arq24z?tbS6eR6fGPwhU=A@cT6q0APCVxel{c2jtkXZLkFhxv%&OZdsX%NzQ!it$R3iI@f{<bfx(Q$|hP#3@dp8F*1ag}}EpsUX|
m@!s_P?-zyx>3qFbRemzR}M<xM>v}!Xil8v4d+h1M^Z^mweXj8_T10wthJk$4Cr*lk2-
S%^pt;qk9HLi)Z{5RG3qS44CQWI(dk)o7~%02R=oX&=Wf)wsj>#Vi@)xeRCSE%?w;$-
dJJ9w9O?^{U|Q?8y4qP^a4;a{EBsQFNkBO5iG(#Pc-a-
d{k!u20zTLg$1VXa@c`0#RU!N6G5FOAH8h_t=u1pbS?J6MhmnhS^do=_#qEKoa%!&&!k6<FGF497flJVVmXr@_)(siBOG<2{60Wd
WV|=mfrW2W#!^yn}<EVYA1x|coz0f9zx~)}xjoa37Muvf4@{-
6rr}IKTK@k*SAHac7h9vu%U1^gVN2T?SZ4n#H9FX!^*j<%5=wcEZ=rIX;^&)YIskC3+Tgp6NL2^cqU^KRoF~TgG*(sECPut2LQ{i
|bS@yXwj5~AgAkXexkHhS@NSeEzRF1a42~>2hm-{P8|1UFov9YUQ;G=pg0M>rdP5IRK$F$f?M9W?e7Kad<_u)87a-
Kn!l0#%0zs9!Aj5L6_1kla8C9ScH5*lm_%e57Ml?eE8^pWYxeMN}Y*fI9(eP!hUrgV%3Z_xa5o4Ld8slxaB^Pho*Hl}IMPMX+ymu
YI%$+WB}#u=3l$tbok!0HGD^2{~C$-
@2?`bZ@uGG~GtdoWIc1EgEJ0k|@Urw4eT&Qz*Lhux({$JeP+Lt|LAAF%QL1VP>ANU)~=VSuaUnO*}07m<nd(3BOyN{pYlRy#y8JS
3+`<zs%jnl+|wUt@EXnyV-!5vi9|FX+5?Z-U5SDLGMU<7ws0qqQkNp=3OiB(Yf`ZJw#J#Sed8Z)EgHZtl<o1-
clB9>X5^UGGZNGdfkjCZl1+>@{`C1U}3z24KcC>zKK?t<%;MMID=%7c?XRbK6MDv%=v4n18;XfK$6iz&7{fDY|ZCXH2bgDnR#6GL
4|^s66~qXNcqDt?0ls0a7h~FJWGCKyJ-daq0A6H8lu-
^;LBhm;4~?;M6YKi%6$>U)cD(l=rg*2R`<Z%Mj7ywzZ$=e)^cbLQD6=B%e3M8Br>$76mNW<`O9mxEgB8*$h7kmfSFykM0p}EsUqU
I59tXqSArC79r&cmtSnqyok}X%7KGs{tLd$GP&588EqA}{chvF#n1HRqpc=FF7!gYBGHu#2<z%{XI%})k=$zrBh9ymR0h$GNOd%N
?#p4P=?X<ZX2-
TiR&%jZOi+7J+>QVuFd{kS+z>rB?&{lU=%sQ+U0F3Cv>LScAZ#mK;%*J@=|u60`sOZ^X)23xmLm$3)T=4^l(yw>X7rCgcjF~14zI
k~TpP|MY#`k3KKh)E@_P3&%MP`XOCsm(!X?U?ZQE;LxmQ3|N37;6JNpGZ;!Ni))VZBA^@{}Zj?yU5n?%i_)2UDq)47-
rOJgm9VIqPh>>;_BqeMF56fC)~CLI3*V*`!?uGA`MN;kfMKMu>ZWE49;Du!CqdlYS$64i*jd2mdn<&$vzYxkg=7Us>$Yd-
2*3TwQffN+Uo^B(q@QHdq$6P$!=2Imn44tLIv?o<pIZ$N4f7@WSfSojLTOR;nB_OA|EY;S2`<8DPQI*9Kw*7a%(^3aH!SQA219DG
|^$ZsV|Q@zWFq#}z9<uaaO%LL`)$XU+M3Mn%Aq;H@9^A<rU09Z$ee&$_bVs%tvECv&{r>WA29m-
;H>MVc&<yK72rz5%<dnby$lc44!mx9e>39rhVB!b$A-+)i3+G&OVrP3u0_NQ&kFKwZ(FK!EHDd$K;|HrK?UTm=4TdM36@?;8w`}-
#F-~V5|xjN1)O>cf@uF0u`_gwRo2N}MR954!Xb|gSv^k9tRB~r1c-O<}PpCRmMZf}Deol)wy`IpwO!)5R1*`9}E_#<ee2|=-
5YQPPTv0aKlYejxWQM4^RyHd(~owSDvl~(jU+29S+&t0%$oMtbP(VG@kzF&*T+%4}fF?$$X{~oT32gcOOdT$YSxNmUqk>|h7o4(&
JEc!vW`-P208X*bkK#~~heN=t*?N{YASC22wE|RUI_3pcI>cf>t1c(;Dd4DRMA>`}|>j12hofAHq7mm?S-
>uM2b?Rb0+ew}s>fK>!%ObFXrTJZQM1QRd9o^HNnl4;0P-
Aa8)f0|z*Nx9h<G$s>dhoTi3jT7~T74|x7H7|!oyeOnTmdvnoR}AxIIY6rO}>It&U2g1I}v}Q+ej26Nv~n?pMmZF-LtRmcW+V7C0
q2}o(fF_5aZml&qvtKV(?o-<+G=3zgXfOT#j48=65ZrD~`beLOT9P-qC^g-RAL|9E(mOf)2~eD|p{5$+4pDZCrUxiXA-
%Cv!GLLUD<`(~)EpZO#+RhyzYw@nJz!RTlz-@V{%J<@oh1Iju*F6UI&3kO#lYZS{CC-St7K5G>OkgvXuhgx$tmIs50Eb5#wyZ|&l
7fTpfR4-_2CPk;{(@5N)!q(0|OM}L->?n36IS#>5}00000rvUH9m;ag200FW$;(!7Ggz_UOvBYQl0ssI200dcD"""

files = json.loads(lzma.decompress(base64.b85decode(PAYLOAD.encode("ascii"))))
for relative, content in files.items():
    path = Path(relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
print(f"materialized {len(files)} reviewed files")
