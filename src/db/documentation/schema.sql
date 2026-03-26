-- =============================================================================
-- SCHEMA DE LA BASE DE DONNEES - TRAIL BETTING
--
-- Description : Script de création complet de la base de données PostgreSQL
--               pour l'application de pronostics trail running.
--               Contient les tables, index, contraintes métier, triggers,
--               fonctions utilitaires et données initiales (seed).
--
-- Usage       : A exécuter une seule fois via le SQL Editor de Supabase,
--               ou via psql : psql -h <host> -U <user> -d <db> -f schema.sql
--
-- Auteur      : Trail Betting App
-- Version     : 1.0.0
-- =============================================================================


-- =============================================================================
-- EXTENSIONS
-- =============================================================================

-- Activation de l'extension UUID pour la génération automatique des clés primaires
-- Doit être exécutée sur le schéma public (restriction Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


-- =============================================================================
-- SCHEMA
-- =============================================================================

-- Création du schéma applicatif et définition comme schéma de travail
CREATE SCHEMA IF NOT EXISTS trail_betting_db;

SET search_path TO trail_betting_db;


-- =============================================================================
-- SUPPRESSION DES TABLES EXISTANTES (ordre inverse des dépendances FK)
-- A décommenter uniquement pour une réinitialisation complète
-- =============================================================================

-- DROP TABLE IF EXISTS paris CASCADE;
-- DROP TABLE IF EXISTS resultats CASCADE;
-- DROP TABLE IF EXISTS participants_course CASCADE;
-- DROP TABLE IF EXISTS courses CASCADE;
-- DROP TABLE IF EXISTS coureurs CASCADE;
-- DROP TABLE IF EXISTS utilisateurs CASCADE;
-- DROP TYPE IF EXISTS format_utmb CASCADE;


-- =============================================================================
-- TYPES PERSONNALISES
-- =============================================================================

-- Enumération des 4 formats de course officiels UTMB World Series
-- Utilisé comme contrainte sur la table courses
CREATE TYPE format_utmb AS ENUM (
    '50K',      -- Courses autour de 50 kilomètres
    '100K',     -- Courses autour de 100 kilomètres
    '100M',     -- Courses autour de 100 miles (~160 km)
    'Extra'     -- Courses extra (OCC, TDS, MCC, PTL...)
);


-- =============================================================================
-- TABLE : UTILISATEURS
-- =============================================================================

-- Stocke les comptes des participants à l'application de pronostics.
-- Les mots de passe sont obligatoirement hashés (bcrypt) avant insertion.
CREATE TABLE utilisateurs (

    id              UUID            PRIMARY KEY DEFAULT public.uuid_generate_v4(),

    -- Identité
    nom             VARCHAR(100)    NOT NULL,
    prenom          VARCHAR(100)    NOT NULL,
    email           VARCHAR(255)    NOT NULL UNIQUE,
    pseudo          VARCHAR(50)     NOT NULL UNIQUE,

    -- Authentification (mot de passe hashé bcrypt, jamais en clair)
    mdp_hash        VARCHAR(255)    NOT NULL,

    -- Rôle : 'user' pour les participants, 'admin' pour les gestionnaires
    role            VARCHAR(20)     NOT NULL DEFAULT 'user'
                                    CHECK (role IN ('user', 'admin')),

    -- Score cumulé calculé automatiquement par trigger à chaque résultat publié
    points_total    INTEGER         NOT NULL DEFAULT 0
                                    CHECK (points_total >= 0),

    -- Horodatages
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()

);

COMMENT ON TABLE  utilisateurs              IS 'Comptes des participants à l application de pronostics trail.';
COMMENT ON COLUMN utilisateurs.pseudo       IS 'Identifiant public affiché dans le classement. Unique.';
COMMENT ON COLUMN utilisateurs.mdp_hash     IS 'Hash bcrypt du mot de passe. Ne jamais stocker en clair.';
COMMENT ON COLUMN utilisateurs.role         IS 'user = participant standard | admin = gestionnaire de contenu.';
COMMENT ON COLUMN utilisateurs.points_total IS 'Somme des points_gagnes de tous les paris scorés. Mis à jour par trigger.';


-- =============================================================================
-- TABLE : COUREURS
-- =============================================================================

-- Référentiel des athlètes trail avec leurs index UTMB par format.
-- Mis à jour manuellement par les admins chaque vendredi.
CREATE TABLE coureurs (

    id                  UUID        PRIMARY KEY DEFAULT public.uuid_generate_v4(),

    -- Identité
    nom                 VARCHAR(100) NOT NULL,
    prenom              VARCHAR(100) NOT NULL,
    nationalite         VARCHAR(100),

    -- Index UTMB par format (score entre 0 et 1000, null si non classé sur ce format)
    index_utmb_global   NUMERIC(6,2) CHECK (index_utmb_global   BETWEEN 0 AND 1000),
    index_utmb_50k      NUMERIC(6,2) CHECK (index_utmb_50k      BETWEEN 0 AND 1000),
    index_utmb_100k     NUMERIC(6,2) CHECK (index_utmb_100k     BETWEEN 0 AND 1000),
    index_utmb_100m     NUMERIC(6,2) CHECK (index_utmb_100m     BETWEEN 0 AND 1000),
    index_utmb_extra    NUMERIC(6,2) CHECK (index_utmb_extra    BETWEEN 0 AND 1000),

    -- Sexe pour la segmentation des favoris et des paris
    sexe                CHAR(1)     NOT NULL CHECK (sexe IN ('H', 'F')),

    -- Horodatages
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()

);

COMMENT ON TABLE  coureurs                    IS 'Référentiel des athlètes trail et leurs index UTMB World Series.';
COMMENT ON COLUMN coureurs.index_utmb_global  IS 'Index global UTMB toutes distances confondues (0-1000).';
COMMENT ON COLUMN coureurs.index_utmb_50k     IS 'Index UTMB spécifique au format 50K (0-1000). NULL si non classé.';
COMMENT ON COLUMN coureurs.sexe               IS 'H = Homme | F = Femme. Utilisé pour segmenter les favoris par genre.';


-- =============================================================================
-- TABLE : COURSES
-- =============================================================================

-- Calendrier des courses à venir et passées avec leur contexte éditorial.
-- Créées et mises à jour manuellement par les admins chaque vendredi.
CREATE TABLE courses (

    id                  UUID            PRIMARY KEY DEFAULT public.uuid_generate_v4(),

    -- Identification
    nom                 VARCHAR(200)    NOT NULL,
    format              format_utmb     NOT NULL,
    lieu                VARCHAR(200),
    date_course         DATE            NOT NULL,

    -- Contenu éditorial : avis du traileur expert (Le Duc)
    avis_expert         TEXT,

    -- Statut : TRUE une fois que les résultats officiels ont été saisis
    resultats_publies   BOOLEAN         NOT NULL DEFAULT FALSE,

    -- Horodatages
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()

);

COMMENT ON TABLE  courses                    IS 'Calendrier des courses trail avec contexte éditorial.';
COMMENT ON COLUMN courses.format             IS 'Format UTMB World Series : 50K, 100K, 100M ou Extra.';
COMMENT ON COLUMN courses.avis_expert        IS 'Analyse et pronostic libre rédigé par le traileur expert (Le Duc).';
COMMENT ON COLUMN courses.resultats_publies  IS 'Passe à TRUE quand les résultats sont saisis. Déclenche le calcul des points.';


-- =============================================================================
-- TABLE : PARTICIPANTS_COURSE
-- =============================================================================

-- Table de liaison entre coureurs et courses (N-N).
-- Alimente les listes déroulantes du dialog de pari.
CREATE TABLE participants_course (

    id          UUID        PRIMARY KEY DEFAULT public.uuid_generate_v4(),
    course_id   UUID        NOT NULL REFERENCES courses(id)  ON DELETE CASCADE,
    coureur_id  UUID        NOT NULL REFERENCES coureurs(id) ON DELETE CASCADE,

    -- Un coureur ne peut être inscrit qu'une seule fois par course
    CONSTRAINT uq_participant_course UNIQUE (course_id, coureur_id)

);

COMMENT ON TABLE participants_course IS 'Inscriptions des coureurs aux courses. Alimente les favoris et les listes de paris.';


-- =============================================================================
-- TABLE : RESULTATS
-- =============================================================================

-- Podiums officiels saisis par les admins après chaque course.
-- L'insertion d'un résultat déclenche le calcul des points via trigger.
CREATE TABLE resultats (

    id              UUID        PRIMARY KEY DEFAULT public.uuid_generate_v4(),
    course_id       UUID        NOT NULL UNIQUE REFERENCES courses(id) ON DELETE CASCADE,

    -- Podium hommes
    homme_1er       UUID        REFERENCES coureurs(id),
    homme_2eme      UUID        REFERENCES coureurs(id),
    homme_3eme      UUID        REFERENCES coureurs(id),

    -- Podium femmes
    femme_1ere      UUID        REFERENCES coureurs(id),
    femme_2eme      UUID        REFERENCES coureurs(id),
    femme_3eme      UUID        REFERENCES coureurs(id),

    -- Horodatage de saisie
    saisi_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    saisi_par       UUID        REFERENCES utilisateurs(id)

);

COMMENT ON TABLE  resultats            IS 'Podiums officiels saisis par les admins. Déclenche le scoring des paris via trigger.';
COMMENT ON COLUMN resultats.saisi_par  IS 'Référence vers l admin ayant saisi le résultat (traçabilité).';


-- =============================================================================
-- TABLE : PARIS
-- =============================================================================

-- Pronostics déposés par les utilisateurs avant chaque course.
-- Un seul pari autorisé par utilisateur et par course.
CREATE TABLE paris (

    id              UUID        PRIMARY KEY DEFAULT public.uuid_generate_v4(),
    user_id         UUID        NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    course_id       UUID        NOT NULL REFERENCES courses(id)      ON DELETE CASCADE,

    -- Pronostics hommes (FK vers coureurs)
    homme_1er       UUID        REFERENCES coureurs(id),
    homme_2eme      UUID        REFERENCES coureurs(id),
    homme_3eme      UUID        REFERENCES coureurs(id),

    -- Pronostics femmes (FK vers coureurs)
    femme_1ere      UUID        REFERENCES coureurs(id),
    femme_2eme      UUID        REFERENCES coureurs(id),
    femme_3eme      UUID        REFERENCES coureurs(id),

    -- Points attribués après publication des résultats (NULL tant que non scoré)
    points_gagnes   INTEGER     CHECK (points_gagnes >= 0),

    -- Horodatages
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Contrainte : un seul pari par utilisateur et par course
    CONSTRAINT uq_pari_user_course UNIQUE (user_id, course_id)

);

COMMENT ON TABLE  paris               IS 'Pronostics des utilisateurs. Un seul pari autorisé par user et par course.';
COMMENT ON COLUMN paris.points_gagnes IS 'NULL avant résultats. Calculé automatiquement par trigger après publication.';


-- =============================================================================
-- INDEX
-- =============================================================================

CREATE INDEX idx_paris_user_id        ON paris(user_id);
CREATE INDEX idx_paris_course_id      ON paris(course_id);
CREATE INDEX idx_participants_course  ON participants_course(course_id);
CREATE INDEX idx_courses_date         ON courses(date_course);
CREATE INDEX idx_coureurs_index_global ON coureurs(index_utmb_global DESC NULLS LAST);
CREATE INDEX idx_utilisateurs_points  ON utilisateurs(points_total DESC);


-- =============================================================================
-- TRIGGER : mise à jour automatique du champ updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
/*
    Fonction trigger : met à jour automatiquement le champ updated_at
    à l'horodatage courant lors de chaque UPDATE sur la table cible.

    Retourne : NEW (la ligne modifiée avec updated_at mis à jour)
*/
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_utilisateurs_updated_at
    BEFORE UPDATE ON utilisateurs
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_courses_updated_at
    BEFORE UPDATE ON courses
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_paris_updated_at
    BEFORE UPDATE ON paris
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_coureurs_updated_at
    BEFORE UPDATE ON coureurs
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();


-- =============================================================================
-- FONCTION : calcul des points d un pari
-- =============================================================================

CREATE OR REPLACE FUNCTION fn_calculer_points_pari(
    p_paris_id      UUID,
    p_resultats_id  UUID
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
/*
    Calcule le score d'un pari en le comparant aux résultats officiels.

    Grille de points :
        - Coureur pronostiqué à la bonne place exacte        : 10 pts
        - Coureur pronostiqué sur le podium (mauvaise place) :  4 pts
        - Bonus podium complet exact (H ou F)                : +5 pts
        Total maximum par course : (3×10 + 5) × 2 genres    = 70 pts

    Paramètres :
        p_paris_id     (UUID) : identifiant du pari à scorer
        p_resultats_id (UUID) : identifiant des résultats officiels

    Retourne :
        INTEGER : total des points gagnés (0 si aucun pronostic correct)
*/
DECLARE
    v_paris         paris%ROWTYPE;
    v_resultats     resultats%ROWTYPE;
    v_points        INTEGER := 0;
    v_podium_h_ids  UUID[];
    v_podium_f_ids  UUID[];
BEGIN
    SELECT * INTO v_paris     FROM paris     WHERE id = p_paris_id;
    SELECT * INTO v_resultats FROM resultats WHERE id = p_resultats_id;

    v_podium_h_ids := ARRAY[v_resultats.homme_1er, v_resultats.homme_2eme, v_resultats.homme_3eme];
    v_podium_f_ids := ARRAY[v_resultats.femme_1ere, v_resultats.femme_2eme, v_resultats.femme_3eme];

    -- Scoring hommes
    IF v_paris.homme_1er IS NOT NULL AND v_paris.homme_1er = v_resultats.homme_1er THEN
        v_points := v_points + 10;
    ELSIF v_paris.homme_1er IS NOT NULL AND v_paris.homme_1er = ANY(v_podium_h_ids) THEN
        v_points := v_points + 4;
    END IF;

    IF v_paris.homme_2eme IS NOT NULL AND v_paris.homme_2eme = v_resultats.homme_2eme THEN
        v_points := v_points + 10;
    ELSIF v_paris.homme_2eme IS NOT NULL AND v_paris.homme_2eme = ANY(v_podium_h_ids) THEN
        v_points := v_points + 4;
    END IF;

    IF v_paris.homme_3eme IS NOT NULL AND v_paris.homme_3eme = v_resultats.homme_3eme THEN
        v_points := v_points + 10;
    ELSIF v_paris.homme_3eme IS NOT NULL AND v_paris.homme_3eme = ANY(v_podium_h_ids) THEN
        v_points := v_points + 4;
    END IF;

    IF  v_paris.homme_1er  = v_resultats.homme_1er
    AND v_paris.homme_2eme = v_resultats.homme_2eme
    AND v_paris.homme_3eme = v_resultats.homme_3eme THEN
        v_points := v_points + 5;
    END IF;

    -- Scoring femmes
    IF v_paris.femme_1ere IS NOT NULL AND v_paris.femme_1ere = v_resultats.femme_1ere THEN
        v_points := v_points + 10;
    ELSIF v_paris.femme_1ere IS NOT NULL AND v_paris.femme_1ere = ANY(v_podium_f_ids) THEN
        v_points := v_points + 4;
    END IF;

    IF v_paris.femme_2eme IS NOT NULL AND v_paris.femme_2eme = v_resultats.femme_2eme THEN
        v_points := v_points + 10;
    ELSIF v_paris.femme_2eme IS NOT NULL AND v_paris.femme_2eme = ANY(v_podium_f_ids) THEN
        v_points := v_points + 4;
    END IF;

    IF v_paris.femme_3eme IS NOT NULL AND v_paris.femme_3eme = v_resultats.femme_3eme THEN
        v_points := v_points + 10;
    ELSIF v_paris.femme_3eme IS NOT NULL AND v_paris.femme_3eme = ANY(v_podium_f_ids) THEN
        v_points := v_points + 4;
    END IF;

    IF  v_paris.femme_1ere = v_resultats.femme_1ere
    AND v_paris.femme_2eme = v_resultats.femme_2eme
    AND v_paris.femme_3eme = v_resultats.femme_3eme THEN
        v_points := v_points + 5;
    END IF;

    RETURN v_points;
END;
$$;


-- =============================================================================
-- TRIGGER : scoring automatique des paris à la publication des résultats
-- =============================================================================

CREATE OR REPLACE FUNCTION fn_scorer_paris_apres_resultats()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
/*
    Trigger exécuté AFTER INSERT sur la table resultats.

    Actions :
        1. Met à jour points_gagnes sur tous les paris de la course concernée.
        2. Recalcule points_total dans la table utilisateurs.
        3. Passe resultats_publies = TRUE sur la course.

    Retourne : NEW
*/
DECLARE
    v_pari      paris%ROWTYPE;
    v_points    INTEGER;
BEGIN
    FOR v_pari IN
        SELECT * FROM paris WHERE course_id = NEW.course_id
    LOOP
        v_points := fn_calculer_points_pari(v_pari.id, NEW.id);

        UPDATE paris
        SET    points_gagnes = v_points,
               updated_at    = NOW()
        WHERE  id = v_pari.id;

        UPDATE utilisateurs
        SET    points_total = (
                   SELECT COALESCE(SUM(points_gagnes), 0)
                   FROM   paris
                   WHERE  user_id       = v_pari.user_id
                   AND    points_gagnes IS NOT NULL
               ),
               updated_at = NOW()
        WHERE  id = v_pari.user_id;

    END LOOP;

    UPDATE courses
    SET    resultats_publies = TRUE,
           updated_at        = NOW()
    WHERE  id = NEW.course_id;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_scorer_paris
    AFTER INSERT ON resultats
    FOR EACH ROW EXECUTE FUNCTION fn_scorer_paris_apres_resultats();


-- =============================================================================
-- ROW LEVEL SECURITY (RLS) - Supabase
-- =============================================================================

ALTER TABLE utilisateurs  ENABLE ROW LEVEL SECURITY;
ALTER TABLE paris          ENABLE ROW LEVEL SECURITY;
ALTER TABLE resultats      ENABLE ROW LEVEL SECURITY;

CREATE POLICY "utilisateurs_own"
    ON utilisateurs
    FOR ALL
    USING      (id = auth.uid())
    WITH CHECK (id = auth.uid());

CREATE POLICY "paris_own"
    ON paris
    FOR ALL
    USING      (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "resultats_read_all"
    ON resultats FOR SELECT
    USING (TRUE);

CREATE POLICY "resultats_admin_write"
    ON resultats FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM utilisateurs
            WHERE id = auth.uid() AND role = 'admin'
        )
    );


-- =============================================================================
-- GRANTS
-- =============================================================================

GRANT USAGE ON SCHEMA trail_betting_db TO anon, authenticated;
GRANT ALL   ON ALL TABLES    IN SCHEMA trail_betting_db TO authenticated;
GRANT SELECT ON ALL TABLES   IN SCHEMA trail_betting_db TO anon;
GRANT ALL   ON ALL SEQUENCES IN SCHEMA trail_betting_db TO authenticated;
GRANT ALL   ON ALL FUNCTIONS IN SCHEMA trail_betting_db TO authenticated;


-- =============================================================================
-- DONNEES INITIALES (SEED)
-- =============================================================================

-- Compte administrateur par défaut
-- IMPORTANT : remplacer le hash avant la mise en production
-- Hash ci-dessous = bcrypt('changeme', rounds=12)
INSERT INTO utilisateurs (nom, prenom, email, pseudo, mdp_hash, role)
VALUES (
    'Admin',
    'Trail',
    'admin@trailbetting.app',
    'le_duc',
    '$2b$12$placeholderHashARemplacerAvantProduction000000000000000',
    'admin'
)
ON CONFLICT (email) DO NOTHING;


-- =============================================================================
-- FIN DU SCHEMA
-- =============================================================================
