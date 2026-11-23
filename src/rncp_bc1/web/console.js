'use strict';
(() => {
  let token = '', offset = 0, selected = null, session = 0;
  const el = id => document.getElementById(id);
  const number = new Intl.NumberFormat('fr-FR', {maximumFractionDigits: 4});
  const status = text => { el('status').textContent = text; };
  async function request(path, method = 'GET') {
    const activeSession = session;
    const response = await fetch(path, {method, headers: {Authorization: `Bearer ${token}`}, cache: 'no-store', credentials: 'omit'});
    const body = await response.json();
    if (activeSession !== session) throw new Error('Consultation interrompue. Reconnectez-vous.');
    if (!response.ok) throw new Error(response.status === 401 ? 'Jeton invalide ou expiré. Vérifiez votre accès.' : response.status === 403 ? 'Le rôle analyste est requis pour cette action.' : response.status === 429 ? 'Quota atteint. Réessayez à la minute suivante.' : 'Service indisponible ou réponse refusée. Réessayez et consultez les journaux de démonstration.');
    return body;
  }
  function cell(row, value) { const td = document.createElement('td'); td.textContent = value; row.append(td); return td; }
  async function load() {
    el('load').disabled = true; status('Chargement des alertes…');
    try {
      const result = await request(`/v1/alerts?limit=20&offset=${offset}`); el('rows').replaceChildren();
      for (const item of result.items) {
        const tr = document.createElement('tr'); cell(tr, item.transaction_id.slice(0, 12)); cell(tr, item.type); cell(tr, item.amount); cell(tr, number.format(item.score));
        const button = document.createElement('button'); button.type = 'button'; button.textContent = 'Consulter'; button.setAttribute('aria-label', `Consulter l’alerte ${item.transaction_id.slice(0, 12)}`); button.addEventListener('click', () => show(item.transaction_id)); cell(tr, '').append(button); el('rows').append(tr);
      }
      if (!result.items.length) { const tr = document.createElement('tr'); const td = cell(tr, 'Aucune alerte disponible pour cette page.'); td.colSpan = 5; el('rows').append(tr); }
      el('previous').disabled = offset === 0; el('next').disabled = result.items.length < 20 || offset >= 10000; el('page').textContent = `Page ${offset / 20 + 1}`; status(`${result.items.length} alertes chargées. Les données sont synthétiques.`);
    } catch (error) { status(error.message); } finally { el('load').disabled = false; }
  }
  async function show(id) {
    try {
      const item = await request(`/v1/alerts/${id}`); selected = id; el('facts').replaceChildren(); el('draft').replaceChildren();
      for (const [label, value] of [['Référence complète', id], ['Type', item.type], ['Montant sans devise précisée', item.amount], ['Score non calibré', number.format(item.score)], ['Seuil', number.format(item.threshold)], ['Version du modèle', item.model_version]]) { const dt = document.createElement('dt'), dd = document.createElement('dd'); dt.textContent = label; dd.textContent = value; el('facts').append(dt, dd); }
      el('details').hidden = false; el('details-title').focus(); status('Détail de l’alerte chargé.');
    } catch (error) { status(error.message); }
  }
  el('connection').addEventListener('submit', event => { event.preventDefault(); session += 1; el('rows').replaceChildren(); el('details').hidden = true; token = el('token').value.trim(); el('token').value = ''; offset = 0; load(); });
  el('disconnect').addEventListener('click', () => { session += 1; token = ''; el('facts').replaceChildren(); el('draft').replaceChildren(); selected = null; el('token').value = ''; el('details').hidden = true; el('rows').replaceChildren(); el('next').disabled = el('previous').disabled = true; status('Jeton et données effacés.'); el('token').focus(); });
  el('previous').addEventListener('click', () => { offset = Math.max(0, offset - 20); load(); });
  el('next').addEventListener('click', () => { offset += 20; load(); });
  el('generate').addEventListener('click', async () => {
    if (!selected) return; el('generate').disabled = true; status('Génération du brouillon… Cette opération peut prendre plusieurs minutes.');
    try {
      const result = await request(`/v1/alerts/${selected}/explanations`, 'POST'); el('draft').replaceChildren();
      for (const [title, text] of [['Explication pour le conseiller', result.output.analyst_explanation], [result.output.client_email.subject, result.output.client_email.body]]) { const h = document.createElement('h3'), p = document.createElement('p'); h.textContent = title; p.textContent = text; el('draft').append(h, p); }
      status('Brouillon généré et enregistré. Relisez-le avant tout usage. Aucun envoi effectué.');
    } catch (error) { status(error.message); } finally { el('generate').disabled = false; }
  });
})();
