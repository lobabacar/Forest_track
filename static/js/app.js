const searchInput     = document.getElementById('searchInput');
const filtreStatut    = document.getElementById('filtreStatut');
const filtreCategorie = document.getElementById('filtreCategorie');
const resetBtn        = document.getElementById('resetFiltres');
const noResult        = document.getElementById('noResult');

function filtrerTableau() {
  if (!searchInput) return;
  const search    = searchInput.value.toLowerCase();
  const statut    = filtreStatut.value;
  const categorie = filtreCategorie.value;
  const rows      = document.querySelectorAll('.materiel-row');
  let visible     = 0;
  rows.forEach(row => {
    const match = (!search   || row.dataset.nom.includes(search) || row.dataset.code.includes(search))
               && (!statut   || row.dataset.statut    === statut)
               && (!categorie|| row.dataset.categorie === categorie);
    row.style.display = match ? '' : 'none';
    if (match) visible++;
  });
  if (noResult) noResult.classList.toggle('d-none', visible > 0);
}

if (searchInput) {
  searchInput.addEventListener('input', filtrerTableau);
  filtreStatut.addEventListener('change', filtrerTableau);
  filtreCategorie.addEventListener('change', filtrerTableau);
  resetBtn.addEventListener('click', () => {
    searchInput.value = filtreStatut.value = filtreCategorie.value = '';
    filtrerTableau();
  });
}

document.querySelectorAll('input[name="code"]').forEach(el => {
  el.addEventListener('input', () => { el.value = el.value.toUpperCase(); });
});

document.querySelectorAll('.alert.alert-success').forEach(alert => {
  setTimeout(() => bootstrap.Alert.getOrCreateInstance(alert)?.close(), 5000);
});

document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => new bootstrap.Tooltip(el));