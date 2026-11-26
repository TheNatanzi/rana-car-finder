import json, re, math, os, sys
import numpy as np

OUT = sys.argv[1]
TAX = 0.09625
HOME = (37.563, -122.3255)
BUDGET = 25000


def hav(lat, lon):
    R = 3958.8
    p1, p2 = math.radians(HOME[0]), math.radians(lat)
    dl = math.radians(lon - HOME[1])
    dp = p2 - p1
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


CITY = {'Alameda': (37.765, -122.242), 'Antioch': (38.005, -121.806), 'Berkeley': (37.872, -122.273),
        'Castro Valley': (37.694, -122.086), 'Concord': (37.978, -122.031), 'Corte Madera': (37.925, -122.527),
        'Daly City': (37.688, -122.470), 'Dublin': (37.702, -121.936), 'Fairfield': (38.249, -122.040),
        'Fremont': (37.548, -121.989), 'Hayward': (37.669, -122.081), 'Livermore': (37.682, -121.768),
        'Martinez': (38.019, -122.134), 'Oakland': (37.804, -122.271), 'Palo Alto': (37.442, -122.143),
        'Petaluma': (38.232, -122.637), 'Pittsburg': (38.028, -121.885), 'Pleasant Hill': (37.948, -122.061),
        'Pleasanton': (37.662, -121.875), 'Redwood City': (37.485, -122.236), 'Richmond': (37.936, -122.348),
        'San Francisco': (37.775, -122.419), 'San Jose': (37.338, -121.886), 'San Leandro': (37.725, -122.156),
        'San Lorenzo': (37.681, -122.124), 'San Pablo': (37.962, -122.346), 'San Rafael': (37.974, -122.531),
        'Santa Clara': (37.354, -121.955), 'Suisun City': (38.238, -122.040), 'Sunnyvale': (37.369, -122.036),
        'Union City': (37.594, -122.044), 'Vallejo': (38.104, -122.257), 'Walnut Creek': (37.906, -122.065)}

MODELS = [('corolla cross', 'Corolla Cross', 'SUV'), ('corolla hatchback', 'Corolla Hatchback', 'Hatchback'),
          ('corolla', 'Corolla', 'Sedan'), ('camry', 'Camry', 'Sedan'), ('prius', 'Prius', 'Hatchback'),
          ('rav4', 'RAV4', 'SUV'), ('bz4x', 'bZ4X', 'SUV'), ('b z4x', 'bZ4X', 'SUV'), ('mirai', 'Mirai', 'Sedan'),
          ('ux', 'UX', 'SUV'), ('crown', 'Crown', 'Sedan')]


def parse_title(t):
    tl = t.lower()
    m = re.search(r'\b(202[3-6])\b', t)
    if not m:
        return None
    y = int(m.group(1))
    make = 'Lexus' if 'lexus' in tl else 'Toyota'
    for k, name, body in MODELS:
        if re.search(r'\b' + k + r'\b', tl):
            hyb = 'hybrid' in tl or 'hybris' in tl
            fuel = 'Gas'
            if name == 'bZ4X':
                fuel = 'Electric'
            elif name == 'Mirai':
                fuel = 'Hydrogen'
            elif name in ('Prius', 'UX') or hyb:
                fuel = 'Hybrid'
            if name == 'Corolla' and hyb:
                name = 'Corolla Hybrid'
            if name == 'Camry' and (hyb or y >= 2025):
                name, fuel = 'Camry Hybrid', 'Hybrid'
            trim = re.sub(r'(?i)\b(202\d|toyota|lexus|sedan|4d|hatchback|sport utility|suv|hybrid|hybris|' + k + r')\b', '', t)
            trim = re.sub(r'\$[\d,]+', '', trim)
            trim = re.sub(r'\s+', ' ', trim).strip(' -,*[]')
            return y, make, name, body, fuel, trim[:36]
    return None


cars = []

# ---------- CarGurus
hist = {l.split()[0]: l.split()[1:] for l in open('hist.txt')}
for x in json.load(open('cg.json')):
    model = x['modelName']
    fuel = {'Gasoline': 'Gas', 'Fuel Cell': 'Hydrogen'}.get(x['localizedFuelType'], x['localizedFuelType'])
    if model == 'Camry' and fuel == 'Hybrid':
        model = 'Camry Hybrid'
    body = {'SUV / Crossover': 'SUV'}.get(x['bodyTypeName'], x['bodyTypeName'])
    h = hist.get(str(x['id']))
    acc = None if not h or h[0] == '-' else int(h[0])
    own = None if not h or h[1] == '-' else int(h[1])
    title = 'clean*'
    extra = []
    dp = 'det/%s.json' % x['id']
    if os.path.exists(dp):
        dj = json.load(open(dp))
        vh = dj.get('vehicleHistory') or {}
        desc = (dj.get('description') or '').lower()
        if vh.get('hasVehicleHistory'):
            if vh.get('accidentCount') is not None:
                acc = vh['accidentCount']
            if vh.get('ownerCount') is not None:
                own = vh['ownerCount']
            if acc is None:
                acc = 0
            title = 'clean'
        if vh.get('isSalvage') or vh.get('isTotalLoss') or vh.get('isTheftTitle') or vh.get('isLemon') or re.search(r'salvage|rebuilt title|branded title', desc):
            title = 'salvage'
        elif vh.get('isFrameDamaged'):
            title = 'frame'
        if vh.get('isFleet') or vh.get('isRentalFleet'):
            extra.append('Former rental or fleet car')
    cars.append(dict(extra=extra,
        src='CarGurus', seller='Dealer' if x['sellerType'] == 'DEALER' else 'Private',
        sellerName=x.get('serviceProviderName') or '', year=x['carYear'], make=x['makeName'], model=model,
        trim=(x.get('trimName') or '').replace(' FWD', ''), body=body, fuel=fuel, price=int(x['price']),
        miles=int(x['mileage']), dist=round(x['distance']), city=x['sellerCity'].replace(', CA', ''),
        market=x.get('expectedPrice'), deal=x.get('dealRating'), acc=acc, own=own, cpo=bool(x.get('isCPO')),
        days=x.get('daysOnMarket'), url='https://www.cargurus.com/Cars/link/%s' % x['id'],
        img=(x.get('originalPictureData') or {}).get('url', ''), vin=x.get('vin', ''), title=title,
        color=x.get('exteriorColorName') or '', phone=x.get('phoneNumberString') or '', note=''))

# ---------- market model fitted on CarGurus market values (log price ~ model + year + miles)
tr = [c for c in cars if c['market']]
mods = sorted({c['model'] for c in tr})


def feat(c):
    return [1.0] + [1.0 if c['model'] == m else 0.0 for m in mods[1:]] + [c['year'] - 2023, c['miles'] / 10000]


A = np.array([feat(c) for c in tr])
yv = np.log(np.array([c['market'] for c in tr], float))
coef, *_ = np.linalg.lstsq(A, yv, rcond=None)
print('market model MAE $', round(float(np.mean(np.abs(np.exp(A @ coef) - np.exp(yv))))), mods)


def est(c):
    if c['model'] not in mods or c['miles'] is None:
        return None
    return int(round(float(np.exp(np.array(feat(c)) @ coef)), -1))


for c in cars:
    c['marketEst'] = False
    if not c['market']:
        c['market'] = est(c)
        c['marketEst'] = True
vins = {c['vin'] for c in cars if c['vin']}

# ---------- Craigslist
for x in json.load(open('cl.json')):
    if x.get('gone') or not x.get('odometer'):
        continue
    p = parse_title(x['title'])
    if not p:
        print('CL skip', x['title'])
        continue
    y, make, model, body, fuel, trim = p
    if x.get('vin'):
        if x['vin'] in vins:
            print('CL duplicate dropped:', x['title'][:45])
            continue
        vins.add(x['vin'])
    d = round(hav(float(x['lat']), float(x['lon']))) if x.get('lat') else None
    loc = x['loc'].title()[:26] if not re.search(r'call|\.com', x['loc'], re.I) else ''
    c = dict(src='Craigslist', seller='Dealer' if x['dealer'] else 'Private', sellerName='', year=y, make=make,
             model=model, trim=trim, body=body, fuel=fuel, price=x['price'],
             miles=int(x['odometer'].replace(',', '')), dist=d, city=loc, market=None, deal=None, acc=None,
             own=None, cpo=bool(re.search(r'certified', x['title'], re.I)), days=None,
             url=x.get('final') or x['url'], img=x.get('img') or '', vin=x.get('vin') or '',
             title=x.get('titlestatus') or '?', color='', phone='', note=x['body'][:200])
    c['market'] = est(c)
    c['marketEst'] = True
    cars.append(c)

# ---------- Facebook
fbdet = json.load(open('fb_det.json', encoding='utf-8')) if os.path.exists('fb_det.json') else {}
seen = set()
for l in open('fb_list.txt', encoding='utf-8'):
    i, price, t, city = l.rstrip('\n').split(';')
    p = parse_title(t)
    if not p:
        print('FB skip', t)
        continue
    y, make, model, body, fuel, trim = p
    cityn = city.replace(', CA', '')
    k = (price, model, y, cityn)
    if k in seen:
        continue
    seen.add(k)
    d = fbdet.get(i, {})
    if d.get('gone'):
        continue
    ll = CITY.get(cityn)
    c = dict(src='Facebook', seller=d.get('seller', 'Unknown'), sellerName='', year=y, make=make, model=model,
             trim=trim, body=body, fuel=fuel, price=int(price), miles=d.get('miles'),
             dist=round(hav(*ll)) if ll else None, city=cityn, market=None, deal=None, acc=None, own=None,
             cpo=False, days=None, url='https://www.facebook.com/marketplace/item/%s/' % i, img='', vin='',
             title=d.get('title', '?'), color='', phone='', note=d.get('note', ''))
    c['market'] = est(c)
    c['marketEst'] = True
    cars.append(c)

# ---------- filters + score
out = []
drop = {}


def dropc(why):
    drop[why] = drop.get(why, 0) + 1


for c in cars:
    if c['fuel'] == 'Hydrogen':
        dropc('Hydrogen Mirai')
        continue
    if c['body'] not in ('Sedan', 'SUV', 'Hatchback'):
        dropc('Not a sedan or SUV')
        continue
    if c['miles'] is not None and c['miles'] > 70000:
        dropc('Over 70k miles')
        continue
    if c['dist'] is not None and c['dist'] > 100:
        dropc('Over 100 miles away')
        continue
    if c['title'] == 'frame':
        dropc('Frame damage')
        continue
    if c['title'] not in ('clean', 'clean*', '?'):
        dropc('Salvage or branded title')
        continue
    fees = 450 if c['seller'] == 'Dealer' else 350
    c['otd'] = int(round(c['price'] * (1 + TAX) + fees))
    c['inBudget'] = c['otd'] <= BUDGET
    c['over'] = max(0, c['otd'] - BUDGET)
    age = max(0.5, 2026.9 - (c['year'] - 0.4))
    if c['market']:
        pct = (c['market'] - c['price']) / c['market']
        c['below'] = int(c['market'] - c['price'])
        sP = max(0, min(40, (pct + 0.10) / 0.25 * 40))
    else:
        c['below'] = None
        sP = 14
    if c['miles'] is not None:
        ratio = c['miles'] / (12000 * age)
        sM = max(0, min(25, (1.6 - ratio) / 1.2 * 25))
    else:
        sM = 8
    sY = 3 + (c['year'] - 2023) * 4
    if c['acc'] is None:
        sH = 5
    elif c['acc'] == 0:
        sH = 10 if c['own'] == 1 else 8 if c['own'] else 7
    elif c['acc'] == 1:
        sH = 3
    else:
        sH = 0
    m = c['miles'] if c['miles'] is not None else 60000
    if c['cpo']:
        sW = 10
    elif m < 36000 and age < 3:
        sW = 7
    elif m < 60000:
        sW = 4
    else:
        sW = 0
    c['parts'] = [round(sP), round(sM), round(sY), round(sH), round(sW)]
    c['score'] = sum(c['parts'])
    flags = list(c.pop('extra', []))
    if flags:
        c['score'] -= 4
    if c['src'] == 'CarGurus' and c['title'] == 'clean*':
        flags.append('Title record not checked')
        if c['market'] and c['price'] < c['market'] * 0.87:
            flags.append('Very cheap: check for salvage')
    if c['fuel'] == 'Electric':
        flags.append('Electric: needs home charging')
    if c['acc']:
        flags.append('%d accident%s reported' % (c['acc'], 's' if c['acc'] > 1 else ''))
    if c['own'] and c['own'] >= 3:
        flags.append('%d owners' % c['own'])
    if c['src'] == 'Facebook' and c['miles'] is None:
        flags.append('Miles not shown: ask seller')
    if c['src'] == 'Facebook' and c['title'] == 'clean':
        flags.append('Clean title per seller: get a Carfax')
    if c['src'] == 'Facebook' and c['title'] == '?':
        flags.append('Title not confirmed: ask seller')
    if c['deal'] in ('OVERPRICED', 'POOR_PRICE'):
        flags.append('Priced high vs market')
    if c['market'] and c['price'] < c['market'] * 0.82 and c['src'] != 'CarGurus':
        flags.append('Very cheap: check for salvage or scam')
    if c['days'] and c['days'] > 75:
        flags.append('%d days unsold: room to negotiate' % c['days'])
    c['flags'] = flags
    c['check'] = 'full' if c['acc'] is not None else 'partial' if c['miles'] is not None else 'low'
    out.append(c)

out.sort(key=lambda c: (-c['score'], c['price']))
for n, c in enumerate(out, 1):
    c['id'] = n
meta = dict(checked='2026-11-25', tax=TAX, budget=BUDGET, home='San Mateo, CA',
            counts={s: sum(1 for c in out if c['src'] == s) for s in ('CarGurus', 'Facebook', 'Craigslist')},
            dropped=drop, cheapestLexus=26593)
os.makedirs(OUT + '/data', exist_ok=True)
json.dump(dict(meta=meta, cars=out), open(OUT + '/data/cars.json', 'w', encoding='utf-8'), separators=(',', ':'))
print(len(out), meta['counts'], drop, 'inBudget', sum(c['inBudget'] for c in out))
for c in out[:14]:
    print(c['score'], c['parts'], c['src'], c['year'], c['model'], c['trim'][:16], c['price'], c['otd'], c['miles'],
          c['market'], c['acc'], c['own'], c['cpo'], c['city'], c['dist'])
