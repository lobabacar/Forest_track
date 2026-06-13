import os
from dotenv import load_dotenv
load_dotenv()

from app import app, db, Utilisateur, ROLE_ADMIN, ROLE_GERANT, ROLE_OPERATEUR

# ─── Liste des utilisateurs à importer ──────────────────────
# Le nom est généré automatiquement depuis l'email
# Modifiez le rôle selon vos besoins

def nom_depuis_email(email):
    """Génère un nom propre depuis l'email : anne-lyse.thouin → Anne-Lyse Thouin"""
    partie = email.split('@')[0]          # anne-lyse.thouin
    mots   = partie.replace('-', ' ').replace('.', ' ').split()
    return ' '.join(mot.capitalize() for mot in mots)

utilisateurs = [
    # (email, role, mot_de_passe_temporaire)
    ('anne-lyse.thouin@coop-ecologie.com',        ROLE_OPERATEUR, 'BEA2024!'),
    ('anthony.st-jean@coop-ecologie.com',          ROLE_OPERATEUR, 'BEA2024!'),
    ('audrey.lachance@coop-ecologie.com',          ROLE_GERANT,    'BEA2024!'),
    
    ('benjamin.brosseau@coop-ecologie.com',        ROLE_OPERATEUR, 'BEA2024!'),
    ('dominic.desjardins@coop-ecologie.com',       ROLE_OPERATEUR, 'BEA2024!'),
    ('emilie.reny-nolin@coop-ecologie.com',        ROLE_OPERATEUR, 'BEA2024!'),
    ('erica.poulin@coop-ecologie.com',             ROLE_OPERATEUR, 'BEA2024!'),
    ('genevieve.chartier@coop-ecologie.com',       ROLE_OPERATEUR, 'BEA2024!'),
    ('helene.boulianne@coop-ecologie.com',         ROLE_OPERATEUR, 'BEA2024!'),
    ('jeremie.caron@coop-ecologie.com',            ROLE_OPERATEUR, 'BEA2024!'),
    ('karine.gagnon@coop-ecologie.com',            ROLE_OPERATEUR, 'BEA2024!'),
    ('laurence.vincent-gaboury@coop-ecologie.com', ROLE_OPERATEUR, 'BEA2024!'),
    ('laury.parent@coop-ecologie.com',             ROLE_OPERATEUR, 'BEA2024!'),
    ('loic.st-onge@coop-ecologie.com',             ROLE_OPERATEUR, 'BEA2024!'),
    ('maina.berger@coop-ecologie.com',             ROLE_OPERATEUR, 'BEA2024!'),
    ('marc-aurele.vallee@coop-ecologie.com',       ROLE_OPERATEUR, 'BEA2024!'),
    ('maxime.gaillard@coop-ecologie.com',          ROLE_OPERATEUR, 'BEA2024!'),
    ('pascale.forget@coop-ecologie.com',           ROLE_OPERATEUR, 'BEA2024!'),
    ('sophie.pouliot@coop-ecologie.com',           ROLE_OPERATEUR, 'BEA2024!'),
    ('stephanie.langevin@coop-ecologie.com',       ROLE_GERANT,    'BEA2024!'),
    ('tommy.brasseur@coop-ecologie.com',           ROLE_OPERATEUR, 'BEA2024!'),
    ('vanessa.duclos@coop-ecologie.com',           ROLE_OPERATEUR, 'BEA2024!'),
    ('veronique.beaulieu@coop-ecologie.com',       ROLE_OPERATEUR, 'BEA2024!'),
    ('william.hamel@coop-ecologie.com',            ROLE_OPERATEUR, 'BEA2024!'),
    ('zakary.nicol@coop-ecologie.com',             ROLE_OPERATEUR, 'BEA2024!'),
    ('zoe.st-onge@coop-ecologie.com',              ROLE_OPERATEUR, 'BEA2024!'),
]

def importer():
    with app.app_context():
        crees   = 0
        ignores = 0
        for email, role, mdp in utilisateurs:
            # Vérifier si l'utilisateur existe déjà
            existant = Utilisateur.query.filter_by(email=email).first()
            if existant:
                print(f'⏭  Ignoré (existe déjà) : {email}')
                ignores += 1
                continue
            u = Utilisateur(
                nom   = nom_depuis_email(email),
                email = email,
                role  = role,
                actif = True
            )
            u.set_password(mdp)
            db.session.add(u)
            crees += 1
            print(f'✅ Créé : {u.nom} ({role})')

        db.session.commit()
        print(f'\n─── Résumé ───────────────────────')
        print(f'✅ {crees} utilisateurs créés')
        print(f'⏭  {ignores} ignorés (existaient déjà)')
        print(f'──────────────────────────────────')
        print(f'Mot de passe temporaire : BEA2024!')
        print(f'Chaque utilisateur devra le changer dans Mon Profil.')

if __name__ == '__main__':
    importer()