"""Builds pairs.csv (active universe) and removed_pairs.csv (qualitative rejects).

Run once; the scanner only reads pairs.csv. Edit the lists below to add/remove pairs.
Format: "TICKER_A TICKER_B | group"   (removed: "A B | group | reason")
Tickers use Yahoo format (BF-B, BRK-B).
"""
import csv, os

KEEP = """
XOM CVX | Integrated oil
SHEL BP | Integrated oil
SHEL TTE | Integrated oil
BP TTE | Integrated oil
XOM SHEL | Integrated oil
XOM COP | Integrated oil
SU CNQ | Canadian oil
SU IMO | Canadian oil
CNQ CVE | Canadian oil
COP EOG | E&P
EOG DVN | E&P
DVN FANG | E&P
FANG EOG | E&P
COP FANG | E&P
OXY COP | E&P
OXY APA | E&P
APA DVN | E&P
OVV DVN | E&P
PR FANG | E&P Permian
MTDR PR | E&P Permian
SM MTDR | E&P Permian
EQT EXE | Natural gas E&P
EXE AR | Natural gas E&P
EQT AR | Natural gas E&P
RRC AR | Natural gas E&P
EQT RRC | Natural gas E&P
CNX RRC | Natural gas E&P
SLB HAL | Oilfield services
HAL BKR | Oilfield services
SLB BKR | Oilfield services
NOV FTI | Oilfield equipment
HP PTEN | Land drillers
RIG NE | Offshore drillers
MPC VLO | Refiners
VLO PSX | Refiners
MPC PSX | Refiners
DINO PBF | Refiners
KMI WMB | Midstream
WMB OKE | Midstream
OKE TRGP | Midstream
KMI OKE | Midstream
EPD ET | Midstream MLPs
EPD MPLX | Midstream MLPs
ENB TRP | Canadian pipelines
DOW LYB | Commodity chemicals
LYB WLK | Commodity chemicals
OLN WLK | Chlor-alkali
EMN CE | Specialty chemicals
LIN APD | Industrial gases
SHW PPG | Paints & coatings
PPG AXTA | Paints & coatings
SHW RPM | Paints & coatings
ALB SQM | Lithium
CF NTR | Fertilizers
MOS NTR | Fertilizers
NUE STLD | Steel
NUE CMC | Steel
STLD CMC | Steel
FCX SCCO | Copper
FCX TECK | Copper
RIO BHP | Diversified miners
BHP VALE | Diversified miners
NEM AEM | Gold miners
NEM B | Gold miners
AEM B | Gold miners
WPM FNV | Precious metals streamers
AA CENX | Aluminum
MLM VMC | Aggregates
VMC CRH | Aggregates
MLM CRH | Aggregates
EXP MLM | Cement & aggregates
IP PKG | Containerboard
PKG SW | Containerboard
IP SW | Containerboard
BALL CCK | Beverage cans
ADM BG | Ag processing
LMT NOC | Defense primes
NOC GD | Defense primes
LMT GD | Defense primes
LHX NOC | Defense primes
LHX LMT | Defense primes
GD HII | Shipbuilders
RTX GE | Aero engines
TDG HEI | Aero parts
CAT DE | Heavy machinery
DE AGCO | Ag equipment
DE CNH | Ag equipment
AGCO CNH | Ag equipment
PCAR CMI | Heavy trucks
TRN GBX | Railcars
OSK TEX | Specialty vehicles
URI HRI | Equipment rental
FAST GWW | Industrial distribution
GWW MSM | Industrial distribution
FAST MSM | Industrial distribution
AIT MSM | Industrial distribution
ITW DOV | Diversified industrials
PH ITW | Diversified industrials
IR DOV | Diversified industrials
XYL PNR | Water equipment
IEX NDSN | Precision/flow
SNA SWK | Tools
ROK EMR | Automation
ETN HUBB | Electrical equipment
NVT HUBB | Electrical equipment
AYI HUBB | Electrical equipment
AME FTV | Instruments
TT CARR | HVAC
CARR LII | HVAC
TT LII | HVAC
MAS FBIN | Building products
PWR MTZ | Infrastructure contractors
EME FIX | Specialty contractors
J ACM | Engineering services
UNP CSX | Railroads
CP CNI | Canadian railroads
UPS FDX | Parcel delivery
ODFL SAIA | LTL trucking
ODFL XPO | LTL trucking
SAIA XPO | LTL trucking
KNX WERN | Truckload
JBHT HUBG | Intermodal
CHRW EXPD | Freight brokerage
DAL UAL | Airlines
UAL AAL | Airlines
DAL AAL | Airlines
LUV ALK | Airlines
WM RSG | Waste
RSG WCN | Waste
WM WCN | Waste
ADP PAYX | Payroll
PAYC PCTY | HR software
EFX TRU | Credit bureaus
MCO SPGI | Ratings agencies
ICE CME | Exchanges
CME CBOE | Exchanges
NDAQ ICE | Exchanges
RHI MAN | Staffing
LDOS BAH | Gov IT services
CACI SAIC | Gov IT services
LDOS CACI | Gov IT services
CPRT RBA | Vehicle auctions
DUK SO | Utilities Southeast
AEP DUK | Utilities
AEP SO | Utilities
D DUK | Utilities Southeast
D SO | Utilities Southeast
ETR SO | Utilities South
ETR AEP | Utilities
XEL WEC | Utilities Midwest
WEC LNT | Utilities Midwest
LNT XEL | Utilities Midwest
AEE WEC | Utilities Midwest
DTE WEC | Utilities Midwest
CMS WEC | Utilities Midwest
CMS DTE | Utilities Michigan
DTE AEE | Utilities Midwest
AEE CMS | Utilities Midwest
EVRG AEE | Utilities Midwest
EVRG LNT | Utilities Midwest
OGE EVRG | Utilities Plains
ED ES | Utilities Northeast
ED PEG | Utilities Northeast
PEG EXC | Utilities Mid-Atlantic
EXC PPL | Utilities Mid-Atlantic
PPL FE | Utilities Mid-Atlantic
FE EXC | Utilities Mid-Atlantic
PPL AEP | Utilities
EIX PCG | Utilities California
SRE EIX | Utilities California
CNP NI | Utilities gas-heavy
NEE DUK | Utilities large-cap
PNW IDA | Utilities West
POR IDA | Utilities West
PNW POR | Utilities West
ATO OGS | Gas utilities
OGS SR | Gas utilities
AWK CWT | Water utilities
CWT AWR | Water utilities
CEG VST | Power generators
VST NRG | Power generators
JPM BAC | Money-center banks
BAC C | Money-center banks
C WFC | Money-center banks
JPM WFC | Money-center banks
BAC WFC | Money-center banks
JPM C | Money-center banks
USB PNC | Super-regional banks
PNC TFC | Super-regional banks
USB TFC | Super-regional banks
PNC FITB | Super-regional banks
FITB HBAN | Regional banks
HBAN KEY | Regional banks
KEY CFG | Regional banks
CFG RF | Regional banks
RF FITB | Regional banks
MTB CFG | Regional banks
HBAN RF | Regional banks
KEY FITB | Regional banks
TFC RF | Regional banks
ZION WAL | Regional banks West
ZION KEY | Regional banks
EWBC CATY | Regional banks
FHN RF | Regional banks South
WBS VLY | Regional banks Northeast
CFR BOKF | Regional banks Texas/OK
PB CFR | Regional banks Texas
ASB ONB | Regional banks Midwest
UMBF CBSH | Regional banks Midwest
GS MS | Investment banks
SCHW IBKR | Brokers
RJF SF | Wealth/brokerage
LPLA RJF | Wealth/brokerage
EVR LAZ | Advisory boutiques
EVR PJT | Advisory boutiques
BX KKR | Alt managers
KKR APO | Alt managers
APO ARES | Alt managers
BX APO | Alt managers
ARES OWL | Alt managers
CG KKR | Alt managers
TROW BEN | Traditional asset managers
BEN IVZ | Traditional asset managers
TROW IVZ | Traditional asset managers
STT NTRS | Custody banks
BNY STT | Custody banks
NTRS BNY | Custody banks
AXP COF | Card issuers
COF SYF | Card issuers
SYF BFH | Private-label cards
V MA | Card networks
PYPL XYZ | Digital payments
CPAY WEX | Fleet payments
CB TRV | P&C insurers
TRV HIG | P&C insurers
AIG HIG | P&C insurers
ALL PGR | Personal auto insurers
WRB MKL | Specialty insurers
CINF WRB | P&C insurers
AFG CINF | P&C insurers
SIGI THG | Regional P&C insurers
KNSL RLI | E&S insurers
ACGL AXS | Specialty insurers
RNR EG | Reinsurers
MET PRU | Life insurers
PRU LNC | Life insurers
CRBG EQH | Annuity writers
AFL UNM | Supplemental insurers
UNM GL | Supplemental insurers
AON MRSH | Insurance brokers
MRSH AJG | Insurance brokers
AJG BRO | Insurance brokers
WTW AON | Insurance brokers
PSA EXR | Self-storage REITs
EXR CUBE | Self-storage REITs
PSA CUBE | Self-storage REITs
EQIX DLR | Data center REITs
AMT CCI | Tower REITs
CCI SBAC | Tower REITs
AMT SBAC | Tower REITs
PLD FR | Industrial REITs
PLD EGP | Industrial REITs
EGP FR | Industrial REITs
REXR TRNO | Industrial REITs
O NNN | Net lease REITs
O ADC | Net lease REITs
NNN ADC | Net lease REITs
NNN EPRT | Net lease REITs
WPC O | Net lease REITs
SPG MAC | Mall REITs
KIM REG | Shopping center REITs
REG FRT | Shopping center REITs
KIM BRX | Shopping center REITs
FRT KIM | Shopping center REITs
BRX REG | Shopping center REITs
CPT MAA | Apartment REITs Sunbelt
ESS UDR | Apartment REITs coastal
UDR CPT | Apartment REITs
VMRK ESS | Apartment REITs coastal
INVH AMH | Single-family rental REITs
SUI ELS | Manufactured housing REITs
WELL VTR | Senior housing REITs
VTR DOC | Health care REITs
OHI SBRA | Skilled nursing REITs
BXP VNO | Office REITs
SLG VNO | Office REITs NYC
CUZ HIW | Office REITs Sunbelt
HST PK | Hotel REITs
VICI GLPI | Gaming REITs
LAMR OUT | Billboard REITs
CBRE JLL | Real estate services
MRK PFE | Big pharma
PFE BMY | Big pharma
BMY MRK | Big pharma
JNJ MRK | Big pharma
JNJ PFE | Big pharma
ABBV BMY | Big pharma
AZN NVS | European pharma
GSK SNY | European pharma
AZN GSK | European pharma
VTRS TEVA | Generics
ZTS ELAN | Animal health
AMGN GILD | Large biotech
ABBV AMGN | Large biopharma
SYK ZBH | Orthopedics
ZBH SNN | Orthopedics
MDT BSX | Med devices
ABT MDT | Med devices
BDX BAX | Hospital supplies
GEHC PHG | Imaging
TMO DHR | Life science tools
TMO A | Life science tools
A MTD | Lab instruments
IQV ICLR | CROs
MCK COR | Drug distributors
COR CAH | Drug distributors
CAH MCK | Drug distributors
LH DGX | Lab testing
CVS CI | PBM / insurers
HCA UHS | Hospitals
HCA THC | Hospitals
UNH ELV | Managed care
ELV CI | Managed care
CNC MOH | Medicaid managed care
HUM UNH | Medicare Advantage
KO PEP | Soft drinks
TAP BUD | Brewers
STZ TAP | Brewers
BF-B DEO | Spirits
MO BTI | Tobacco
PG CL | Household products
CL CHD | Household products
CHD CLX | Household products
PG KMB | Household products
CL KMB | Household products
PG CHD | Household products
CL CLX | Household products
GIS CAG | Packaged food
CAG CPB | Packaged food
CPB SJM | Packaged food
SJM CAG | Packaged food
GIS CPB | Packaged food
GIS POST | Packaged food
HSY MDLZ | Confectionery
PEP MDLZ | Snacks
HRL TSN | Protein
TSN PPC | Chicken
WMT COST | Mass retail
BJ COST | Warehouse clubs
DG DLTR | Dollar stores
KR ACI | Grocers
CASY MUSA | Convenience stores
SYY USFD | Foodservice distribution
USFD PFGC | Foodservice distribution
SYY PFGC | Foodservice distribution
GM F | Detroit automakers
F STLA | Automakers
TM HMC | Japanese automakers
APTV LEA | Auto parts
BWA LEA | Auto parts
AZO ORLY | Auto parts retail
GPC LKQ | Auto parts distribution
AN LAD | Auto dealers
PAG GPI | Auto dealers
LAD GPI | Auto dealers
ABG AN | Auto dealers
HD LOW | Home improvement
DHI LEN | Homebuilders
LEN PHM | Homebuilders
PHM DHI | Homebuilders
NVR PHM | Homebuilders
DHI NVR | Homebuilders
TOL PHM | Homebuilders
KBH MTH | Homebuilders
TMHC MTH | Homebuilders
TJX ROST | Off-price retail
ROST BURL | Off-price retail
TJX BURL | Off-price retail
ANF AEO | Teen apparel
AEO URBN | Teen apparel
M KSS | Department stores
RL TPR | Luxury/accessible luxury
PVH RL | Apparel brands
VFC PVH | Apparel brands
NKE LULU | Athletic apparel
MCD YUM | Quick service
YUM QSR | Quick service
MCD QSR | Quick service
DPZ PZZA | Pizza chains
DRI TXRH | Casual dining
DRI EAT | Casual dining
TXRH EAT | Casual dining
MAR HLT | Hotels
HLT H | Hotels
MAR H | Hotels
WH CHH | Economy hotels
CCL RCL | Cruise lines
RCL NCLH | Cruise lines
CCL NCLH | Cruise lines
BKNG EXPE | Online travel
VAC HGV | Timeshare
LVS WYNN | Casinos Macau/LV
WYNN MGM | Casinos
MGM LVS | Casinos
CZR MGM | Casinos
CZR BYD | Regional casinos
DKNG FLUT | Online betting
HAS MAT | Toys
THO WGO | RVs
PII HOG | Powersports
DKS ASO | Sporting goods
WSM RH | Home furnishings
FIVE OLLI | Discount retail
EBAY ETSY | Online marketplaces
T VZ | Telecom
VZ TMUS | Telecom
T TMUS | Telecom
CMCSA CHTR | Cable
GOOGL META | Digital advertising
PINS SNAP | Social media
DIS CMCSA | Media conglomerates
OMC WPP | Ad agencies
TXN ADI | Analog semis
ADI MCHP | Analog/MCU semis
MCHP NXPI | MCU semis
NXPI ON | Auto semis
TXN MCHP | Analog/MCU semis
NXPI STM | Auto/industrial semis
ADI NXPI | Analog semis
ON STM | Power semis
MRVL AVGO | Custom silicon/networking
TSM UMC | Foundries
ENPH SEDG | Residential solar
AMAT LRCX | Semi equipment
LRCX KLAC | Semi equipment
AMAT KLAC | Semi equipment
ASML AMAT | Semi equipment
ONTO NVMI | Semi metrology
MKSI ENTG | Semi materials/subsystems
HPQ DELL | PCs
NTAP P | Enterprise storage
STX WDC | Hard drives
ANET CSCO | Networking
FLEX JBL | EMS
APH TEL | Connectors
ARW AVT | Electronics distribution
CDNS SNPS | EDA software
PANW CRWD | Cybersecurity
PANW FTNT | Cybersecurity
FTNT CHKP | Firewalls
CRWD ZS | Cybersecurity
DDOG DT | Observability
SNOW MDB | Data platforms
ADSK PTC | Design software
IBM ACN | IT services
ACN CTSH | IT services
CTSH INFY | IT services
INFY WIT | Indian IT services
EPAM GLOB | IT services
MAA UDR | Apartment REITs
HIG CINF | P&C insurers
PSX DINO | Refiners
CVX COP | Integrated oil
ELV HUM | Managed care
TRV ALL | P&C insurers
WFC USB | Banks
MS SCHW | Wealth/brokerage
ADI ON | Analog/power semis
"""

REMOVED = """
GOOGL GOOG | Digital advertising | Same company (share classes), not a rivals trade
FOXA FOX | Broadcasting | Same company (share classes)
NWSA NWS | Publishing | Same company (share classes)
UNP NSC | Railroads | Pending UNP-NSC merger (STB review, close targeted 2027): spread trades on deal terms
CSX NSC | Railroads | NSC now prices off the UNP takeover, not rail fundamentals
AWK WTRG | Water utilities | Pending all-stock merger (close targeted Q1 2027): pure merger-arb spread
KMB KVUE | Household products | KMB is acquiring Kenvue: deal-driven spread
KO KDP | Soft drinks | KDP bought JDE Peet's and is splitting into beverage + coffee companies
PEP KDP | Soft drinks | Same: KDP is mid-transformation
KHC GIS | Packaged food | Kraft Heinz is splitting into two companies
MMM HON | Conglomerates | Honeywell has been breaking itself up (aerospace and materials spun off)
WAT MTD | Lab instruments | Waters absorbed BD's biosciences/diagnostics unit in Feb 2026: different company now
FIS GPN | Payments | GPN and FIS swapped businesses (Worldpay / Issuer Solutions): history no longer comparable
FIS FISV | Payments | Fiserv's late-2025 guidance reset broke the relationship
LLY NVO | Big pharma | GLP-1 share war: textbook structural divergence, Lilly keeps taking share
NVDA AMD | Semis | AI-accelerator dominance; spread trends instead of reverting
INTC AMD | Semis | Multi-year market-share transfer to AMD; zero-sum rivalry
TSLA GM | Automakers | Tesla trades as a tech/AI story, not an automaker
RIVN LCID | EVs | Cash-burn and dilution driven; no stable relationship
MO PM | Tobacco | PM's smoke-free growth (Zyn/IQOS) vs MO's decline: structural
WMT TGT | Mass retail | Target's multi-year share loss to Walmart
MNST CELH | Energy drinks | Celsius is a momentum/distribution story, not a stable comp
NKE DECK | Athletic footwear | Hoka/Ugg growth partly comes out of Nike's share
KMX CVNA | Used cars | Carvana is taking share from CarMax
ORLY AAP | Auto parts retail | Advance Auto's restructuring and share loss
SBUX MCD | Restaurants | Different businesses; Starbucks turnaround is idiosyncratic
AMZN EBAY | Internet retail | No longer comparable businesses (AWS, ads, logistics)
NFLX DIS | Media | Pure-play streaming vs parks/media conglomerate
SMCI DELL | Servers | Super Micro's governance/accounting issues dominate its price
REGN VRTX | Biotech | Driven by pipeline readouts, not shared fundamentals
MRNA BNTX | Biotech | Binary pipeline/vaccine-demand bets
FSLR ENPH | Solar | Utility-scale/tariff winner vs residential: policy-driven divergence
"""

NAMES = {
 "SHEL":"Shell","BP":"BP","TTE":"TotalEnergies","SU":"Suncor","CNQ":"Canadian Natural","IMO":"Imperial Oil","CVE":"Cenovus",
 "PR":"Permian Resources","MTDR":"Matador","SM":"SM Energy","AR":"Antero Resources","RRC":"Range Resources","CNX":"CNX Resources",
 "NOV":"NOV","FTI":"TechnipFMC","HP":"Helmerich & Payne","PTEN":"Patterson-UTI","RIG":"Transocean","NE":"Noble Corp","DINO":"HF Sinclair",
 "PBF":"PBF Energy","EPD":"Enterprise Products","ET":"Energy Transfer","MPLX":"MPLX","ENB":"Enbridge","TRP":"TC Energy","WLK":"Westlake",
 "OLN":"Olin","EMN":"Eastman Chemical","CE":"Celanese","AXTA":"Axalta","RPM":"RPM International","SQM":"SQM","NTR":"Nutrien",
 "CMC":"Commercial Metals","SCCO":"Southern Copper","TECK":"Teck Resources","RIO":"Rio Tinto","BHP":"BHP","VALE":"Vale",
 "AEM":"Agnico Eagle","B":"Barrick Mining","WPM":"Wheaton Precious Metals","FNV":"Franco-Nevada","AA":"Alcoa","CENX":"Century Aluminum",
 "EXP":"Eagle Materials","CCK":"Crown Holdings","HEI":"HEICO","AGCO":"AGCO","CNH":"CNH Industrial","TRN":"Trinity Industries",
 "GBX":"Greenbrier","OSK":"Oshkosh","TEX":"Terex","HRI":"Herc Holdings","MSM":"MSC Industrial","AIT":"Applied Industrial Tech",
 "NVT":"nVent","AYI":"Acuity","FBIN":"Fortune Brands","MTZ":"MasTec","ACM":"AECOM","CP":"Canadian Pacific Kansas City","CNI":"Canadian National",
 "SAIA":"Saia","XPO":"XPO","KNX":"Knight-Swift","WERN":"Werner","HUBG":"Hub Group","AAL":"American Airlines","ALK":"Alaska Air",
 "WCN":"Waste Connections","PAYC":"Paycom","PCTY":"Paylocity","TRU":"TransUnion","RHI":"Robert Half","MAN":"ManpowerGroup",
 "BAH":"Booz Allen","CACI":"CACI","SAIC":"SAIC","RBA":"RB Global","OGE":"OGE Energy","IDA":"IDACORP","POR":"Portland General",
 "OGS":"ONE Gas","SR":"Spire","CWT":"California Water","AWR":"American States Water","WTRG":"Essential Utilities","ZION":"Zions",
 "WAL":"Western Alliance","EWBC":"East West Bancorp","CATY":"Cathay General","FHN":"First Horizon","WBS":"Webster Financial",
 "VLY":"Valley National","CFR":"Cullen/Frost","BOKF":"BOK Financial","PB":"Prosperity Bancshares","ASB":"Associated Banc-Corp",
 "ONB":"Old National","UMBF":"UMB Financial","CBSH":"Commerce Bancshares","SF":"Stifel","LPLA":"LPL Financial","EVR":"Evercore",
 "LAZ":"Lazard","PJT":"PJT Partners","OWL":"Blue Owl","CG":"Carlyle","BFH":"Bread Financial","WEX":"WEX","MKL":"Markel",
 "AFG":"American Financial","SIGI":"Selective Insurance","THG":"Hanover Insurance","KNSL":"Kinsale","RLI":"RLI","AXS":"AXIS Capital",
 "RNR":"RenaissanceRe","LNC":"Lincoln National","CRBG":"Corebridge","EQH":"Equitable","UNM":"Unum","CUBE":"CubeSmart","FR":"First Industrial",
 "EGP":"EastGroup","REXR":"Rexford Industrial","TRNO":"Terreno","NNN":"NNN REIT","ADC":"Agree Realty","EPRT":"Essential Properties",
 "WPC":"W. P. Carey","MAC":"Macerich","BRX":"Brixmor","AMH":"American Homes 4 Rent","SUI":"Sun Communities","ELS":"Equity LifeStyle",
 "OHI":"Omega Healthcare","SBRA":"Sabra","VNO":"Vornado","SLG":"SL Green","CUZ":"Cousins Properties","HIW":"Highwoods","PK":"Park Hotels",
 "GLPI":"Gaming and Leisure Properties","LAMR":"Lamar","OUT":"Outfront Media","JLL":"Jones Lang LaSalle","NVO":"Novo Nordisk","AZN":"AstraZeneca",
 "NVS":"Novartis","GSK":"GSK","SNY":"Sanofi","TEVA":"Teva","ELAN":"Elanco","BNTX":"BioNTech","SNN":"Smith & Nephew","PHG":"Philips",
 "ICLR":"ICON","THC":"Tenet","MOH":"Molina","TAP":"Molson Coors","BUD":"AB InBev","DEO":"Diageo","BTI":"British American Tobacco",
 "CAG":"Conagra","CPB":"Campbell's","POST":"Post Holdings","PPC":"Pilgrim's Pride","BJ":"BJ's Wholesale","ACI":"Albertsons","MUSA":"Murphy USA",
 "USFD":"US Foods","PFGC":"Performance Food Group","STLA":"Stellantis","TM":"Toyota","HMC":"Honda","LEA":"Lear","BWA":"BorgWarner",
 "LKQ":"LKQ","AN":"AutoNation","LAD":"Lithia Motors","PAG":"Penske Automotive","GPI":"Group 1 Automotive","ABG":"Asbury Automotive",
 "TOL":"Toll Brothers","KBH":"KB Home","MTH":"Meritage Homes","TMHC":"Taylor Morrison","BURL":"Burlington","ANF":"Abercrombie & Fitch",
 "AEO":"American Eagle","URBN":"Urban Outfitters","M":"Macy's","KSS":"Kohl's","PVH":"PVH","VFC":"VF Corp","QSR":"Restaurant Brands",
 "PZZA":"Papa John's","TXRH":"Texas Roadhouse","EAT":"Brinker","H":"Hyatt","WH":"Wyndham Hotels","CHH":"Choice Hotels","VAC":"Marriott Vacations",
 "HGV":"Hilton Grand Vacations","CZR":"Caesars","BYD":"Boyd Gaming","DKNG":"DraftKings","FLUT":"Flutter","MAT":"Mattel","THO":"Thor Industries",
 "WGO":"Winnebago","PII":"Polaris","HOG":"Harley-Davidson","DKS":"Dick's Sporting Goods","ASO":"Academy Sports","RH":"RH","FIVE":"Five Below",
 "OLLI":"Ollie's","ETSY":"Etsy","PINS":"Pinterest","SNAP":"Snap","WPP":"WPP","STM":"STMicroelectronics","TSM":"TSMC","UMC":"UMC",
 "SEDG":"SolarEdge","ASML":"ASML","ONTO":"Onto Innovation","NVMI":"Nova","MKSI":"MKS","ENTG":"Entegris","ARW":"Arrow Electronics",
 "AVT":"Avnet","CHKP":"Check Point","ZS":"Zscaler","DT":"Dynatrace","SNOW":"Snowflake","MDB":"MongoDB","INFY":"Infosys","WIT":"Wipro",
 "EPAM":"EPAM","GLOB":"Globant","RIVN":"Rivian","LCID":"Lucid","CELH":"Celsius","CVNA":"Carvana","KMX":"CarMax","AAP":"Advance Auto Parts",
 "BF-B":"Brown-Forman","GOOG":"Alphabet (C)","FOX":"Fox (B)","NWS":"News Corp (B)","KVUE":"Kenvue","KDP":"Keurig Dr Pepper","ENPH":"Enphase","OVV":"Ovintiv",
}

def load_sp500(path):
    out = {}
    if os.path.exists(path):
        for r in csv.DictReader(open(path)):
            out[r["Symbol"].replace(".", "-")] = (r["Security"], r["GICS Sub-Industry"])
    return out

def parse(block, with_reason=False):
    rows = []
    for line in block.strip().splitlines():
        parts = [p.strip() for p in line.split("|")]
        a, b = parts[0].split()
        rows.append((a, b, parts[1], parts[2] if with_reason else ""))
    return rows

def main(sp500_csv="../dl/sp500.csv"):
    sp = load_sp500(sp500_csv)
    name = lambda t: NAMES.get(t) or (sp[t][0] if t in sp else t)
    keep, removed = parse(KEEP), parse(REMOVED, True)
    seen, dupes = set(), []
    for a, b, *_ in keep + removed:
        k = frozenset((a, b))
        if k in seen: dupes.append((a, b))
        seen.add(k)
    assert not dupes, f"duplicate pairs: {dupes}"
    with open("pairs.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["ticker_a", "ticker_b", "name_a", "name_b", "group"])
        for a, b, g, _ in keep: w.writerow([a, b, name(a), name(b), g])
    with open("removed_pairs.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["ticker_a", "ticker_b", "name_a", "name_b", "group", "reason"])
        for a, b, g, r in removed: w.writerow([a, b, name(a), name(b), g, r])
    missing = sorted({t for a, b, *_ in keep for t in (a, b) if t not in sp and t not in NAMES})
    print(f"candidates={len(keep)+len(removed)} kept={len(keep)} removed={len(removed)} "
          f"tickers={len({t for a,b,*_ in keep for t in (a,b)})}")
    if missing: print("no name for:", missing)

if __name__ == "__main__":
    main()
