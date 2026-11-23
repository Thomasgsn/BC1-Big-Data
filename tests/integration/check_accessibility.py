"""Consultation réelle au clavier, données réelles et audit axe-core hors réseau public."""
import hashlib
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

base=os.environ['BC1_API_BASE_URL'];token=os.environ['API_TOKEN_READER']
out=Path('/evidence');out.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch()
    # Certificat privé de laboratoire : la validation du certificat et de la CA est
    # testée séparément par check_integrated_security.py ; ce test vise le DOM.
    context=browser.new_context(ignore_https_errors=True,viewport={'width':1280,'height':900})
    page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(base,wait_until='networkidle')
    assert page.locator('html').get_attribute('lang')=='fr'
    page.keyboard.press('Tab');assert page.locator(':focus').inner_text()=='Aller au contenu'
    page.keyboard.press('Enter');assert page.locator(':focus').get_attribute('id')=='main'
    page.get_by_label('Jeton de consultation ou d’analyse').fill(token)
    page.get_by_role('button',name='Afficher les alertes').focus();page.keyboard.press('Enter')
    page.get_by_role('button',name='Consulter l’alerte',exact=False).first.wait_for(timeout=20000)
    assert page.locator('#rows tr').count()==20
    assert page.locator('#token').input_value()==''
    assert token not in page.url and token not in page.locator('body').inner_text()
    page.get_by_role('button',name='Consulter l’alerte',exact=False).first.focus();page.keyboard.press('Enter')
    page.locator('#details:not([hidden])').wait_for();assert page.locator(':focus').get_attribute('id')=='details-title'
    # Exécution par le débogueur de test : conserver la CSP stricte de l'application.
    page.evaluate(Path('/opt/axe.min.js').read_text())
    result=page.evaluate('async () => await axe.run(document, {runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21aa"]}})')
    violations=[{'id':x['id'],'impact':x.get('impact'),'description':x['description'],'targets':[n['target'] for n in x['nodes']]} for x in result['violations']]
    assert not violations,json.dumps(violations)
    page.screenshot(path=str(out/'consultation-desktop.png'),full_page=True)
    page.get_by_role('button',name='Effacer le jeton').click();assert page.locator('#rows tr').count()==0;assert page.locator('#token').input_value()==''
    assert page.evaluate('localStorage.length')==0 and page.evaluate('sessionStorage.length')==0
    page.get_by_label('Jeton de consultation ou d’analyse').fill('explicit-invalid-test-token-that-is-long-enough')
    page.get_by_role('button',name='Afficher les alertes').click();expect(page.locator('#status')).to_contain_text('Jeton invalide')
    page.set_viewport_size({'width':390,'height':844});page.get_by_label('Jeton de consultation ou d’analyse').fill(token);page.get_by_role('button',name='Afficher les alertes').click();page.get_by_role('button',name='Consulter l’alerte',exact=False).first.wait_for(timeout=15000)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Page overflow outside scrollable table'
    page.screenshot(path=str(out/'consultation-mobile.png'),full_page=True)
    assert not errors,errors
    report={'event':'accessible_consultation_verified','keyboard_skip_link':True,'keyboard_load_and_detail':True,'focus_on_detail_heading':True,'actual_alert_rows':20,'axe_version':result['testEngine']['version'],'axe_violations':violations,'axe_incomplete':len(result['incomplete']),'invalid_token_error_shown':True,'no_browser_token_storage':True,'no_global_mobile_overflow':True,'console_errors':errors,'screenshots':{},'certificate_scope':'Browser ignores private certificate; actual TLS CA/hostname checks are separate and passed','limits':'Automated checks and keyboard paths only; no claim of complete WCAG certification or human screen-reader audit'}
    for f in ['consultation-desktop.png','consultation-mobile.png']:report['screenshots'][f]=hashlib.sha256((out/f).read_bytes()).hexdigest()
    (out/'accessibility.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report));browser.close()
