import os

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
import qrcode, io, base64
# ─── UTILITAIRE RETARDS ──────────────────────────────────────
def get_emprunts_en_retard():
    """Retourne tous les emprunts actifs dont la date de retour prévue est dépassée."""
    aujourd_hui = datetime.utcnow().date()
    return Emprunt.query.filter(
        Emprunt.actif == True,
        Emprunt.date_retour_prevue != None,
        Emprunt.date_retour_prevue < aujourd_hui
    ).all()

def nb_retards():
    """Nombre d'emprunts en retard — injecté dans tous les templates."""
    return len(get_emprunts_en_retard())


load_dotenv()

app = Flask(__name__)
#app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-fallback-key-insecure') # decoche en developpement
#app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///forestier.db')   # decovhe en developpement
#production
db_url = os.getenv('DATABASE_URL', 'sqlite:///forestier.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

app.config['SECRET_KEY']              = os.getenv('SECRET_KEY', 'dev-key-insecure')
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
@app.context_processor
def inject_retards():
    if current_user.is_authenticated:
        return {'nb_retards': nb_retards()}
    return {'nb_retards': 0}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'warning'

ROLE_ADMIN     = 'admin'
ROLE_GERANT    = 'gerant'
ROLE_OPERATEUR = 'operateur'
ROLE_LABELS = {ROLE_ADMIN:'Administrateur', ROLE_GERANT:'Gérant', ROLE_OPERATEUR:'Opérateur'}

# ─── MODÈLES ────────────────────────────────────────────────
class Utilisateur(UserMixin, db.Model):
    id                 = db.Column(db.Integer, primary_key=True)
    nom                = db.Column(db.String(100), nullable=False)
    email              = db.Column(db.String(120), unique=True, nullable=False)
    mot_de_passe       = db.Column(db.String(200), nullable=False)
    role               = db.Column(db.String(20), default=ROLE_OPERATEUR)
    actif              = db.Column(db.Boolean, default=True)
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)
    derniere_connexion = db.Column(db.DateTime)

    def set_password(self, mdp):
        self.mot_de_passe = generate_password_hash(mdp)
    def check_password(self, mdp):
        return check_password_hash(self.mot_de_passe, mdp)
    @property
    def role_label(self):
        return ROLE_LABELS.get(self.role, self.role)
    def peut(self, action):
        perms = {
            ROLE_ADMIN:     ['emprunter','retourner','maintenance','ajouter','modifier','admin'],
            ROLE_GERANT:    ['emprunter','retourner','maintenance','ajouter','modifier'],
            ROLE_OPERATEUR: ['emprunter','retourner'],
        }
        return action in perms.get(self.role, [])

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Utilisateur, int(user_id))

class Materiel(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    code         = db.Column(db.String(20), unique=True, nullable=False)
    nom          = db.Column(db.String(100), nullable=False)
    categorie    = db.Column(db.String(50), nullable=False)
    numero_serie = db.Column(db.String(50))
    description  = db.Column(db.Text)
    emplacement  = db.Column(db.String(100), default='Dépôt principal')
    statut       = db.Column(db.String(20), default='disponible')
    date_achat   = db.Column(db.Date)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    cree_par_id  = db.Column(db.Integer, db.ForeignKey('utilisateur.id'))
    cree_par     = db.relationship('Utilisateur', foreign_keys=[cree_par_id])
    emprunts     = db.relationship('Emprunt', backref='materiel', lazy=True,
                                   order_by='Emprunt.date_emprunt.desc()')
    latitude   = db.Column(db.Float, nullable=True)
    longitude  = db.Column(db.Float, nullable=True)
    dernier_scan = db.Column(db.DateTime, nullable=True)

class Emprunt(db.Model):
    id                 = db.Column(db.Integer, primary_key=True)
    materiel_id        = db.Column(db.Integer, db.ForeignKey('materiel.id'), nullable=False)
    utilisateur_id     = db.Column(db.Integer, db.ForeignKey('utilisateur.id'))
    nom_emprunteur     = db.Column(db.String(100), nullable=False)
    chantier           = db.Column(db.String(100))
    date_emprunt       = db.Column(db.DateTime, default=datetime.utcnow)
    date_retour        = db.Column(db.DateTime)
    date_retour_prevue = db.Column(db.Date)
    notes              = db.Column(db.Text)
    actif              = db.Column(db.Boolean, default=True)
    emprunteur         = db.relationship('Utilisateur', foreign_keys=[utilisateur_id])
    latitude_scan  = db.Column(db.Float, nullable=True)
    longitude_scan = db.Column(db.Float, nullable=True)

class Maintenance(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    materiel_id  = db.Column(db.Integer, db.ForeignKey('materiel.id'), nullable=False)
    description  = db.Column(db.Text, nullable=False)
    date_debut   = db.Column(db.DateTime, default=datetime.utcnow)
    date_fin     = db.Column(db.DateTime)
    technicien   = db.Column(db.String(100))
    cout         = db.Column(db.Float)
    actif        = db.Column(db.Boolean, default=True)
    cree_par_id  = db.Column(db.Integer, db.ForeignKey('utilisateur.id'))
    materiel_ref = db.relationship('Materiel', backref='maintenances')

# ─── DÉCORATEURS ────────────────────────────────────────────
def permission_requise(action):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            if not current_user.peut(action):
                flash("Vous n'avez pas la permission d'effectuer cette action.", 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def admin_requis(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != ROLE_ADMIN:
            flash('Accès réservé aux administrateurs.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ─── QR CODE ────────────────────────────────────────────────
def generer_qr(code, base_url='http://localhost:5000'):
    qr = qrcode.QRCode(version=1, box_size=8, border=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(f"{base_url}/materiel/{code}")
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()

# ─── AUTH ────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        user  = Utilisateur.query.filter_by(email=email).first()
        if user and user.actif and user.check_password(request.form['mot_de_passe']):
            user.derniere_connexion = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=request.form.get('remember') == 'on')
            flash(f'Bienvenue, {user.nom} !', 'success')
            return redirect(request.args.get('next') or url_for('index'))
        flash('Email ou mot de passe incorrect.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('login'))

@app.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'infos':
            current_user.nom = request.form['nom']
            db.session.commit()
            flash('Profil mis à jour.', 'success')
        elif action == 'mdp':
            ancien, nouveau, confirm = (request.form['ancien_mdp'],
                                        request.form['nouveau_mdp'],
                                        request.form['confirmer_mdp'])
            if not current_user.check_password(ancien):
                flash('Ancien mot de passe incorrect.', 'danger')
            elif nouveau != confirm:
                flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
            elif len(nouveau) < 6:
                flash('Minimum 6 caractères requis.', 'danger')
            else:
                current_user.set_password(nouveau)
                db.session.commit()
                flash('Mot de passe modifié.', 'success')
    mes_emprunts = Emprunt.query.filter_by(utilisateur_id=current_user.id)\
                                .order_by(Emprunt.date_emprunt.desc()).limit(10).all()
    return render_template('profil.html', mes_emprunts=mes_emprunts)

# ─── ADMIN UTILISATEURS ─────────────────────────────────────
@app.route('/admin/utilisateurs')
@admin_requis
def admin_utilisateurs():
    users = Utilisateur.query.order_by(Utilisateur.created_at.desc()).all()
    return render_template('admin_utilisateurs.html', users=users, roles=ROLE_LABELS)

@app.route('/admin/utilisateurs/nouveau', methods=['GET', 'POST'])
@admin_requis
def admin_nouveau_utilisateur():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        if Utilisateur.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return redirect(url_for('admin_nouveau_utilisateur'))
        u = Utilisateur(nom=request.form['nom'], email=email,
                        role=request.form['role'], actif=True)
        u.set_password(request.form['mot_de_passe'])
        db.session.add(u)
        db.session.commit()
        flash(f'Utilisateur {u.nom} créé.', 'success')
        return redirect(url_for('admin_utilisateurs'))
    return render_template('admin_form_utilisateur.html', user=None,
                           roles=ROLE_LABELS, titre='Nouvel utilisateur')

@app.route('/admin/utilisateurs/<int:uid>/modifier', methods=['GET', 'POST'])
@admin_requis
def admin_modifier_utilisateur(uid):
    u = db.session.get(Utilisateur, uid)
    if not u:
        flash('Utilisateur introuvable.', 'danger')
        return redirect(url_for('admin_utilisateurs'))
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'infos':
            u.nom   = request.form['nom']
            u.email = request.form['email'].strip().lower()
            u.role  = request.form['role']
            u.actif = request.form.get('actif') == 'on'
            db.session.commit()
            flash('Utilisateur modifié.', 'success')
        elif action == 'mdp':
            nouveau = request.form['nouveau_mdp']
            if len(nouveau) < 6:
                flash('Minimum 6 caractères.', 'danger')
            else:
                u.set_password(nouveau)
                db.session.commit()
                flash('Mot de passe réinitialisé.', 'success')
        return redirect(url_for('admin_utilisateurs'))
    return render_template('admin_form_utilisateur.html', user=u,
                           roles=ROLE_LABELS, titre="Modifier l'utilisateur")

@app.route('/admin/utilisateurs/<int:uid>/supprimer', methods=['POST'])
@admin_requis
def admin_supprimer_utilisateur(uid):
    u = db.session.get(Utilisateur, uid)
    if u and u.id != current_user.id:
        db.session.delete(u)
        db.session.commit()
        flash('Utilisateur supprimé.', 'success')
    else:
        flash('Impossible de supprimer ce compte.', 'danger')
    return redirect(url_for('admin_utilisateurs'))

# ─── MATÉRIELS ───────────────────────────────────────────────
@app.route('/')
@login_required
def index():
    materiels      = Materiel.query.all()
    total          = len(materiels)
    disponibles    = sum(1 for m in materiels if m.statut == 'disponible')
    en_utilisation = sum(1 for m in materiels if m.statut == 'utilisation')
    en_maintenance = sum(1 for m in materiels if m.statut == 'maintenance')
    return render_template('index.html', materiels=materiels, total=total,
                           disponibles=disponibles, en_utilisation=en_utilisation,
                           en_maintenance=en_maintenance)

@app.route('/materiel/nouveau', methods=['GET', 'POST'])
@permission_requise('ajouter')
def nouveau_materiel():
    if request.method == 'POST':
        if Materiel.query.filter_by(code=request.form['code'].upper()).first():
            flash('Ce code existe déjà.', 'danger')
            return redirect(url_for('nouveau_materiel'))
        m = Materiel(
            code         = request.form['code'].upper(),
            nom          = request.form['nom'],
            categorie    = request.form['categorie'],
            numero_serie = request.form.get('numero_serie', ''),
            description  = request.form.get('description', ''),
            emplacement  = request.form.get('emplacement', 'Dépôt principal'),
            cree_par_id  = current_user.id,
            date_achat   = datetime.strptime(request.form['date_achat'], '%Y-%m-%d').date()
                           if request.form.get('date_achat') else None
        )
        db.session.add(m)
        db.session.commit()
        flash(f'Matériel "{m.nom}" ajouté !', 'success')
        return redirect(url_for('fiche_materiel', code=m.code))
    return render_template('nouveau_materiel.html')

@app.route('/materiel/<code>')
@login_required
def fiche_materiel(code):
    m = Materiel.query.filter_by(code=code.upper()).first_or_404()
    qr_b64 = generer_qr(m.code, request.host_url.rstrip('/'))
    emprunt_actif      = Emprunt.query.filter_by(materiel_id=m.id, actif=True).first()
    maintenance_active = Maintenance.query.filter_by(materiel_id=m.id, actif=True).first()
    return render_template('fiche.html', m=m, qr_b64=qr_b64,
                           emprunt_actif=emprunt_actif,
                           maintenance_active=maintenance_active,
                           aujourd_hui=datetime.utcnow().date())

# @app.route('/materiel/<code>/emprunter', methods=['POST'])
# @permission_requise('emprunter')
# def emprunter(code):
#     m = Materiel.query.filter_by(code=code.upper()).first_or_404()
#     if m.statut != 'disponible':
#         flash("Ce matériel n'est pas disponible.", 'warning')
#         return redirect(url_for('fiche_materiel', code=code))
#     e = Emprunt(
#         materiel_id        = m.id,
#         utilisateur_id     = current_user.id,
#         nom_emprunteur     = current_user.nom,
#         chantier           = request.form.get('chantier', ''),
#         notes              = request.form.get('notes', ''),
#         date_retour_prevue = datetime.strptime(request.form['date_retour_prevue'], '%Y-%m-%d').date()
#                              if request.form.get('date_retour_prevue') else None
#     )
#     m.statut      = 'utilisation'
#     m.emplacement = request.form.get('chantier', m.emplacement)
#     db.session.add(e)
#     db.session.commit()
#     flash(f'Emprunt enregistré pour {e.nom_emprunteur}.', 'success')
#     return redirect(url_for('fiche_materiel', code=code))
@app.route('/materiel/<code>/emprunter', methods=['POST'])
@permission_requise('emprunter')
def emprunter(code):
    m = Materiel.query.filter_by(code=code.upper()).first_or_404()
    if m.statut != 'disponible':
        flash("Ce matériel n'est pas disponible.", 'warning')
        return redirect(url_for('fiche_materiel', code=code))
    
    # Récupérer les coordonnées GPS si fournies
    lat = request.form.get('latitude')
    lon = request.form.get('longitude')
    
    e = Emprunt(
        materiel_id        = m.id,
        utilisateur_id     = current_user.id,
        nom_emprunteur     = current_user.nom,
        chantier           = request.form.get('chantier', ''),
        notes              = request.form.get('notes', ''),
        latitude_scan      = float(lat) if lat else None,
        longitude_scan     = float(lon) if lon else None,
        date_retour_prevue = datetime.strptime(request.form['date_retour_prevue'], '%Y-%m-%d').date()
                             if request.form.get('date_retour_prevue') else None
    )
    m.statut      = 'utilisation'
    m.emplacement = request.form.get('chantier', m.emplacement)
    if lat and lon:
        m.latitude    = float(lat)
        m.longitude   = float(lon)
        m.dernier_scan = datetime.utcnow()
    db.session.add(e)
    db.session.commit()
    flash(f'Emprunt enregistré pour {e.nom_emprunteur}.', 'success')
    return redirect(url_for('fiche_materiel', code=code))

@app.route('/materiel/<code>/retourner', methods=['POST'])
@permission_requise('retourner')
def retourner(code):
    m = Materiel.query.filter_by(code=code.upper()).first_or_404()
    e = Emprunt.query.filter_by(materiel_id=m.id, actif=True).first()
    if e:
        e.actif = False
        e.date_retour = datetime.utcnow()
    m.statut      = 'disponible'
    m.emplacement = 'Dépôt principal'
    db.session.commit()
    flash('Matériel retourné avec succès.', 'success')
    return redirect(url_for('fiche_materiel', code=code))

@app.route('/materiel/<code>/maintenance', methods=['POST'])
@permission_requise('maintenance')
def mise_en_maintenance(code):
    m = Materiel.query.filter_by(code=code.upper()).first_or_404()
    maint = Maintenance(
        materiel_id = m.id,
        description = request.form['description'],
        technicien  = request.form.get('technicien', ''),
        cout        = float(request.form['cout']) if request.form.get('cout') else None,
        cree_par_id = current_user.id
    )
    m.statut = 'maintenance'
    db.session.add(maint)
    db.session.commit()
    flash('Matériel mis en maintenance.', 'warning')
    return redirect(url_for('fiche_materiel', code=code))

@app.route('/materiel/<code>/fin_maintenance', methods=['POST'])
@permission_requise('maintenance')
def fin_maintenance(code):
    m = Materiel.query.filter_by(code=code.upper()).first_or_404()
    maint = Maintenance.query.filter_by(materiel_id=m.id, actif=True).first()
    if maint:
        maint.actif    = False
        maint.date_fin = datetime.utcnow()
    m.statut      = 'disponible'
    m.emplacement = 'Dépôt principal'
    db.session.commit()
    flash('Maintenance terminée, matériel disponible.', 'success')
    return redirect(url_for('fiche_materiel', code=code))

@app.route('/materiel/<code>/qr')
@login_required
def qr_image(code):
    from flask import send_file
    m = Materiel.query.filter_by(code=code.upper()).first_or_404()
    url = f"{request.host_url.rstrip('/')}/materiel/{m.code}"
    qr  = qrcode.QRCode(version=1, box_size=10, border=4,
                        error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png',
                     download_name=f'QR_{m.code}.png', as_attachment=True)

@app.route('/api/materiels')
@login_required
def api_materiels():
    return jsonify([{'id':m.id,'code':m.code,'nom':m.nom,
                     'categorie':m.categorie,'statut':m.statut,
                     'emplacement':m.emplacement}
                    for m in Materiel.query.all()])
# ─── visualisation sur la carte ───────────────────────────────────────

@app.route('/carte')
@login_required
def carte():
    return render_template('carte.html')

@app.route('/api/carte/materiels')
@login_required
def api_carte_materiels():
    """Retourne les matériels avec coordonnées pour OpenLayers."""
    materiels = Materiel.query.all()
    data = []
    for m in materiels:
        emprunt_actif = Emprunt.query.filter_by(materiel_id=m.id, actif=True).first()
        data.append({
            'id':           m.id,
            'code':         m.code,
            'nom':          m.nom,
            'categorie':    m.categorie,
            'statut':       m.statut,
            'emplacement':  m.emplacement,
            'latitude':     m.latitude,
            'longitude':    m.longitude,
            'dernier_scan': m.dernier_scan.strftime('%d/%m/%Y %H:%M') if m.dernier_scan else None,
            'emprunteur':   emprunt_actif.nom_emprunteur if emprunt_actif else None,
            'chantier':     emprunt_actif.chantier if emprunt_actif else None,
            'url_fiche':    url_for('fiche_materiel', code=m.code),
        })
    return jsonify(data)

@app.route('/api/materiel/<code>/localisation', methods=['POST'])
@login_required
def maj_localisation(code):
    """Met à jour les coordonnées GPS au moment du scan."""
    m = Materiel.query.filter_by(code=code.upper()).first_or_404()
    data = request.get_json()
    if data and data.get('latitude') and data.get('longitude'):
        m.latitude    = data['latitude']
        m.longitude   = data['longitude']
        m.dernier_scan = datetime.utcnow()
        db.session.commit()
        return jsonify({'ok': True})
    return jsonify({'ok': False}), 400
# ─── ALERTES RETARDS ─────────────────────────────────────────
@app.route('/alertes')
@login_required
def alertes():
    emprunts_retard = get_emprunts_en_retard()
    aujourd_hui = datetime.utcnow().date()
    # Calcul du nombre de jours de retard pour chaque emprunt
    retards = []
    for e in emprunts_retard:
        jours = (aujourd_hui - e.date_retour_prevue).days
        retards.append({'emprunt': e, 'jours': jours})
    # Trier du plus ancien au plus récent
    retards.sort(key=lambda x: x['jours'], reverse=True)
    return render_template('alertes.html', retards=retards, aujourd_hui=aujourd_hui)

@app.route('/api/retards')
@login_required
def api_retards():
    aujourd_hui = datetime.utcnow().date()
    emprunts = get_emprunts_en_retard()
    return jsonify([{
        'materiel_code': e.materiel.code,
        'materiel_nom':  e.materiel.nom,
        'emprunteur':    e.nom_emprunteur,
        'chantier':      e.chantier,
        'date_prevue':   e.date_retour_prevue.strftime('%d/%m/%Y'),
        'jours_retard':  (aujourd_hui - e.date_retour_prevue).days,
        'url_fiche':     url_for('fiche_materiel', code=e.materiel.code),
    } for e in emprunts])

# ─── INIT DÉMO ───────────────────────────────────────────────
def init_demo():
    if Utilisateur.query.count() > 0:
        return
    admin  = Utilisateur(nom='Babacar Toure lo', email='btlo@foresttrack.ca', role=ROLE_ADMIN, actif=True)
    gerant = Utilisateur(nom='Marietou Mbengue',   email='mmbengue@foresttrack.ca', role=ROLE_GERANT, actif=True)
    op1    = Utilisateur(nom='Omar Thiam',  email='othiam@foresttrack.ca', role=ROLE_OPERATEUR, actif=True)
    op2    = Utilisateur(nom='Amina Mbengue',     email='ambengue@foresttrack.ca',   role=ROLE_OPERATEUR, actif=True)
    admin.set_password('admin123')
    gerant.set_password('gerant123')
    op1.set_password('oper123')
    op2.set_password('oper123')
    db.session.add_all([admin, gerant, op1, op2])
    db.session.flush()
    # demo = [
    #     Materiel(code='TRON-001', nom='Tronçonneuse Stihl MS 500i', categorie='Abattage',
    #              numero_serie='SHL-2024-001', cree_par_id=admin.id,
    #              description='Tronçonneuse professionnelle 79cc, guide 63cm'),
    #     Materiel(code='DBSC-002', nom='Débusqueuse CAT 525D', categorie='Transport',
    #              numero_serie='CAT-2022-044', emplacement='Chantier Nord',
    #              statut='utilisation', cree_par_id=admin.id,
    #              description='Débusqueuse à câble 140kW'),
    #     Materiel(code='ABAT-003', nom='Abatteuse Ponsse Ergo', categorie='Abattage',
    #              numero_serie='PON-2023-017', emplacement='Atelier',
    #              statut='maintenance', cree_par_id=admin.id,
    #              description='Abatteuse 8 roues, tête H7'),
    #     Materiel(code='TRON-004', nom='Tronçonneuse Husqvarna 572XP', categorie='Abattage',
    #              numero_serie='HSQ-2023-089', cree_par_id=gerant.id,
    #              description='70.6cc, guide 50cm, frein de chaîne'),
    #     Materiel(code='MOTO-005', nom='Moto-manuel Vermeer SC852', categorie='Broyage',
    #              numero_serie='VRM-2021-033', emplacement='Dépôt secondaire',
    #              cree_par_id=gerant.id, description='Broyeur de souches automoteur 99cv'),
    # ]
    demo = [
    Materiel(code='TRON-001', nom='Tronçonneuse Stihl MS 500i', categorie='Abattage',
             numero_serie='SHL-2024-001', cree_par_id=admin.id,
             description='Tronçonneuse professionnelle 79cc, guide 63cm',
             latitude=47.3215, longitude=-71.4782,           # ← Dépôt principal
             dernier_scan=datetime.utcnow()),

    Materiel(code='DBSC-002', nom='Débusqueuse CAT 525D', categorie='Transport',
             numero_serie='CAT-2022-044', emplacement='Chantier Nord',
             statut='utilisation', cree_par_id=admin.id,
             description='Débusqueuse à câble 140kW',
             latitude=47.5840, longitude=-71.2103,           # ← Chantier Nord
             dernier_scan=datetime.utcnow()),

    Materiel(code='ABAT-003', nom='Abatteuse Ponsse Ergo', categorie='Abattage',
             numero_serie='PON-2023-017', emplacement='Atelier',
             statut='maintenance', cree_par_id=admin.id,
             description='Abatteuse 8 roues, tête H7',
             latitude=47.3350, longitude=-71.5100,           # ← Atelier
             dernier_scan=datetime.utcnow()),

    Materiel(code='TRON-004', nom='Tronçonneuse Husqvarna 572XP', categorie='Abattage',
             numero_serie='HSQ-2023-089', cree_par_id=gerant.id,
             description='70.6cc, guide 50cm, frein de chaîne',
             latitude=47.3180, longitude=-71.4850,           # ← Dépôt principal
             dernier_scan=datetime.utcnow()),

    Materiel(code='MOTO-005', nom='Moto-manuel Vermeer SC852', categorie='Broyage',
             numero_serie='VRM-2021-033', emplacement='Dépôt secondaire',
             cree_par_id=gerant.id,
             description='Broyeur de souches automoteur 99cv',
             latitude=47.2990, longitude=-71.3920,           # ← Dépôt secondaire
             dernier_scan=datetime.utcnow()),
]
    db.session.add_all(demo)
    db.session.flush()
    db.session.add(Emprunt(materiel_id=demo[1].id, utilisateur_id=op1.id,
                           nom_emprunteur=op1.nom, chantier='Chantier Nord', actif=True))
    db.session.add(Maintenance(materiel_id=demo[2].id, cree_par_id=gerant.id,
                               description='Révision 500h - changement filtres et courroies',
                               technicien='Marc Leblanc', actif=True))
    db.session.commit()

with app.app_context():
    db.create_all()
    init_demo()

if __name__ == '__main__':
    app.run(debug=True)


# ## `requirements.txt`
# ```
# Flask==3.0.3
# Flask-SQLAlchemy==3.1.1
# Flask-Login==0.6.3
# qrcode[pil]==7.4.2
# Pillow==10.4.0