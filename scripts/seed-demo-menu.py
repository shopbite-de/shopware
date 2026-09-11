#!/usr/bin/env python3
# Seeds the demo menu (categories, property groups, products, cross-sellings) into the
# "Demo" sales channel via the Admin sync API. Idempotent: all IDs are derived from the
# menu numbers, so re-running updates instead of duplicating.
#
#   python3 scripts/seed-demo-menu.py <integration-key> <integration-secret> [--dry]
#
# Needs scripts/lafattoria.json (scraped from pizzeria-lafattoria.de) next to it.
import json, sys, uuid, urllib.request, re
KEY, SECRET = sys.argv[1], sys.argv[2]
U = 'https://shopware.shopbite.de'
NS = uuid.UUID('7b1f1f4e-3c2a-4a8e-9d3e-5e1a2b3c4d5e')
def hid(key): return uuid.uuid5(NS, key).hex
def req(path, data=None, token=None, headers=None):
    r = urllib.request.Request(U+path, data=json.dumps(data).encode() if data is not None else None, method='POST' if data is not None else 'GET')
    r.add_header('Content-Type','application/json'); r.add_header('Accept','application/json')
    for k,v in (headers or {}).items(): r.add_header(k,v)
    if token: r.add_header('Authorization','Bearer '+token)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp: return resp.status, json.loads(resp.read() or b'{}')
    except urllib.error.HTTPError as e: return e.code, e.read()[:3000].decode(errors='replace')
s,t = req('/api/oauth/token', {'grant_type':'client_credentials','client_id':KEY,'client_secret':SECRET}); tok=t['access_token']
A=lambda x:x.get('attributes',x)
def search(e,b):
    s,r=req(f'/api/search/{e}',b,token=tok); assert s==200,(e,r); return [A(x) for x in r['data']]

# --- context from the shop
sc = search('sales-channel',{'filter':[{'type':'equals','field':'name','value':'Demo'}]})[0]
SC_ID, NAV_ID, CUR_ID = sc['id'], sc['navigationCategoryId'], sc['currencyId']
taxes = {t['taxRate']:t['id'] for t in search('tax',{'limit':10})}
TAX7, TAX19 = taxes[7.0], taxes[19.0]
dt = search('delivery-time',{'filter':[{'type':'equals','field':'name','value':'Sofort verfügbar'}]})[0]['id']
speise = search('category',{'filter':[{'type':'equals','field':'name','value':'Speisekarte'},{'type':'equals','field':'parentId','value':NAV_ID}]})[0]
MENU_ID = speise['id']
vors = search('category',{'filter':[{'type':'equals','field':'name','value':'Vorspeisen'},{'type':'equals','field':'parentId','value':MENU_ID}]})
VORS_ID = vors[0]['id'] if vors else hid('category:vorspeisen')
print('sales channel', SC_ID, 'menu', MENU_ID, 'vorspeisen', VORS_ID)

# --- categories (flat under Speisekarte)
CATS = [  # key, name, icon
 ('vorspeisen','Vorspeisen','i-lucide-soup'),
 ('salate','Salate','i-lucide-salad'),
 ('pizza','Pizza','i-lucide-pizza'),
 ('nudeln','Nudeln','i-lucide-wheat'),
 ('fleisch','Fleischgerichte','i-lucide-beef'),
 ('fisch','Fisch','i-lucide-fish'),
 ('extras','Extras & Beilagen','i-lucide-french-fries'),
 ('nachtisch','Nachtisch','i-lucide-ice-cream-cone'),
 ('getraenke','Getränke','i-lucide-cup-soda'),
]
cat_id = {k: (VORS_ID if k=='vorspeisen' else hid('category:'+k)) for k,_,_ in CATS}
cat_payload=[]; prev=None
for k,name,icon in CATS:
    p={'id':cat_id[k],'parentId':MENU_ID,'name':name,'active':True,'visible':True,'type':'page','productAssignmentType':'product','displayNestedProducts':True,'customFields':{'shopbite_category_icon':icon}}
    if prev: p['afterCategoryId']=prev
    prev=cat_id[k]; cat_payload.append(p)
cat_payload.append({'id':MENU_ID,'customFields':{'shopbite_category_icon':'i-lucide-utensils'}})

# --- products
site = json.load(open(__import__('os').path.join(__import__('os').path.dirname(__file__),'lafattoria.json')))
def S(nr): return site[str(nr)]
IT='Italienisch'; DE='Deutsch'
# (nr, category, name override, description override, ingredients, veggie, vegan, kitchen, tax, factor, crosssell)
P=[]
def add(nr,cat,name=None,desc=None,ing=None,veg=False,vegan=False,kitchen=IT,tax=7,factor=1,xs=None,price=None):
    src=site.get(str(nr),{}); P.append(dict(nr=str(nr),cat=cat,name=name or src.get('name'),desc=desc if desc is not None else src.get('desc'),ing=ing or [],veg=veg,vegan=vegan,kitchen=kitchen,tax=tax,factor=factor,xs=xs,price=price if price is not None else src.get('price')))
add(1,'vorspeisen',desc='Krabbencocktail mit Toastbrot',ing=['Krabben','Cocktailsoße','Toastbrot'])
add(3,'vorspeisen','Mozzarella Caprese','Tomaten und Mozzarella mit Basilikum und Olivenöl',['Tomaten','Mozzarella','Basilikum'],veg=True)
add(4,'vorspeisen',desc='Gebackener Camembert mit Preiselbeeren und Toastbrot',ing=['Camembert','Preiselbeeren','Toastbrot'],veg=True)
add(6,'vorspeisen',desc='Meeresfrüchtesalat mit Olivenöl und Zitrone',ing=['Meeresfrüchte','Olivenöl','Zitrone'])
add(12,'salate',ing=['Eisbergsalat','Zwiebeln'],veg=True,vegan=True)
add(14,'salate',ing=['Tomaten','Thunfisch','Zwiebeln'])
add(16,'salate',ing=['Ei','Eisbergsalat','Käse','Meeresfrüchte','Mozzarella','Schinken'])
add(18,'salate',ing=['Eisbergsalat','Gurken','Hähnchenbrustfilet','Käse','Mais','Tomaten','Zwiebeln'])
add(20,'salate',ing=['Eisbergsalat','Gurken','Tomaten','Zwiebeln'],veg=True,vegan=True)
PZ=[(21,'Pizza Margherita',[],True,False),(22,'Pizza Salami',['Salami'],False,False),(23,'Pizza Prosciutto',['Schinken'],False,False),(24,'Pizza Funghi',['Pilze'],True,False),(26,'Pizza Mix',['Pilze','Salami','Schinken'],False,False),(27,'Pizza Romana',['Salami','Shrimps','Zucchini','Zwiebeln'],False,False),(29,'Pizza Quattro Stagioni',['Artischocken','Salami','Schinken','Zwiebeln'],False,False),(30,'Pizza Calzone',['Champignons','Paprika','Salami','Schinken'],False,False),(31,'Pizza Tonno',['Knoblauch','Thunfisch','Zwiebeln'],False,False),(32,'Pizza Hawaii',['Ananas','Schinken'],False,False),(35,'Pizza Diavolo',['Knoblauch','Peperoni (scharf)','Peperoniwurst'],False,False),(38,'Pizza Vegetaria',['Brokkoli','Pilze','Zucchini','Zwiebeln'],True,False),(46,'Pizza Quattro Formaggi',['Gorgonzola','Mozzarella','Parmesan'],True,False)]
for nr,name,ing,veg,vegan in PZ:
    add(nr,'pizza',name,'Mit Tomatensoße und Käse'+(', '+', '.join(ing) if ing else ''),['Tomatensoße','Käse']+ing,veg,vegan,xs='extras')
add(48,'pizza','Pizzabrot Knoblauch','Pizzabrot mit Knoblauch und Olivenöl',['Knoblauch','Olivenöl'],veg=True,vegan=True,xs='extras')
PA=[(50,'Spaghetti Napoli','Spaghetti in Tomatensoße',['Tomatensoße'],True,True),(51,'Spaghetti Bolognese','Spaghetti in Hackfleischsoße',['Hackfleischsoße'],False,False),(52,'Spaghetti Carbonara','Spaghetti mit Vorderschinken und Ei in Sahnesoße',['Vorderschinken','Ei','Sahnesoße'],False,False),(54,'Spaghetti Aglio e Olio','Spaghetti mit Knoblauch, Olivenöl und scharfen Peperoni',['Knoblauch','Olivenöl','Peperoni (scharf)'],True,True),(56,'Spaghetti Frutti di Mare','Spaghetti mit Meeresfrüchten und Knoblauch in Tomatensoße',['Meeresfrüchte','Knoblauch','Tomatensoße'],False,False),(58,'Spaghetti Gorgonzola','Spaghetti in Gorgonzolasoße',['Gorgonzolasoße'],True,False),(63,'Rigatoni Quattro Formaggi','Rigatoni mit vier Sorten Käse in Sahnesoße',['Käse','Sahnesoße'],True,False),(70,'Tagliatelle Bolognese','Bandnudeln in Bolognesesoße',['Hackfleischsoße'],False,False),(80,'Penne all\'Arrabbiata','Penne mit Oliven, scharfen Peperoni und Knoblauch in Tomatensoße',['Oliven','Peperoni (scharf)','Knoblauch','Tomatensoße'],True,True),(93,'Gnocchi Bolognese','Gnocchi in Hackfleischsoße',['Hackfleischsoße'],False,False),(95,'Lasagne','Eier-Nudelteigscheiben mit Hackfleisch- und Bechamelsoße, überbacken',['Hackfleischsoße','Bechamelsoße','Käse'],False,False)]
for nr,name,desc,ing,veg,vegan in PA: add(nr,'nudeln',name,desc,ing,veg,vegan)
ME=[(103,'Schnitzel Wiener Art','Paniertes Schweineschnitzel nach Wiener Art mit Pommes frites',DE),(105,'Rahmschnitzel','Paniertes Schnitzel mit Rahmsoße und Pommes frites',DE),(111,'Prager Schnitzel','Paniertes Schnitzel mit Vorderschinken, Spargel und Rahmsoße, überbacken',DE),(112,'Cordon Bleu','Paniertes Schnitzel gefüllt mit Schinken und Käse',DE),(115,'Scaloppina al Vino Bianco','Kalbsschnitzel in Weißweinsoße',IT),(119,'Scaloppina ai Funghi','Kalbsschnitzel mit frischen Pilzen in Sahnesoße',IT),(123,'Bistecca alla Griglia','Gegrilltes Rumpsteak',IT),(125,'Bistecca al Gorgonzola','Rumpsteak in Gorgonzolasoße',IT)]
for nr,name,desc,k in ME: add(nr,'fleisch',name,desc,[],kitchen=k,factor=2)
FI=[(133,'Calamari Fritti','Frittierte Tintenfischringe mit Knoblauchsoße'),(135,'Scampi alla Provinciale','Garnelen mit Knoblauch in Tomaten-Weißweinsoße'),(139,'Salmone alla Griglia','Gegrilltes Lachsfilet mit Zitrone'),(140,'Salmone all\'Aglio','Lachs in Knoblauchsoße mit Salzkartoffeln')]
for nr,name,desc in FI: add(nr,'fisch',name,desc,[],factor=2)
SIDES=[(200,'Portion Pommes frites',True,True),(201,'Portion Reis',True,True),(202,'Portion Kroketten',True,False),(203,'Portion Bratkartoffeln',True,True),(204,'Portion Joghurtsoße',True,False),(205,'Portion Knoblauchsoße',True,False),(206,'Portion Salzkartoffeln',True,True),(207,'Portion Gemüse',True,True)]
for nr,name,veg,vegan in SIDES: add(nr,'extras',name,'',[],veg,vegan)
add(141,'nachtisch','Tartufo','Schokoladeneis mit knuspriger Kakaohülle und flüssigem Schokoladenkern',[],True)
add(144,'nachtisch','Tiramisu','Hausgemachtes Tiramisu mit Espresso und Mascarpone',[],True)
add(145,'nachtisch','Lavakuchen','Warmer Schokoladenkuchen mit flüssigem Kern und einer Kugel Vanilleeis',[],True)
DR=[(300,'Coca-Cola 0,33 l',2.5),(301,'Coca-Cola Zero 0,33 l',2.5),(302,'Fanta Orange 0,33 l',2.5),(303,'Mineralwasser 0,5 l',2.0),(304,'Apfelschorle 0,5 l',2.5),(305,'Eistee Pfirsich 0,33 l',2.5)]
for nr,name,price in DR: add(nr,'getraenke',name,'',[],True,True,tax=19,price=price)
EX=[(900,'Extra Käse',1.0),(901,'Extra Salami',1.5),(902,'Extra Schinken',1.5),(903,'Extra Pilze',1.0),(904,'Extra Peperoni (scharf)',1.0),(905,'Extra Zwiebeln',0.8),(906,'Extra Oliven',1.0),(907,'Extra Mozzarella',1.5)]
for nr,name,price in EX: add(nr,None,name,'',[],price=price)

# --- property groups
# variants: product nr -> {group: [(option, surcharge)]}
SIDES_OPT=[('Pommes frites',0),('Bratkartoffeln',0),('Kroketten',0),('Reis',0)]
VARIANTS={}
for nr,_,_,_,_ in PZ: VARIANTS[str(nr)]={'Größe':[('Normal 30 cm',0),('Groß 40 cm',3.0)]}
for nr,_,_,_ in ME:
    VARIANTS[str(nr)]={'Beilage':SIDES_OPT}
    if nr in (123,125): VARIANTS[str(nr)]['Garstufe']=[('Medium',0),('Durchgebraten',0)]
groups={'Hauptzutaten':sorted({i for p in P for i in p['ing']}),'Vegetarisch':['Ja'],'Vegan':['Ja'],
        'Größe':[o for o,_ in VARIANTS['21']['Größe']],'Beilage':[o for o,_ in SIDES_OPT],'Garstufe':['Medium','Durchgebraten']}
pg_payload=[]; opt={}
for pos,(g,opts) in enumerate(groups.items()):
    gid=hid('pg:'+g); pg_payload.append({'id':gid,'name':g,'displayType':'text','sortingType':'alphanumeric','filterable': g in ('Vegetarisch','Vegan','Küche'),'visibleOnProductDetailPage':True,'position':pos,'options':[{'id':hid('po:'+g+':'+o),'name':o,'position':i} for i,o in enumerate(opts)]})
    for o in opts: opt[(g,o)]=hid('po:'+g+':'+o)

def money(gross,rate): return {'currencyId':CUR_ID,'gross':round(gross,2),'net':round(gross/(1+rate/100),4),'linked':True}
prod_payload=[]; xs_payload=[]; variant_payload=[]
pid={p['nr']:hid('product:'+p['nr']) for p in P}
for p in P:
    props=[{'id':opt[('Hauptzutaten',i)]} for i in p['ing']]
    if p['vegan']: props.append({'id':opt[('Vegan','Ja')]})   # vegan implies vegetarian, only one badge
    elif p['veg']: props.append({'id':opt[('Vegetarisch','Ja')]})
    numbered=int(p['nr'])<900
    d={'id':pid[p['nr']],'productNumber':('LF-' if numbered else 'EXTRA-')+p['nr'],'name':p['name'],'description':p['desc'] or '','stock':999,'active':True,'taxId':TAX7 if p['tax']==7 else TAX19,'price':[money(p['price'],p['tax'])],'deliveryTimeId':dt,'minPurchase':1,'purchaseSteps':1,'isCloseout':False,
       'visibilities':[{'id':hid('vis:'+p['nr']),'salesChannelId':SC_ID,'visibility':30}],'properties':props,
       'customFields':{'shopbite_receipt_print_type':'number' if numbered else 'label','shopbite_delivery_time_factor':p['factor']}}
    if p['cat']: d['categories']=[{'id':cat_id[p['cat']]}]
    prod_payload.append(d)
    if p['nr'] in VARIANTS:
        import itertools
        spec=VARIANTS[p['nr']]
        d['configuratorSettings']=[{'id':hid('cs:'+p['nr']+':'+g+':'+o),'optionId':opt[(g,o)]} for g,opts in spec.items() for o,_ in opts]
        d['variantListingConfig']={'displayParent':True,'mainVariantId':None}
        for combo in itertools.product(*[[(g,o,sur) for o,sur in opts] for g,opts in spec.items()]):
            key='|'.join(o for _,o,_ in combo); surcharge=sum(sur for _,_,sur in combo)
            slug='-'.join(o.split()[0].lower() for _,o,_ in combo)
            child={'id':hid('variant:'+p['nr']+':'+key),'parentId':pid[p['nr']],'productNumber':'LF-'+p['nr']+'-'+slug,'stock':999,'active':True,
                   'options':[{'id':opt[(g,o)]} for g,o,_ in combo]}
            if surcharge: child['price']=[money(p['price']+surcharge,p['tax'])]
            variant_payload.append(child)
    if p['xs']=='extras':
        xs_payload.append({'id':hid('xs:'+p['nr']+':extras'),'productId':pid[p['nr']],'name':'Extras','type':'productList','active':True,'position':0,'sortBy':'name','sortDirection':'ASC','limit':24,'assignedProducts':[{'id':hid('xsp:'+p['nr']+':'+str(e)),'productId':pid[str(e)],'position':i} for i,(e,_,_) in enumerate(EX)]})
    if p['xs']=='beilagen':
        xs_payload.append({'id':hid('xs:'+p['nr']+':beilagen'),'productId':pid[p['nr']],'name':'Beilagen','type':'productList','active':True,'position':0,'sortBy':'name','sortDirection':'ASC','limit':24,'assignedProducts':[{'id':hid('xsp:'+p['nr']+':'+str(e)),'productId':pid[str(e)],'position':i} for i,(e,_,_,_) in enumerate(SIDES)]})

# cleanup of earlier runs: no "Beilagen" cross-sellings, no double diet flag on vegan products
xs_delete=[{'id':hid('xs:'+p['nr']+':beilagen')} for p in P if p['cat'] in ('fleisch','fisch')]
prop_delete=[{'productId':pid[p['nr']],'optionId':opt[('Vegetarisch','Ja')]} for p in P if p['vegan']]
# the former 'Küche' property group (Italienisch/Deutsch) makes no sense for a single restaurant: drop it incl. options and product assignments
group_delete=[{'id':hid('pg:Küche')}]
# --- footer navigation: root (folder) -> columns (folder) -> links (link categories).
# The storefront maps footer level 1 to columns and level 2 to links (seoUrl = externalLink / category url).
FOOTER=[
    ('Speisekarte',[('Pizza','category','pizza'),('Nudeln','category','nudeln'),('Fleischgerichte','category','fleisch'),('Getränke','category','getraenke')]),
    ('Service',[('Kontakt','external','/kontakt'),('Zahlung und Versand','external','/zahlung-und-versand'),('Mein Konto','external','/konto'),('Merkliste','external','/merkliste')]),
    ('Rechtliches',[('Impressum','external','/impressum'),('Datenschutz','external','/datenschutz'),('AGB','external','/agb')]),
]
FOOTER_ROOT=hid('category:footer')
footer_payload=[{'id':FOOTER_ROOT,'name':'Footer','type':'folder','active':True,'visible':True,'productAssignmentType':'product'}]
prev_col=None
for col,links in FOOTER:
    cid=hid('category:footer:'+col)
    c={'id':cid,'parentId':FOOTER_ROOT,'name':col,'type':'folder','active':True,'visible':True,'productAssignmentType':'product'}
    if prev_col: c['afterCategoryId']=prev_col
    prev_col=cid; footer_payload.append(c); prev_link=None
    for name,kind,target in links:
        lid=hid('category:footer:'+col+':'+name)
        l={'id':lid,'parentId':cid,'name':name,'type':'link','active':True,'visible':True,'productAssignmentType':'product','linkNewTab':False}
        if kind=='category': l['linkType']='category'; l['internalLink']=cat_id[target]; l['externalLink']=None
        else: l['linkType']='external'; l['externalLink']=target; l['internalLink']=None
        if prev_link: l['afterCategoryId']=prev_link
        prev_link=lid; footer_payload.append(l)
sc_payload=[{'id':SC_ID,'footerCategoryId':FOOTER_ROOT}]

ops=[{'action':'upsert','entity':'property_group','payload':pg_payload},{'action':'upsert','entity':'category','payload':cat_payload},{'action':'upsert','entity':'product','payload':prod_payload},{'action':'upsert','entity':'product','payload':variant_payload},{'action':'upsert','entity':'product_cross_selling','payload':xs_payload},{'action':'delete','entity':'product_cross_selling','payload':xs_delete},{'action':'delete','entity':'product_property','payload':prop_delete},{'action':'delete','entity':'property_group','payload':group_delete},{'action':'upsert','entity':'category','payload':footer_payload},{'action':'upsert','entity':'sales_channel','payload':sc_payload}]
if '--dry' in sys.argv: print(json.dumps([x for x in prod_payload if x['productNumber']=='LF-123'][0]['configuratorSettings'][:2],ensure_ascii=False)); print(json.dumps(variant_payload[-1],ensure_ascii=False)); print(len(prod_payload),'products',len(variant_payload),'variants',len(xs_payload),'cross-sellings',len(xs_delete),'xs deletes',len(prop_delete),'prop deletes'); sys.exit()
s,r=req('/api/_action/sync',ops,token=tok,headers={'fail-on-error':'true'})
print('sync',s); 
if s!=200: print(str(r)[:3000]); sys.exit(1)
print('written:',{k:len(v.get('result',[])) if isinstance(v,dict) else v for k,v in (r.items() if isinstance(r,dict) else enumerate(r))} if r else r)
print(len(prod_payload),'products',len(variant_payload),'variants',len(xs_payload),'cross-sellings',len(cat_payload),'categories',len(pg_payload),'property groups',len(footer_payload),'footer categories')
json.dump({'cat_id':cat_id,'pid':pid,'sc':SC_ID},open('/tmp/seed-ids.json','w'))
