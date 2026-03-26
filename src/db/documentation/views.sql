-- =============================================================================
-- VUES SQL - TRAIL BETTING
--
-- Description : Vues PostgreSQL créées dans Supabase pour simplifier les
--               requêtes complexes côté Python.
--               Ces vues sont lues via le client Supabase comme des tables
--               ordinaires, sans avoir besoin de psycopg2.
--
-- Usage       : Exécuter dans le SQL Editor de Supabase après schema.sql.
-- =============================================================================


-- =============================================================================
-- SCHEMA DE TRAVAIL
-- =============================================================================

SET search_path TO trail_betting_db;


-- =============================================================================
-- VUE : courses à venir
-- =============================================================================

CREATE OR REPLACE VIEW vue_courses_a_venir AS
SELECT
    c.id,
    c.nom,
    c.format,
    c.lieu,
    c.date_course,
    c.avis_expert
FROM
    courses c
WHERE
    c.date_course       >= CURRENT_DATE
    AND c.resultats_publies = FALSE
ORDER BY
    c.date_course ASC;

COMMENT ON VIEW vue_courses_a_venir IS
    'Courses à venir sans résultats publiés, triées par date croissante.';


-- =============================================================================
-- VUE : participants d une course avec leurs index UTMB
-- =============================================================================

CREATE OR REPLACE VIEW vue_participants_course AS
SELECT
    pc.course_id,
    c.id                AS coureur_id,
    c.nom,
    c.prenom,
    c.nationalite,
    c.sexe,
    c.index_utmb_global,
    c.index_utmb_20k,
    c.index_utmb_50k,
    c.index_utmb_100k,
    c.index_utmb_100m
FROM
    participants_course pc
    JOIN coureurs c ON c.id = pc.coureur_id;

COMMENT ON VIEW vue_participants_course IS
    'Participants de chaque course avec leurs index UTMB. Filtrer sur course_id côté Python.';


-- =============================================================================
-- VUE : paris d un utilisateur avec noms des coureurs et course
-- =============================================================================

CREATE OR REPLACE VIEW vue_paris_utilisateur AS
SELECT
    p.id                                        AS pari_id,
    p.user_id,
    p.course_id,
    c.nom                                       AS course_nom,
    c.format                                    AS course_format,
    c.date_course,
    CONCAT(h1.prenom, ' ', UPPER(h1.nom))       AS homme_1er,
    CONCAT(h2.prenom, ' ', UPPER(h2.nom))       AS homme_2eme,
    CONCAT(h3.prenom, ' ', UPPER(h3.nom))       AS homme_3eme,
    CONCAT(f1.prenom, ' ', UPPER(f1.nom))       AS femme_1ere,
    CONCAT(f2.prenom, ' ', UPPER(f2.nom))       AS femme_2eme,
    CONCAT(f3.prenom, ' ', UPPER(f3.nom))       AS femme_3eme,
    p.points_gagnes,
    p.created_at
FROM
    paris p
    JOIN courses  c   ON c.id  = p.course_id
    LEFT JOIN coureurs h1 ON h1.id = p.homme_1er
    LEFT JOIN coureurs h2 ON h2.id = p.homme_2eme
    LEFT JOIN coureurs h3 ON h3.id = p.homme_3eme
    LEFT JOIN coureurs f1 ON f1.id = p.femme_1ere
    LEFT JOIN coureurs f2 ON f2.id = p.femme_2eme
    LEFT JOIN coureurs f3 ON f3.id = p.femme_3eme;

COMMENT ON VIEW vue_paris_utilisateur IS
    'Paris avec noms des coureurs pronostiqués et infos course. Filtrer sur user_id côté Python.';


-- =============================================================================
-- VUE : classement général des utilisateurs
-- =============================================================================

CREATE OR REPLACE VIEW vue_classement_general AS
SELECT
    RANK() OVER (
        ORDER BY u.points_total DESC, u.pseudo ASC
    )::INTEGER                                  AS rang,
    u.id                                        AS user_id,
    u.pseudo,
    u.points_total,
    COUNT(p.id)                                 AS nb_paris,
    COUNT(p.id) FILTER (
        WHERE p.points_gagnes IS NOT NULL
    )                                           AS nb_paris_scores,
    CASE
        WHEN COUNT(p.id) FILTER (
            WHERE p.points_gagnes IS NOT NULL
        ) = 0 THEN 0
        ELSE ROUND(
            u.points_total::NUMERIC /
            NULLIF(
                COUNT(p.id) FILTER (
                    WHERE p.points_gagnes IS NOT NULL
                ) * 70, 0
            ) * 100, 1
        )
    END                                         AS taux_reussite
FROM
    utilisateurs u
    LEFT JOIN paris p ON p.user_id = u.id
WHERE
    u.role = 'user'
GROUP BY
    u.id, u.pseudo, u.points_total
ORDER BY
    u.points_total DESC,
    u.pseudo ASC;

COMMENT ON VIEW vue_classement_general IS
    'Classement général avec rang, points, nb paris et taux de réussite. Admins exclus.';


-- =============================================================================
-- VUE : historique des points par utilisateur
-- =============================================================================

CREATE OR REPLACE VIEW vue_historique_points AS
SELECT
    p.user_id,
    c.date_course,
    c.nom                                               AS course_nom,
    c.format                                            AS course_format,
    p.points_gagnes,
    SUM(p.points_gagnes) OVER (
        PARTITION BY p.user_id
        ORDER BY c.date_course ASC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                                   AS cumul_points,
    CONCAT(h1p.prenom, ' ', UPPER(h1p.nom))             AS homme_1er_parie,
    CONCAT(h1r.prenom, ' ', UPPER(h1r.nom))             AS homme_1er_reel,
    CONCAT(f1p.prenom, ' ', UPPER(f1p.nom))             AS femme_1ere_pariee,
    CONCAT(f1r.prenom, ' ', UPPER(f1r.nom))             AS femme_1ere_reelle
FROM
    paris p
    JOIN courses   c   ON c.id        = p.course_id
    JOIN resultats r   ON r.course_id = c.id
    LEFT JOIN coureurs h1p ON h1p.id  = p.homme_1er
    LEFT JOIN coureurs f1p ON f1p.id  = p.femme_1ere
    LEFT JOIN coureurs h1r ON h1r.id  = r.homme_1er
    LEFT JOIN coureurs f1r ON f1r.id  = r.femme_1ere
WHERE
    p.points_gagnes IS NOT NULL;

COMMENT ON VIEW vue_historique_points IS
    'Historique des points course par course avec cumul. Filtrer sur user_id côté Python.';


-- =============================================================================
-- VUE : résultats complets d une course (podium H et F avec noms)
-- =============================================================================

CREATE OR REPLACE VIEW vue_resultats_course AS
SELECT
    r.course_id,
    c.nom                                           AS course_nom,
    c.date_course,
    CONCAT(h1.prenom, ' ', UPPER(h1.nom))           AS homme_1er,
    CONCAT(h2.prenom, ' ', UPPER(h2.nom))           AS homme_2eme,
    CONCAT(h3.prenom, ' ', UPPER(h3.nom))           AS homme_3eme,
    CONCAT(f1.prenom, ' ', UPPER(f1.nom))           AS femme_1ere,
    CONCAT(f2.prenom, ' ', UPPER(f2.nom))           AS femme_2eme,
    CONCAT(f3.prenom, ' ', UPPER(f3.nom))           AS femme_3eme
FROM
    resultats r
    JOIN courses c  ON c.id = r.course_id
    LEFT JOIN coureurs h1 ON h1.id = r.homme_1er
    LEFT JOIN coureurs h2 ON h2.id = r.homme_2eme
    LEFT JOIN coureurs h3 ON h3.id = r.homme_3eme
    LEFT JOIN coureurs f1 ON f1.id = r.femme_1ere
    LEFT JOIN coureurs f2 ON f2.id = r.femme_2eme
    LEFT JOIN coureurs f3 ON f3.id = r.femme_3eme;

COMMENT ON VIEW vue_resultats_course IS
    'Podium complet H/F avec noms pour une course. Filtrer sur course_id côté Python.';


-- =============================================================================
-- VUE : derniers résultats publiés
-- =============================================================================

CREATE OR REPLACE VIEW vue_derniers_resultats AS
SELECT
    c.date_course,
    c.nom                                           AS course_nom,
    c.format                                        AS course_format,
    CONCAT(h1.prenom, ' ', UPPER(h1.nom))           AS homme_1er,
    CONCAT(f1.prenom, ' ', UPPER(f1.nom))           AS femme_1ere,
    r.saisi_at
FROM
    resultats r
    JOIN courses c  ON c.id  = r.course_id
    LEFT JOIN coureurs h1 ON h1.id = r.homme_1er
    LEFT JOIN coureurs f1 ON f1.id = r.femme_1ere
ORDER BY
    c.date_course DESC;

COMMENT ON VIEW vue_derniers_resultats IS
    'Derniers résultats publiés avec vainqueurs H/F. Appliquer LIMIT côté Python.';


-- =============================================================================
-- GRANTS SUR LES VUES
-- =============================================================================

GRANT USAGE ON SCHEMA trail_betting_db TO anon, authenticated;

GRANT SELECT ON trail_betting_db.vue_courses_a_venir     TO anon, authenticated;
GRANT SELECT ON trail_betting_db.vue_participants_course TO anon, authenticated;
GRANT SELECT ON trail_betting_db.vue_paris_utilisateur   TO authenticated;
GRANT SELECT ON trail_betting_db.vue_classement_general  TO anon, authenticated;
GRANT SELECT ON trail_betting_db.vue_historique_points   TO authenticated;
GRANT SELECT ON trail_betting_db.vue_resultats_course    TO anon, authenticated;
GRANT SELECT ON trail_betting_db.vue_derniers_resultats  TO anon, authenticated;
