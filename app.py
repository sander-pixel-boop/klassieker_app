import streamlit as st
import pandas as pd
import pulp
import io

st.set_page_config(page_title="Scorito Klassiekers Manager", layout="wide", page_icon="🚴")

# --- 1. DATA: PRIJZEN (Uit jouw screenshots) ---
PRICES_CSV = """Naam,Prijs
T. Pogačar,7000000
M. van der Poel,6000000
J. Philipsen,5000000
M. Pedersen,4500000
W. van Aert,4500000
J. Milan,3500000
T. Pidcock,3000000
M. Brennan,3000000
A. De Lie,2500000
C. Laporte,2500000
T. Benoot,2500000
T. Wellens,2500000
M. Jorgenson,2500000
T. Merlier,2500000
R. Evenepoel,2500000
F. Ganna,2000000
O. Kooij,2000000
B. Healy,2000000
P. Magnier,2000000
J. Stuyven,1500000
S. Küng,1500000
F. Vermeersch,1500000
N. Politt,1500000
N. Powless,1500000
M. Matthews,1500000
B. Girmay,1500000
M. Bjerg,1500000
M. Mohorič,1500000
R. Grégoire,1500000
M. Skjelmose,1500000
B. Cosnefroy,1500000
K. Groves,1500000
M. Vacek,1500000
T. Skujiņš,1000000
M. Teunissen,1000000
M. Trentin,1000000
J. Narváez,1000000
S. Dillier,1000000
J. Meeus,1000000
D. van Poppel,1000000
T. Nys,1000000
K. Vauquelin,1000000
J. Almeida,1000000
I. del Toro,1000000
A. Yates,1000000
B. McNulty,1000000
F. Großschartner,1000000
P. Bittner,1000000
M. Van Gils,1000000
J. Vingegaard,1000000
G. Vermeersch,750000
D. van Baarle,750000
L. Mozzato,750000
V. Madouas,750000
L. Pithie,750000
D. Teuns,750000
H. Hofstetter,750000
L. Rex,750000
F. Wright,750000
D. Ballerini,750000
S. Wærenskjold,750000
E. Planckaert,750000
M. Gogl,750000
F. Sénéchal,750000
S. Kragh Andersen,750000
G. Ciccone,750000
M. van den Berg,750000
A. Laurance,750000
A. Zingle,750000
O. Riesebeek,750000
L. Martinez,750000
L. Van Eetvelt,750000
O. Onley,750000
T. Bayer,750000
Y. Lampaert,500000
R. Tiller,500000
A. Turgis,500000
J. Degenkolb,500000
B. Turner,500000
K. Asgreen,500000
J. Alaphilippe,500000
J. Tratnik,500000
M. Cort,500000
M. Hoelgaard,500000
E. Theuns,500000
S. Bissegger,500000
J. Rutsch,500000
P. Eenkhoorn,500000
P. Allegaert,500000
M. Valgren,500000
B. Van Lerberghe,500000
C. Bol,500000
I. García Cortina,500000
O. Doull,500000
J. Abrahamsen,500000
O. Naesen,500000
M. Haller,500000
Q. Simmons,500000
M. Louvel,500000
A. Lutsenko,500000
J. Stewart,500000
B. Jungels,500000
T. van der Hoorn,500000
J. Biermans,500000
J. Jacobs,500000
M. Kwiatkowski,500000
M. Walscheid,500000
J. De Buyst,500000
T. Van Asbroeck,500000
G. Moscon,500000
A. Capiot,500000
L. Durbridge,500000
T. Roosen,500000
M. Hirschi,500000
A. Bettiol,500000
P. Roglič,500000
A. Aranburu,500000
A. Bagioli,500000
J. Haig,500000
A. Vlasov,500000
V. Lafay,500000
Q. Hermans,500000
M. Schmid,500000
P. Bilbao,500000
S. Buitrago,500000
D. Martínez,500000
P. Konrad,500000
M. Honoré,500000
R. Adrià,500000
G. Martin,500000
C. Canal,500000
Q. Pacher,500000
T. Geoghegan Hart,500000
B. Mollema,500000
N. Schultz,500000
A. Covi,500000
W. Barguil,500000
W. Kelderman,500000
A. Kron,500000
S. Higuita,500000
A. Kirsch,500000
X. Meurisse,500000
S. Velasco,500000
C. Strong,500000
V. Albanese,500000
A. De Gendt,500000
M. Menten,500000
D. Formolo,500000
A. Segaert,500000
M. Landa,500000
T. Foss,500000
E. Hayter,500000
J. Mosca,500000
D. Van Gestel,500000
A. Vendrame,500000
S. Bennett,500000
A. Kamp,500000
S. Battistella,500000
J. Steimle,500000
M. Schachmann,500000
I. Van Wilder,500000
D. Caruso,500000
M. Govekar,500000
B. Coquard,500000
I. Izagirre,500000
B. Thomas,500000
F. Gall,500000
G. Mühlberger,500000
R. Carapaz,500000
D. Gaudu,500000
T. Gruel,500000
R. Molard,500000
E. Bernal,500000
D. Godon,500000
M. Sobrero,500000
L. Rota,500000
L. Taminiaux,500000
G. Zimmermann,500000
G. Serrano,500000
N. Tesfatsion,500000
G. Bennett,500000
S. Clarke,500000
K. Neilands,500000
D. Smith,500000
S. Williams,500000
E. Dunbar,500000
J. Hindley,500000
K. Bouwman,500000
F. Engelhardt,500000
N. Eekhoff,500000
W. Poels,500000
A. Charmig,500000
N. Conci,500000
D. Ulissi,500000"""

# --- 2. DATA: RATINGS (Met scores 0-10) ---
STATS_CSV = """FirstName	LastName	MarketRiderId	NameShort	RiderId	TeamId	Type	Team	Scorito GC	Scorito Climb	Scorito Time trial	Scorito Punch	Scorito Hill	Scorito Cobbles	Scorito Sprint
Tadej	Pogačar	12910	T. Pogačar	6432	14	Hills	UAE Team Emirates	10	10	10	10	10	8	0
Mathieu	van der Poel	12889	M. van der Poel	6357	121	Cobbles	Alpecin-Premier Tech	0	2	4	10	10	10	4
Mads	Pedersen	12766	M. Pedersen	532	16	Cobbles	Lidl - Trek	0	0	4	6	4	8	8
Wout	van Aert	12834	W. van Aert	1225	30	Cobbles	Team Visma	0	4	10	8	8	9	8
Jasper	Philipsen	12884	J. Philipsen	5398	121	Sprinter	Alpecin-Premier Tech	0	0	0	0	0	8	10
Jonathan	Milan	12982	J. Milan	7166	16	Sprinter	Lidl - Trek	0	0	2	2	0	0	10
Tim	Merlier	12853	T. Merlier	5048	5	Sprinter	Soudal Quick-Step	0	0	0	0	0	2	10
Matthew	Brennan	13178	M. Brennan	8364	30	Sprinter	Team Visma	0	0	0	0	0	0	0
Thomas	Pidcock	13287	T. Pidcock	6504	211	Hills	Pinarello	4	6	2	8	10	4	0
Christophe	Laporte	12744	C. Laporte	261	30	Cobbles	Team Visma	0	0	2	5	4	7	4
Tiesj	Benoot	12784	T. Benoot	723	25	Cobbles	Decathlon	0	4	0	4	8	6	0
Tim	Wellens	12786	T. Wellens	788	14	Cobbles	UAE Team Emirates	0	4	2	4	6	6	0
Remco	Evenepoel	12912	R. Evenepoel	6452	28	Hills	Red Bull - BORA	10	8	10	2	10	0	0
Matteo	Jorgenson	12961	M. Jorgenson	7003	30	Hills	Team Visma	6	6	6	0	6	6	0
Filippo	Ganna	12832	F. Ganna	1220	12	Cobbles	INEOS	0	2	10	0	4	4	2
Olav	Kooij	12996	O. Kooij	7239	25	Sprinter	Decathlon	0	0	0	0	2	2	8
Ben	Healy	13007	B. Healy	7525	42	Hills	EF Education	0	2	2	2	8	0	0
Arnaud	De Lie	13017	A. De Lie	7537	34	Cobbles	Lotto	0	0	0	6	6	8	8
Paul	Magnier	13127	P. Magnier	8032	5	Sprinter	Soudal Quick-Step	0	0	0	2	0	0	4
Nils	Politt	12739	N. Politt	174	14	Cobbles	UAE Team Emirates	0	0	2	0	0	8	0
Michael	Matthews	12762	M. Matthews	507	44	Sprinter	Team Jayco	0	2	2	6	6	4	6
Jasper	Stuyven	12787	J. Stuyven	792	5	Cobbles	Soudal Quick-Step	0	0	0	2	2	6	4
Matej	Mohorič	12813	M. Mohorič	1102	51	Hills	Bahrain	0	2	0	2	6	6	0
Benoît	Cosnefroy	12815	B. Cosnefroy	1169	14	Hills	UAE Team Emirates	0	2	0	6	8	0	0
Neilson	Powless	12870	N. Powless	5324	42	Hills	EF Education	4	4	4	0	6	4	0
Mikkel	Bjerg	12881	M. Bjerg	5389	14	Other	UAE Team Emirates	0	0	6	0	2	4	0
Kaden	Groves	12921	K. Groves	6513	121	Sprinter	Alpecin-Premier Tech	0	0	0	2	2	0	8
Florian	Vermeersch	12956	F. Vermeersch	6991	14	Cobbles	UAE Team Emirates	0	0	0	0	0	6	0
Mattias	Skjelmose	12972	M. Skjelmose	7041	16	Hills	Lidl - Trek	6	4	4	4	8	0	0
Juan	Ayuso	12998	J. Ayuso	7244	16	Hills	Lidl - Trek	8	8	8	0	4	0	0
Biniam	Girmay	13014	B. Girmay	7533	52	Sprinter	NSN Cycling	0	2	0	6	4	4	8
Mathias	Vacek	13039	M. Vacek	7651	16	Cobbles	Lidl - Trek	0	0	4	2	2	0	2
Romain	Grégoire	13070	R. Grégoire	7731	24	Hills	Groupama - FDJ	0	2	0	4	6	0	0
Stefan	Küng	13264	S. Küng	528	206	Cobbles	Tudor	0	0	8	0	2	8	0
Dylan	Groenewegen	13286	D. Groenewegen	1092	251	Sprinter	Unibet	0	0	0	0	0	0	8
Adam	Yates	12769	A. Yates	608	14	Other	UAE Team Emirates	6	8	4	4	6	0	0
Toms	Skujiņš	12770	T. Skujiņš	618	16	Cobbles	Lidl - Trek	0	0	0	4	4	4	0
Danny	van Poppel	12771	D. van Poppel	621	28	Sprinter	Red Bull - BORA	0	0	0	0	0	2	4
Mike	Teunissen	12782	M. Teunissen	702	8	Other	XDS Astana	0	0	0	4	0	4	2
Jhonatan	Narváez	12861	J. Narváez	5283	14	Hills	UAE Team Emirates	0	4	0	6	6	4	4
João	Almeida	12880	J. Almeida	5386	14	Other	UAE Team Emirates	8	8	8	6	6	0	0
Jonas	Vingegaard	12903	J. Vingegaard	6406	30	Hills	Team Visma	10	10	10	2	4	0	0
Maxim	Van Gils	12927	M. Van Gils	6576	28	Hills	Red Bull - BORA	0	2	0	2	6	0	2
Jordi	Meeus	12987	J. Meeus	7177	28	Sprinter	Red Bull - BORA	0	0	0	0	0	2	6
Sam	Welsford	13023	S. Welsford	7548	12	Sprinter	INEOS	0	0	0	0	0	0	6
Kévin	Vauquelin	13042	K. Vauquelin	7659	12	Hills	INEOS	0	0	2	6	4	0	0
Thibau	Nys	13077	T. Nys	7741	16	Hills	Lidl - Trek	0	2	0	8	4	0	0
Isaac	del Toro	13135	I. del Toro	8042	14	Hills	UAE Team Emirates	2	4	2	4	4	0	0
Matteo	Trentin	13275	M. Trentin	402	206	Other	Tudor	0	2	0	2	2	4	2
Milan	Fretin	13328	M. Fretin	7657	13	Sprinter	Cofidis	0	0	0	0	0	0	6
Hugo	Hofstetter	12733	H. Hofstetter	86	52	Other	NSN Cycling	0	0	0	0	2	2	4
Phil	Bauhaus	12777	P. Bauhaus	632	51	Sprinter	Bahrain	0	0	0	0	0	0	6
Giulio	Ciccone	12797	G. Ciccone	913	16	Hills	Lidl - Trek	4	6	0	6	4	0	0
Dylan	van Baarle	12805	D. van Baarle	1076	5	Other	Soudal Quick-Step	0	0	2	0	4	6	0
Valentin	Madouas	12821	V. Madouas	1194	24	Cobbles	Groupama - FDJ	0	2	0	4	4	6	0
Davide	Ballerini	12843	D. Ballerini	2001	8	Other	XDS Astana	0	0	0	2	2	2	2
Fabio	Jakobsen	12859	F. Jakobsen	5281	27	Sprinter	Team Picnic	0	0	0	0	0	0	4
Gianni	Vermeersch	12888	G. Vermeersch	6335	28	Cobbles	Red Bull - BORA	0	0	0	0	2	6	2
Gerben	Thijssen	12907	G. Thijssen	6423	121	Other	Alpecin-Premier Tech	0	0	0	0	0	0	6
Axel	Zingle	12918	A. Zingle	6491	30	Other	Team Visma	0	0	0	4	4	0	4
Laurenz	Rex	12983	L. Rex	7171	5	Cobbles	Soudal Quick-Step	0	0	0	2	2	2	0
Søren	Wærenskjold	12999	S. Wærenskjold	7246	124	Other	Uno-X	0	0	2	2	0	2	2
Casper	van Uden	13000	C. van Uden	7253	27	Sprinter	Team Picnic	0	0	0	0	0	0	4
Marijn	van den Berg	13001	M. van den Berg	7258	42	Other	EF Education	0	0	0	4	2	0	4
Ethan	Vernon	13020	E. Vernon	7541	52	Sprinter	NSN Cycling	0	0	0	0	0	0	4
Axel	Laurance	13030	A. Laurance	7567	12	Other	INEOS	0	0	0	4	4	0	0
Laurence	Pithie	13052	L. Pithie	7683	28	Other	Red Bull - BORA	0	0	0	4	4	4	2
Lenny	Martinez	13071	L. Martinez	7732	51	Other	Bahrain	4	4	2	2	4	0	0
Lennert	Van Eetvelt	13094	L. Van Eetvelt	7793	34	Hills	Lotto	4	6	0	2	4	0	0
Julian	Alaphilippe	13251	J. Alaphilippe	705	206	Other	Tudor	2	4	2	6	6	4	0
Luca	Mozzato	13268	L. Mozzato	6974	206	Other	Tudor	0	0	0	0	0	4	4
Fred	Wright	13288	F. Wright	6987	211	Other	Pinarello	0	0	4	4	4	2	2
Matteo	Moschetti	13311	M. Moschetti	6385	211	Other	Pinarello	0	0	0	0	0	0	4
Dylan	Teuns	13345	D. Teuns	982	13	Other	Cofidis	0	4	2	8	6	4	0
John	Degenkolb	12727	J. Degenkolb	44	27	Other	Team Picnic	0	0	0	0	2	6	2
Davide	Formolo	12728	D. Formolo	72	10	Other	Movistar	2	4	0	2	6	0	0
Yves	Lampaert	12738	Y. Lampaert	167	5	Other	Soudal Quick-Step	0	0	6	0	2	4	0
Bob	Jungels	12742	B. Jungels	250	12	Other	INEOS	0	2	2	0	4	2	0
Alexey	Lutsenko	12743	A. Lutsenko	255	52	Other	NSN Cycling	2	2	2	2	4	2	0
Michał	Kwiatkowski	12746	M. Kwiatkowski	319	12	Other	INEOS	0	2	2	2	4	2	0
Magnus	Cort	12750	M. Cort	349	124	Other	Uno-X	0	2	4	2	4	2	2
Nairo	Quintana	12755	N. Quintana	412	10	Other	Movistar	2	2	0	0	2	0	0
Gianni	Moscon	12767	G. Moscon	533	28	Other	Red Bull - BORA	0	2	2	2	2	2	0
Pello	Bilbao	12773	P. Bilbao	625	51	Other	Bahrain	6	6	6	4	6	0	0
Primož	Roglič	12785	P. Roglič	785	28	Other	Red Bull - BORA	10	10	10	10	8	0	0
Mikel	Landa	12788	M. Landa	803	5	Other	Soudal Quick-Step	6	8	0	2	0	0	0
Daniel Felipe	Martínez	12791	D. Martínez	817	28	Other	Red Bull - BORA	4	6	4	4	4	0	0
Warren	Barguil	12795	W. Barguil	900	27	Other	Team Picnic	0	4	0	4	4	0	0
Alberto	Bettiol	12796	A. Bettiol	908	8	Other	XDS Astana	0	0	4	4	4	2	0
Quentin	Pacher	12800	Q. Pacher	983	24	Other	Groupama - FDJ	0	0	0	4	2	0	0
Guillaume	Martin	12808	G. Martin	1096	24	Other	Groupama - FDJ	4	6	0	4	4	0	0
Jack	Haig	12811	J. Haig	1099	12	Other	INEOS	4	4	0	6	4	0	0
Oliver	Naesen	12814	O. Naesen	1103	25	Cobbles	Decathlon	0	0	0	0	0	2	0
Iván	García Cortina	12817	I. García Cortina	1181	10	Other	Movistar	0	0	0	2	2	2	2
Pascal	Ackermann	12818	P. Ackermann	1184	44	Other	Team Jayco	0	0	0	0	0	0	6
Ben	O'Connor	12819	B. O'Connor	1189	44	Other	Team Jayco	6	8	0	0	4	0	0
David	Gaudu	12820	D. Gaudu	1190	24	Other	Groupama - FDJ	4	4	0	2	4	0	0
Richard	Carapaz	12823	R. Carapaz	1199	42	Other	EF Education	6	8	2	2	6	0	0
Enric	Mas	12826	E. Mas	1204	10	Other	Movistar	8	8	2	0	4	0	0
Tao	Geoghegan Hart	12827	T. Geoghegan Hart	1211	16	Other	Lidl - Trek	2	4	2	4	4	0	0
Lennard	Kämna	12829	L. Kämna	1214	16	Other	Lidl - Trek	4	6	6	0	4	0	0
Egan	Bernal	12850	E. Bernal	2065	12	Other	INEOS	4	6	2	2	4	0	0
Sergio	Higuita	12857	S. Higuita	5091	8	Other	XDS Astana	4	6	0	8	8	0	0
Jai	Hindley	12867	J. Hindley	5318	28	Other	Red Bull - BORA	6	6	0	2	4	0	0
Sepp	Kuss	12869	S. Kuss	5323	30	Other	Team Visma	6	8	2	0	4	0	0
Aleksandr	Vlasov	12873	A. Vlasov	5340	28	Other	Red Bull - BORA	4	4	4	6	4	0	0
Kasper	Asgreen	12886	K. Asgreen	5436	42	Other	EF Education	0	0	6	2	4	6	0
Cees	Bol	12890	C. Bol	6361	25	Other	Decathlon	0	0	0	0	0	2	2
Rasmus	Tiller	12902	R. Tiller	6405	124	Other	Uno-X	0	0	0	0	0	4	0
Andreas	Kron	12908	A. Kron	6426	124	Other	Uno-X	0	0	0	4	4	0	0
Felix	Gall	12914	F. Gall	6455	25	Other	Decathlon	6	6	0	2	4	0	0
Jake	Stewart	12917	J. Stewart	6489	52	Other	NSN Cycling	0	0	0	0	0	2	4
Tobias	Foss	12920	T. Foss	6505	12	Other	INEOS	4	4	6	2	4	0	0
Ilan	Van Wilder	12923	I. Van Wilder	6524	5	Other	Soudal Quick-Step	4	4	4	2	4	0	0
Thymen	Arensman	12926	T. Arensman	6565	12	Other	INEOS	6	6	8	0	2	0	0
Jonas	Abrahamsen	12930	J. Abrahamsen	6912	124	Other	Uno-X	0	0	0	2	0	2	0
Matteo	Sobrero	12939	M. Sobrero	6951	16	Other	Lidl - Trek	0	2	6	2	4	0	0
Alessandro	Covi	12943	A. Covi	6962	44	Other	Team Jayco	0	2	0	4	4	0	0
Attila	Valter	12946	A. Valter	6965	51	Other	Bahrain	2	4	0	0	4	0	0
Ethan	Hayter	12948	E. Hayter	6967	5	Other	Soudal Quick-Step	0	2	8	2	4	0	4
Stefan	Bissegger	12950	S. Bissegger	6972	25	Other	Decathlon	0	0	6	4	2	2	0
Juan Pedro	López	12955	J. López	6990	10	Other	Movistar	4	4	0	0	0	0	0
Matis	Louvel	12957	M. Louvel	6994	52	Other	NSN Cycling	0	0	0	0	0	2	0
Andrea	Bagioli	12958	A. Bagioli	6995	16	Other	Lidl - Trek	0	2	0	6	6	0	0
Alberto	Dainese	12963	A. Dainese	7009	5	Other	Soudal Quick-Step	0	0	0	0	0	0	6
Einer	Rubio	12965	E. Rubio	7015	10	Other	Movistar	4	4	0	0	2	0	0
Santiago	Buitrago	12966	S. Buitrago	7019	51	Other	Bahrain	4	4	0	4	4	0	0
Carlos	Canal	12967	C. Canal	7022	10	Other	Movistar	0	0	0	4	2	0	4
Carlos	Rodríguez	12969	C. Rodríguez	7025	12	Other	INEOS	6	6	4	0	4	0	0
Quinn	Simmons	12970	Q. Simmons	7026	16	Other	Lidl - Trek	2	2	4	4	4	2	0
Antonio	Tiberi	12973	A. Tiberi	7043	51	Other	Bahrain	6	6	6	0	0	0	0
Magnus	Sheffield	12992	M. Sheffield	7229	12	Other	INEOS	0	0	6	0	4	0	0
Mauro	Schmid	12997	M. Schmid	7243	44	Other	Team Jayco	0	0	4	4	4	0	0
Cian	Uijtdebroeks	13005	C. Uijtdebroeks	7520	10	Other	Movistar	6	6	0	0	0	0	0
Ben	Turner	13012	B. Turner	7531	12	Other	INEOS	0	0	0	0	2	4	4
Corbin	Strong	13016	C. Strong	7536	52	Other	NSN Cycling	0	0	0	2	2	0	4
Giulio	Pellizzari	13031	G. Pellizzari	7575	28	Other	Red Bull - BORA	4	6	2	0	0	0	0
Orluis	Aular	13034	O. Aular	7599	10	Other	Movistar	0	0	0	0	2	0	6
Roger	Adrià	13035	R. Adrià	7624	10	Other	Movistar	0	2	0	4	4	0	2
Jenno	Berckmoes	13040	J. Berckmoes	7654	34	Other	Lotto	0	0	0	0	2	0	2
Anthon	Charmig	13043	A. Charmig	7669	124	Other	Uno-X	0	2	0	2	2	0	0
Tobias Halland	Johannessen	13048	T. Johannessen	7674	124	Other	Uno-X	2	4	2	0	2	0	0
Derek	Gee	13055	D. Gee	7686	16	Other	Lidl - Trek	4	6	4	0	4	0	0
Stian	Fredheim	13057	S. Fredheim	7710	124	Other	Uno-X	0	0	0	0	0	0	4
Gleb	Syritsa	13062	G. Syritsa	7717	8	Other	XDS Astana	0	0	0	0	0	0	2
Florian	Lipowitz	13064	F. Lipowitz	7720	28	Other	Red Bull - BORA	6	6	6	0	4	0	0
Thibaud	Gruel	13160	T. Gruel	8178	24	Other	Groupama - FDJ	0	0	0	2	0	0	2
Oscar	Onley	13080	O. Onley	7745	12	Other	INEOS	0	2	0	2	2	0	0
Max	Poole	13081	M. Poole	7746	27	Other	Team Picnic	4	4	0	0	2	0	0
Joshua	Tarling	13083	J. Tarling	7749	12	Other	INEOS	0	0	10	0	0	0	0
Iván	Romeo	13084	I. Romeo	7750	10	Other	Movistar	2	2	4	0	0	0	0
Davide	Piganzoli	13086	D. Piganzoli	7765	30	Other	Team Visma	2	2	0	0	0	0	0
Pablo	Castrillo	13087	P. Castrillo	7769	10	Other	Movistar	0	4	0	0	2	0	0
Matevž	Govekar	13095	M. Govekar	7837	51	Other	Bahrain	0	0	0	2	2	0	2
Paul	Penhoët	13096	P. Penhoët	7838	24	Other	Groupama - FDJ	0	0	0	0	0	0	4
Joseph	Blackmore	13156	J. Blackmore	8166	52	Other	NSN Cycling	0	0	0	0	2	0	0
William Junior	Lecerf	13126	W. Lecerf	8031	5	Other	Soudal Quick-Step	0	2	0	0	2	0	0
Anders	Foldager	13131	A. Foldager	8038	44	Other	Team Jayco	0	0	0	0	0	0	2
Guillermo Thomas	Silva	13137	G. Silva	8059	8	Other	XDS Astana	0	0	0	0	0	0	2
Alec	Segaert	13141	A. Segaert	8075	51	Other	Bahrain	0	0	2	2	0	0	0
Noah	Hobbs	13231	N. Hobbs	8596	42	Other	EF Education	0	0	0	0	0	0	2
Wout	Poels	13250	W. Poels	135	251	Other	Unibet	0	4	0	2	2	0	0
Arvid	De Kleijn	13254	A. De Kleijn	6898	206	Other	Tudor	0	0	0	0	0	0	4
Marco	Haller	13258	M. Haller	328	206	Other	Tudor	0	0	0	0	0	2	0
Marc	Hirschi	13259	M. Hirschi	6433	206	Hills	Tudor	0	4	0	8	8	2	0
Fabian	Lienhard	13265	F. Lienhard	5413	206	Other	Tudor	0	0	0	0	0	0	2
Marius	Mayrhofer	13266	M. Mayrhofer	6509	206	Other	Tudor	0	0	0	0	2	0	4
Rick	Pluimers	13269	R. Pluimers	7829	206	Other	Tudor	0	0	0	0	2	0	4
Michael	Storer	13271	M. Storer	5319	206	Other	Tudor	2	6	0	0	4	0	0
Maikel	Zijlaard	13281	M. Zijlaard	5401	206	Other	Tudor	0	0	2	0	0	0	4
Victor	Lafay	13282	V. Lafay	5298	251	Other	Unibet	0	0	0	6	4	0	0
Clément	Venturini	13284	C. Venturini	1270	251	Other	Unibet	0	0	0	0	0	0	2
Sjoerd	Bax	13292	S. Bax	7559	211	Other	Pinarello	0	0	0	0	2	0	0
Sam	Bennett	13293	S. Bennett	60	211	Other	Pinarello	0	0	0	2	2	0	6
Aimé	De Gendt	13297	A. De Gendt	1001	211	Other	Pinarello	0	0	0	2	0	0	0
David	De La Cruz	13298	D. De La Cruz	413	211	Other	Pinarello	0	4	2	0	2	0	0
Mark	Donovan	13299	M. Donovan	6555	211	Other	Pinarello	0	4	0	0	2	0	0
Eddie	Dunbar	13300	E. Dunbar	5349	211	Other	Pinarello	4	6	0	2	4	0	0
Thomas	Gloag	13302	T. Gloag	7742	211	Other	Pinarello	0	2	0	0	2	0	0
Chris	Harper	13304	C. Harper	6910	211	Other	Pinarello	0	2	0	0	2	0	0
Quinten	Hermans	13305	Q. Hermans	6903	211	Other	Pinarello	0	0	0	4	4	0	0
Damien	Howson	13307	D. Howson	894	211	Other	Pinarello	0	2	2	0	0	0	0
Emils	Liepinš	13308	E. Liepinš	6341	211	Other	Pinarello	0	0	0	0	0	0	2
Xandro	Meurisse	13310	X. Meurisse	331	211	Other	Pinarello	0	2	0	2	2	0	0
Jannik	Steimle	13314	J. Steimle	6930	211	Other	Pinarello	0	0	2	2	2	0	0
Piet	Allegaert	13318	P. Allegaert	1959	13	Other	Cofidis	0	0	0	0	0	2	2
Stanisław	Aniołkowski	13319	S. Aniołkowski	5085	13	Other	Cofidis	0	0	0	0	0	0	4
Alex	Aranburu	13320	A. Aranburu	5061	13	Other	Cofidis	0	2	0	6	6	0	4
Jenthe	Biermans	13321	J. Biermans	1208	13	Other	Cofidis	0	0	0	0	0	2	2
Emanuel	Buchmann	13322	E. Buchmann	79	13	Other	Cofidis	2	2	0	0	2	0	0
Simon	Carr	13323	S. Carr	7017	13	Other	Cofidis	0	2	0	0	2	0	0
Bryan	Coquard	13325	B. Coquard	985	13	Other	Cofidis	0	0	0	2	2	0	6
Ion	Izagirre	13329	I. Izagirre	315	13	Other	Cofidis	0	2	2	2	4	0	0
Alex	Kirsch	13332	A. Kirsch	893	13	Other	Cofidis	0	0	0	2	2	0	2
Sylvain	Moniquet	13338	S. Moniquet	6535	13	Other	Cofidis	0	0	0	0	2	0	0
Hugo	Page	13340	H. Page	7535	13	Other	Cofidis	0	0	0	0	0	0	2
Benjamin	Thomas	13346	B. Thomas	5315	13	Other	Cofidis	0	0	2	2	2	0	0
Emilien	Jeannière	13361	E. Jeannière	7822	26	Other	TotalEnergies	0	0	0	0	0	0	4
Anthony	Turgis	13362	A. Turgis	425	26	Other	TotalEnergies	0	0	0	4	2	4	0
Giovanni	Lonardi	13367	G. Lonardi	6422	138	Other	Team Polti VisitMalta	0	0	0	0	0	0	2
Enrico	Zanoncello	13371	E. Zanoncello	7582	20	Other	Bardiani CSF 7 Saber	0	0	0	0	0	0	2
Dušan	Rajović	13374	D. Rajović	6942	212	Other	Solution Tech NIPPO Rali	0	0	0	0	0	0	2
"""

# --- 3. LOGICA ---

def load_data():
    # 1. Laad Prijzen
    df_prices = pd.read_csv(io.StringIO(PRICES_CSV), sep=',')
    df_prices['Prijs_Clean'] = pd.to_numeric(df_prices['Prijs'], errors='coerce').fillna(0)
    df_prices['Match_Name'] = df_prices['Naam'].str.lower().str.strip()
    
    # 2. Laad Stats (Let op: separator is tab)
    df_stats = pd.read_csv(io.StringIO(STATS_CSV), sep='\t')
    df_stats.rename(columns={
        'NameShort': 'Naam_Stats',
        'Scorito Cobbles': 'Kassei',
        'Scorito Hill': 'Heuvel',
        'Scorito Sprint': 'Sprint',
        'Scorito Punch': 'Punch'
    }, inplace=True)
    df_stats['Match_Name'] = df_stats['Naam_Stats'].str.lower().str.strip()
    
    # 3. Merge
    merged = pd.merge(df_prices, df_stats, on='Match_Name', how='inner')
    
    return merged

df = load_data()

st.title("🏆 Scorito Manager 2026")
st.write(f"Database geladen: **{len(df)} renners** beschikbaar met prijs én statistieken.")

# --- SIDEBAR ---
st.sidebar.header("Instellingen")
budget = st.sidebar.number_input("Budget (€)", value=46000000, step=250000)

st.sidebar.subheader("Strategie Gewicht")
w_kassei = st.sidebar.slider("Kassei (RvV/Roubaix)", 0, 10, 8)
w_heuvel = st.sidebar.slider("Heuvel (LBL/Waalse Pijl)", 0, 10, 6)
w_sprint = st.sidebar.slider("Sprint (Gent/Schelde)", 0, 10, 4)

# Score Berekening
df['Score'] = (
    (df['Kassei'] * w_kassei) +
    (df['Heuvel'] * w_heuvel) +
    (df['Sprint'] * w_sprint) +
    (df['Punch'] * 0.5)
)

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Top Renners (op basis van jouw strategie)")
    st.dataframe(df[['Naam', 'Prijs_Clean', 'Score', 'Kassei', 'Heuvel', 'Sprint']].sort_values('Score', ascending=False).head(10))

with col2:
    st.subheader("Optimalisatie")
    if st.button("🚀 Maak Beste Team"):
        prob = pulp.LpProblem("Scorito", pulp.LpMaximize)
        selection = pulp.LpVariable.dicts("Sel", df.index, cat='Binary')
        
        # Doel
        prob += pulp.lpSum([df['Score'][i] * selection[i] for i in df.index])
        
        # Budget
        prob += pulp.lpSum([df['Prijs_Clean'][i] * selection[i] for i in df.index]) <= budget
        
        # Aantal (20)
        prob += pulp.lpSum([selection[i] for i in df.index]) == 20
        
        prob.solve()
        
        if pulp.LpStatus[prob.status] == 'Optimal':
            idx = [i for i in df.index if selection[i].varValue == 1]
            team = df.loc[idx]
            
            st.success(f"Team Gevonden! Kosten: € {team['Prijs_Clean'].sum():,.0f}")
            st.dataframe(team[['Naam', 'Prijs_Clean', 'Kassei', 'Heuvel', 'Sprint']].sort_values('Prijs_Clean', ascending=False))
        else:
            st.error("Geen team gevonden binnen budget.")
